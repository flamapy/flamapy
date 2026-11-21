"""Descriptor-driven facade over the flamapy analysis operations.

The public operation methods are not written by hand. At import time :func:`_install_operations`
reads the :class:`OperationDescriptor`s discovered from the installed plugins
(:meth:`DiscoverMetamodels.available_operations`) and synthesises one method per operation, each
with a real signature and ``__doc__`` so the CLI and REST layers can keep introspecting the class.
Dropping a new operation into a plugin therefore extends the Python facade, the CLI and the REST API
for free. Backend resolution is dynamic (by fm-to-backend transformation extension), so there is no
per-operation or per-backend code here. Static typing is provided by a generated ``.pyi`` stub.
"""
import inspect
import logging
import os
import threading
from enum import Enum
from typing import Any, Dict, Iterator, Optional, Union

import dataclasses
import warnings

from flamapy.core import cache as artifact_cache
from flamapy.core.discover import DiscoverMetamodels
from flamapy.core.exceptions import FlamaException, OperationTimeout, PluginNotFound
from flamapy.core.execution import Interruptible, Job, default_engine, run_and_wrap
from flamapy.core.models import VariabilityModel
from flamapy.core.models.language_level import LanguageLevel
from flamapy.core.operations import (
    OperationDescriptor,
    OperationResult,
    StreamingOperation,
)
from flamapy.core.planner import Plan, plan as plan_backend
from flamapy.metamodels.configuration_metamodel.models import Configuration
from flamapy.metamodels.fm_metamodel.models import FeatureModel
from flamapy.metamodels.fm_metamodel.operations.fm_language_level import (
    calculate_language_level,
)

logger = logging.getLogger(__name__)


class Backend(str, Enum):
    """Analysis backend identifier.

    Retained so the REST layer can offer a backend dropdown; the facade itself no longer switches on
    it — it resolves the backend dynamically to a transformation extension.
    """

    SAT = "sat"
    BDD = "bdd"
    Z3 = "z3"
    # Optional backends, installed via the flamapy extras of the same name
    # (e.g. pip install "flamapy[sharpsat]", or "flamapy[all-solvers]" for all three).
    SHARPSAT = "sharpsat"
    SDD = "sdd"
    DNNF = "dnnf"
    # Opt-in: let the query planner pick the backend per operation, from the plugins'
    # capability manifests (language level, scale, cost). Also enabled process-wide by
    # setting FLAMAPY_BACKEND=auto. Becomes the default in flamapy 3.0.
    AUTO = "auto"


# Facade backend name -> fm-to-backend transformation extension (the only non-identity mapping).
_BACKEND_ALIAS = {"sat": "pysat"}

# Operations that ran on a fixed backend in 2.6 and accept ``backend=`` since 2.9. In 2.x only a
# per-call ``backend=`` changes them: the workspace default and FLAMAPY_BACKEND do not, so code
# that set a default backend in 2.6 keeps the same results (the default would otherwise move
# atomic sets from the tree to SAT, or send commonality to a backend without it). 3.0 applies
# the defaults to them like to every other selectable operation.
_SELECTABLE_SINCE_2_9 = frozenset({'atomic_sets', 'commonality'})

_TRUE_VALUES = ('1', 'true', 'yes', 'on')


def _env_flag(name: str) -> bool:
    return os.environ.get(name, '').strip().lower() in _TRUE_VALUES


def _raise_errors(setting: Optional[bool]) -> bool:
    """The model's ``raise_errors`` when set, else the FLAMAPY_RAISE_ERRORS variable."""
    return setting if setting is not None else _env_flag('FLAMAPY_RAISE_ERRORS')


def _caller_stacklevel() -> int:
    """The ``warnings.warn`` stacklevel, for its caller, of the first frame outside this module:
    the user's call, whichever facade entry point (operation method, iter_configurations) it
    went through."""
    frame = inspect.currentframe()
    frame = frame.f_back if frame is not None else None  # the function calling warnings.warn
    level = 1
    while frame is not None and frame.f_globals.get('__name__') == __name__:
        frame = frame.f_back
        level += 1
    return level


@dataclasses.dataclass(frozen=True)
class _Route:
    """How one call's backend was chosen. It travels with the call (never stored on the
    facade), so concurrent ``run_async`` jobs on one facade cannot see each other's."""
    # The backend name as requested or defaulted; None for an fm-level operation.
    name: Optional[str] = None
    # True when the choice is the query planner's (backend='auto').
    auto: bool = False
    # None (historical default), 'explicit', or 'auto: <planner rationale>'.
    planner: Optional[str] = None
    # Set when the backend ignores part of the model (its manifest does not support the
    # model's language level): the warning to emit; the result is then not exact.
    level_gap: Optional[str] = None


def _stamp(envelope: OperationResult[Any], route: _Route,
           model: VariabilityModel) -> OperationResult[Any]:
    """Record on a result envelope how its backend was chosen and whether it is exact."""
    if route.planner is not None:
        envelope = dataclasses.replace(envelope, planner=route.planner)
    if route.level_gap is not None:
        envelope = dataclasses.replace(envelope, exact=False)
    if getattr(model, '_flamapy_cache_hit', False):
        envelope = dataclasses.replace(envelope, cache_hit=True)
    return envelope


def _warn_level_gap(route: _Route) -> None:
    if route.level_gap is not None:
        warnings.warn(route.level_gap, UserWarning, stacklevel=_caller_stacklevel())


class FLAMAFeatureModel:
    """A feature model together with the analysis operations discovered from the installed plugins.

    Operation methods are generated from their OperationDescriptors (see the module docstring); call
    them as normal methods, e.g. ``FLAMAFeatureModel(path).satisfiable()``.
    """

    def __init__(self, model_path: str, backend: Optional[str] = None, *,
                 allow_approximate: Optional[bool] = None,
                 raise_errors: Optional[bool] = None) -> None:
        """``model_path`` is the filesystem path to the model (UVL, FaMaXML or FeatureIDE).

        ``backend`` optionally sets a workspace-wide default backend ("sat", "bdd" or "z3",
        plus "sharpsat"/"sdd"/"dnnf" when the corresponding optional flamapy extra is
        installed) for every operation that supports more than one. When left as ``None``
        each operation keeps its historical default, so existing code behaves exactly as
        before. ``atomic_sets`` and ``commonality``, selectable only since 2.9, follow just a
        per-call ``backend=`` in 2.x.

        ``allow_approximate`` lets the ``'auto'`` backend choose approximate implementations
        (e.g. sharpsat's ApproxMC counting, or the structural core features that ignore
        cross-tree constraints); by default the planner only picks exact ones. It has no
        effect on other backends. ``None`` falls back to ``FLAMAPY_ALLOW_APPROXIMATE=1``; a
        per-call ``allow_approximate=`` overrides both.

        ``raise_errors`` opts into the 3.0 error contract today: a failing operation raises
        its ``FlamaException`` instead of logging it and returning ``None``. ``None`` falls
        back to ``FLAMAPY_RAISE_ERRORS=1``, which also applies to the producers (e.g.
        ``generate_random_feature_model``).

        Both flags are keyword-only.
        """
        self.model_path = model_path
        self.discover_metamodel = DiscoverMetamodels()
        self.fm_model = self._read(model_path)
        self.backend = Backend(backend) if backend is not None else None
        self.allow_approximate = allow_approximate
        self.raise_errors = raise_errors
        self._backend_models: Dict[str, VariabilityModel] = {}
        # Provenance envelope of the last executed operation (value, plugin, backend, exact,
        # wall time, model hash). Purely informational in 2.9; methods still return bare
        # values. In 3.0 the envelope becomes the return type.
        self.last_result: Optional[OperationResult] = None
        self._model_language_level: Optional[LanguageLevel] = None

    def _read(self, model_path: str) -> FeatureModel:
        return self.discover_metamodel.use_transformation_t2m(model_path, "fm")

    def _as_configuration(
        self, configuration: Union[str, Dict[str, Any], Configuration]
    ) -> Configuration:
        """Resolve a configuration argument into a Configuration model.

        Accepts a path to a configuration file (read via the configuration transformation), a
        ``{feature: value}`` mapping, or an already-built Configuration.
        """
        if isinstance(configuration, Configuration):
            return configuration
        if isinstance(configuration, dict):
            return Configuration(configuration)
        return self.discover_metamodel.use_transformation_t2m(configuration, "configuration")

    def _route(self, descriptor: OperationDescriptor, backend_arg: Optional[str]) -> _Route:
        """Decide which backend a call runs on, without building anything.

        The backend is the per-call one > workspace default > the ``FLAMAPY_BACKEND``
        environment variable > the operation's default (for backend-selectable ops), or
        simply the fixed default. The value ``'auto'`` (opt-in) hands the choice to the
        query planner; ``None`` (an fm-level op, or a selectable op with no backend
        requested) runs the operation on the feature model directly.
        """
        defaults_apply = (descriptor.selectable_backend
                          and descriptor.name not in _SELECTABLE_SINCE_2_9)
        workspace_default = (self.backend or os.environ.get('FLAMAPY_BACKEND')
                             if defaults_apply else None)
        if descriptor.selectable_backend:
            resolved = backend_arg or workspace_default or descriptor.default_backend
        else:
            resolved = descriptor.default_backend
        if resolved is None:
            return _Route()
        name = resolved.value if isinstance(resolved, Backend) else str(resolved)
        if name == Backend.AUTO.value and descriptor.selectable_backend:
            return _Route(name=name, auto=True)
        return _Route(
            name=name,
            planner='explicit' if backend_arg or workspace_default else None,
            level_gap=self._level_gap(name, descriptor.selectable_backend))

    def _level_gap(self, name: str, selectable: bool) -> Optional[str]:
        """The warning for a backend whose manifest does not support the model's language
        level (e.g. sat/bdd ignore arithmetic constraints), or None when it does.

        In 2.9 this only warns, and the result is marked inexact; flamapy 3.0 raises
        NoCompatibleBackendError instead, like backend='auto' does when no installed plugin
        supports the model.
        """
        extension = _BACKEND_ALIAS.get(name, name)
        try:
            manifest = self.discover_metamodel.plugins.get_plugin_by_extension(extension).manifest
        except PluginNotFound:
            return None  # an unknown backend fails later, when its model is built
        model_level = self._language_level()
        if manifest.supports(model_level):
            return None
        advice = ''
        if selectable and self._z3_supports(model_level) and name != Backend.Z3.value:
            advice = " Use backend='auto' or backend='z3'."
        return (f"The '{name}' backend supports ({manifest.supported_level}), but this model "
                f"is ({model_level}): constraints beyond the backend's level are ignored, so "
                f"the result is not exact.{advice}")

    def _z3_supports(self, model_level: LanguageLevel) -> bool:
        try:
            plugin = self.discover_metamodel.plugins.get_plugin_by_extension(Backend.Z3.value)
        except PluginNotFound:
            return False
        return plugin.manifest.supports(model_level)

    def _model_for(
        self, descriptor: OperationDescriptor, route: _Route,
        allow_approximate: Optional[bool] = None,
    ) -> tuple[VariabilityModel, _Route]:
        """Build the route's target model, lazily transforming (and caching) fm->backend.

        A backend name is mapped to a transformation extension (only ``sat -> pysat``
        differs) and cached per extension. Returns the route too: for ``'auto'`` it now
        carries the planner's rationale.
        """
        if route.name is None:
            return self.fm_model, route
        if route.auto:
            return self._model_via_planner(
                descriptor, route, self._approximate_allowed(allow_approximate))
        return self._backend_model(_BACKEND_ALIAS.get(route.name, route.name)), route

    def _backend_model(self, extension: str) -> VariabilityModel:
        if extension == self.fm_model.get_extension():
            return self.fm_model
        if extension not in self._backend_models:
            self._backend_models[extension] = self.discover_metamodel.use_transformation_m2m(
                self.fm_model, extension)
        return self._backend_models[extension]

    def _language_level(self) -> LanguageLevel:
        if self._model_language_level is None:
            self._model_language_level = calculate_language_level(self.fm_model)
        return self._model_language_level

    def _approximate_allowed(self, per_call: Optional[bool]) -> bool:
        """Per-call flag > the model's setting > the FLAMAPY_ALLOW_APPROXIMATE variable."""
        if per_call is not None:
            return per_call
        if self.allow_approximate is not None:
            return self.allow_approximate
        return _env_flag('FLAMAPY_ALLOW_APPROXIMATE')

    def _plan_operation(self, operation_name: str, allow_approximate: bool = False) -> Plan:
        """Ask the query planner which backend should run ``operation_name`` on this model.

        The backend models this facade has already built count as free for the planner.
        """
        edges = [(t.get_source_extension(), t.get_destination_extension())
                 for t in self.discover_metamodel.get_transformations_m2m()]
        model_hash = self.fm_model.canonical_hash()
        return plan_backend(
            operation_name,
            source_extension=self.fm_model.get_extension(),
            model_level=self._language_level(),
            n_features=len(self.fm_model.get_features()),
            plugins=self.discover_metamodel.plugins,
            m2m_edges=edges,
            artifact_available=lambda ext: artifact_cache.available_for(model_hash, ext),
            available_models=set(self._backend_models),
            allow_approximate=allow_approximate,
        )

    def plan(self, operation: str, *, allow_approximate: Optional[bool] = None) -> Plan:
        """Which backend ``backend='auto'`` would run ``operation`` on this model, and why.

        Returns the planner's :class:`~flamapy.core.planner.Plan` (plugin, target extension,
        transformation chain, rationale, estimated cost in ms, alternatives) without running
        anything. Raises :class:`~flamapy.core.exceptions.NoCompatibleBackendError` when no
        installed plugin can run the operation on this model, and ``FlamaException`` when
        ``operation`` is not a backend-selectable facade operation. ``allow_approximate``
        falls back to the model's setting and the environment, like the operations do.
        """
        method = getattr(type(self), operation, None)
        descriptor = getattr(method, '_facade_descriptor', None)
        if descriptor is None or not descriptor.selectable_backend:
            raise FlamaException(f"'{operation}' is not a backend-selectable facade operation.")
        return self._plan_operation(operation, self._approximate_allowed(allow_approximate))

    def _model_via_planner(self, descriptor: OperationDescriptor, route: _Route,
                           allow_approximate: bool = False) -> tuple[VariabilityModel, _Route]:
        chosen = self._plan_operation(descriptor.name, allow_approximate)
        route = dataclasses.replace(route, planner=f'auto: {chosen.rationale}')
        model = self.fm_model
        for _, destination in chosen.transformation_chain:
            if destination not in self._backend_models:
                self._backend_models[destination] = (
                    self.discover_metamodel.use_transformation_m2m(model, destination))
            model = self._backend_models[destination]
        return model, route

    def _prepare_operation(
        self, descriptor: OperationDescriptor, backend_arg: Optional[str],
        call_kwargs: Dict[str, Any], allow_approximate: Optional[bool] = None,
        route: Optional[_Route] = None,
    ) -> tuple[Any, VariabilityModel, _Route]:
        """Resolve the target model and a fully input-wired operation instance.

        ``route`` is passed by a caller that already decided it (and warned) on the user's
        thread; otherwise it is decided, and its warning emitted, here.
        """
        if route is None:
            route = self._route(descriptor, backend_arg)
            _warn_level_gap(route)
        model, route = self._model_for(descriptor, route, allow_approximate)
        operation = self.discover_metamodel.get_operation(model, descriptor.operation)
        if descriptor.input_adapter is not None:
            descriptor.input_adapter(operation, self, call_kwargs)
        else:
            for input_spec in descriptor.inputs:
                value = call_kwargs.get(input_spec.name)
                if value is None:
                    continue
                if input_spec.kind == 'configuration':
                    value = self._as_configuration(value)
                if input_spec.setter is not None:
                    getattr(operation, input_spec.setter)(value)
        return operation, model, route

    def _run_operation(
        self, descriptor: OperationDescriptor, call_kwargs: Dict[str, Any]
    ) -> Any:
        """Resolve model + operation, wire inputs, execute, and marshal the result.

        Preserves the facade's historical contract: any :class:`FlamaException` is logged and the
        call returns ``None``, unless ``raise_errors`` (or ``FLAMAPY_RAISE_ERRORS=1``) asks for
        the 3.0 contract, which raises it.
        """
        self.last_result = None
        try:
            backend_arg = call_kwargs.pop('backend', None)
            allow_approximate = call_kwargs.pop('allow_approximate', None)
            operation, model, route = self._prepare_operation(
                descriptor, backend_arg, call_kwargs, allow_approximate)
            # The hash is always the source feature model's (memoized there), whichever
            # backend model the operation actually runs on.
            envelope = run_and_wrap(
                operation, model,
                operation_name=descriptor.name, plugin=self._plugin_name_for(model),
                model_hash=self.fm_model.canonical_hash())
            if descriptor.result_adapter is not None:
                envelope = dataclasses.replace(
                    envelope, value=descriptor.result_adapter(envelope.value))
            envelope = _stamp(envelope, route, model)
            self.last_result = envelope
            return envelope.value
        except FlamaException as exception:
            if _raise_errors(self.raise_errors):
                raise
            logger.error("Error: %s", exception)
            warnings.warn(
                "Returning None on operation errors is deprecated: flamapy 3.0 will raise "
                "the FlamaException instead. Catch FlamaException rather than checking for "
                "None.", DeprecationWarning, stacklevel=3)
            return None

    def _plugin_name_for(self, model: VariabilityModel) -> Optional[str]:
        try:
            return self.discover_metamodel.plugins.get_plugin_by_variability_model(model).name
        except PluginNotFound:
            return None

    def run_async(self, operation: str, **kwargs: Any) -> Job:
        """Run a facade operation asynchronously; returns a :class:`Job` immediately.

        ``operation`` is the facade name (e.g. ``'configurations_number'``); ``kwargs``
        are the same arguments the synchronous method takes (including ``backend=``).
        ``job.result(timeout=...)`` waits for the value, raising ``OperationTimeout`` on
        expiry (after requesting cooperative cancellation) — unlike the 2.x synchronous
        methods, errors are **raised**, not swallowed into ``None``.

        Everything after choosing the backend runs inside the job — including the
        fm->backend transformation (e.g. BDD compilation, often the expensive step on large
        models) — so the timeout covers it and preparation errors (unknown backend,
        invalid inputs) are raised by ``job.result()``. The envelope (``job.envelope()``)
        carries the same provenance as the synchronous ``last_result``; the warning about a
        backend that ignores part of the model is emitted here, by the call itself.
        """
        method = getattr(type(self), operation, None)
        descriptor = getattr(method, '_facade_descriptor', None)
        if descriptor is None or getattr(method, '_facade_kind', None) != 'operation':
            raise FlamaException(f"'{operation}' is not a facade analysis operation.")
        call_kwargs = dict(kwargs)
        backend_arg = call_kwargs.pop('backend', None)
        allow_approximate = call_kwargs.pop('allow_approximate', None)
        # Decided (and warned about) on the caller's thread: the route belongs to this job
        # alone, and a warning raised from the worker would point into the thread pool.
        route = self._route(descriptor, backend_arg)
        _warn_level_gap(route)

        def task(interrupt_event: threading.Event) -> OperationResult[Any]:
            prepared, model, job_route = self._prepare_operation(
                descriptor, backend_arg, call_kwargs, allow_approximate, route)
            if interrupt_event.is_set():
                # The deadline expired (or cancel() was called) during preparation: the
                # caller has already given up, so don't start the operation at all.
                raise OperationTimeout(
                    f"'{descriptor.name}' was cancelled before execution started.")
            if isinstance(prepared, Interruptible):
                prepared.set_interrupt_event(interrupt_event)
            envelope = run_and_wrap(
                prepared, model,
                operation_name=descriptor.name, plugin=self._plugin_name_for(model),
                model_hash=self.fm_model.canonical_hash())
            return _stamp(envelope, job_route, model)

        return default_engine().submit_call(task, result_adapter=descriptor.result_adapter)

    def iter_configurations(self, backend: Optional[str] = None) -> Iterator[Configuration]:
        """Iterate the valid configurations, yielding each as the solver produces it.

        Unlike :meth:`configurations` (whose historical default is bdd), the backend
        defaults to ``sat`` — the streaming-capable implementation. Non-streaming
        backends fall back to full enumeration first. Same errors contract as
        :meth:`run_async` (raises, never ``None``).
        """
        descriptor = type(self).configurations._facade_descriptor  # type: ignore[attr-defined]
        operation, model, _ = self._prepare_operation(descriptor, backend or 'sat', {})
        if isinstance(operation, StreamingOperation):
            return operation.iter_execute(model)
        operation.execute(model)
        return iter(operation.get_result())


# One discovery instance, reused to install the operations and to run producers (which have no
# per-facade instance to hold their own).
_DISCOVERY = DiscoverMetamodels()


def _run_producer(descriptor: OperationDescriptor, call_kwargs: Dict[str, Any]) -> Any:
    """Run a 'producer' operation — one that *creates* a model instead of analysing one.

    Producers take no input model, so the operation is instantiated directly and executed with no
    model. Same FlamaException -> None contract as :meth:`FLAMAFeatureModel._run_operation`;
    ``FLAMAPY_RAISE_ERRORS=1`` makes it raise instead (producers have no instance to carry
    ``raise_errors``).
    """
    try:
        operation_class = next(
            (op for op in _DISCOVERY.get_operations() if op.__name__ == descriptor.operation), None)
        if operation_class is None:
            raise FlamaException(f"Operation '{descriptor.operation}' was not discovered")
        operation = operation_class()
        for input_spec in descriptor.inputs:
            value = call_kwargs.get(input_spec.name)
            if value is not None and input_spec.setter is not None:
                getattr(operation, input_spec.setter)(value)
        operation.execute(None)
        result = operation.get_result()
        if descriptor.result_adapter is not None:
            result = descriptor.result_adapter(result)
        return result
    except FlamaException as exception:
        if _raise_errors(None):
            raise
        logger.error("Error: %s", exception)
        warnings.warn(
            "Returning None on operation errors is deprecated: flamapy 3.0 will raise "
            "the FlamaException instead. Catch FlamaException rather than checking for "
            "None.", DeprecationWarning, stacklevel=3)
        return None


_SELECTABLE_NOTE = (
    '\n\n``backend`` chooses the plugin that runs the operation (``"auto"`` lets the query '
    'planner choose); ``allow_approximate`` only has an effect with ``backend="auto"``.')


def _make_operation_method(descriptor: OperationDescriptor) -> Any:
    """Build a real callable from a descriptor.

    Operations become instance methods ``(self, *inputs[, backend])`` dispatching via
    ``_run_operation``; producers become plain functions ``(*inputs)`` (wrapped as a
    ``staticmethod`` by the installer) dispatching via ``_run_producer``.
    """
    producer = descriptor.kind == 'producer'
    parameters = [] if producer else [
        inspect.Parameter('self', inspect.Parameter.POSITIONAL_OR_KEYWORD)]
    for input_spec in descriptor.inputs:
        default = inspect.Parameter.empty if input_spec.required else input_spec.default
        parameters.append(inspect.Parameter(
            input_spec.name, inspect.Parameter.POSITIONAL_OR_KEYWORD,
            default=default, annotation=input_spec.type))
    if descriptor.selectable_backend:
        parameters.append(inspect.Parameter(
            'backend', inspect.Parameter.POSITIONAL_OR_KEYWORD, default=None,
            annotation=Optional[str]))
        # Only meaningful under backend='auto': let the planner pick approximate backends.
        parameters.append(inspect.Parameter(
            'allow_approximate', inspect.Parameter.KEYWORD_ONLY, default=None,
            annotation=Optional[bool]))
    signature = inspect.Signature(parameters)

    def method(*args: Any, **kwargs: Any) -> Any:
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()
        call_kwargs = dict(bound.arguments)
        if producer:
            return _run_producer(descriptor, call_kwargs)
        instance = call_kwargs.pop('self')
        return instance._run_operation(descriptor, call_kwargs)

    method.__name__ = descriptor.name
    method.__qualname__ = f'{FLAMAFeatureModel.__name__}.{descriptor.name}'
    method.__doc__ = descriptor.doc + (_SELECTABLE_NOTE if descriptor.selectable_backend else '')
    method.__signature__ = signature  # type: ignore[attr-defined]
    # Let the CLI/REST/tests tell analysis ops from producers/transformers without re-discovering.
    setattr(method, '_facade_kind', descriptor.kind)
    setattr(method, '_facade_descriptor', descriptor)
    return method


def _install_operations(cls: type) -> None:
    for name, descriptor in _DISCOVERY.available_operations().items():
        method = _make_operation_method(descriptor)
        setattr(cls, name, staticmethod(method) if descriptor.kind == 'producer' else method)


# Async/streaming API methods, not descriptor-generated operations: the CLI generator and
# the descriptor lock test filter on _facade_kind != 'operation'.
FLAMAFeatureModel.plan._facade_kind = 'api'  # type: ignore[attr-defined]
FLAMAFeatureModel.run_async._facade_kind = 'api'  # type: ignore[attr-defined]
FLAMAFeatureModel.iter_configurations._facade_kind = 'api'  # type: ignore[attr-defined]

_install_operations(FLAMAFeatureModel)
