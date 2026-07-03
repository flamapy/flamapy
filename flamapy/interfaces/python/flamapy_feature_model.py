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
from enum import Enum
from typing import Any, Dict, Optional, Union

from flamapy.core.discover import DiscoverMetamodels
from flamapy.core.exceptions import FlamaException
from flamapy.core.models import VariabilityModel
from flamapy.core.operations import OperationDescriptor
from flamapy.metamodels.configuration_metamodel.models import Configuration
from flamapy.metamodels.fm_metamodel.models import FeatureModel

logger = logging.getLogger(__name__)


class Backend(str, Enum):
    """Analysis backend identifier.

    Retained so the REST layer can offer a backend dropdown; the facade itself no longer switches on
    it — it resolves the backend dynamically to a transformation extension.
    """

    SAT = "sat"
    BDD = "bdd"
    Z3 = "z3"
    SHARPSAT = "sharpsat"


# Facade backend name -> fm-to-backend transformation extension (the only non-identity mapping).
_BACKEND_ALIAS = {"sat": "pysat"}


class FLAMAFeatureModel:
    """A feature model together with the analysis operations discovered from the installed plugins.

    Operation methods are generated from their OperationDescriptors (see the module docstring); call
    them as normal methods, e.g. ``FLAMAFeatureModel(path).satisfiable()``.
    """

    def __init__(self, model_path: str, backend: Optional[str] = None) -> None:
        """``model_path`` is the filesystem path to the model (UVL, FaMaXML or FeatureIDE).

        ``backend`` optionally sets a workspace-wide default backend ("sat", "bdd" or "z3") for
        every operation that supports more than one. When left as ``None`` each operation keeps its
        historical default, so existing code behaves exactly as before.
        """
        self.model_path = model_path
        self.discover_metamodel = DiscoverMetamodels()
        self.fm_model = self._read(model_path)
        self.backend = Backend(backend) if backend is not None else None
        self._backend_models: Dict[str, VariabilityModel] = {}

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

    def _model_for(
        self, descriptor: OperationDescriptor, backend_arg: Optional[str]
    ) -> VariabilityModel:
        """Resolve the operation's target model, lazily transforming (and caching) fm->backend.

        The backend is the per-call one > workspace default > the operation's default (for
        backend-selectable ops), or simply the fixed default. When it resolves to ``None`` (an
        fm-level op, or a selectable op with no backend requested) the operation runs on the feature
        model directly. Otherwise the name is mapped to a transformation extension (only
        ``sat -> pysat`` differs) and cached per extension.
        """
        if descriptor.selectable_backend:
            resolved = backend_arg or self.backend or descriptor.default_backend
        else:
            resolved = descriptor.default_backend
        if resolved is None:
            return self.fm_model
        name = resolved.value if isinstance(resolved, Backend) else str(resolved)
        extension = _BACKEND_ALIAS.get(name, name)
        if extension not in self._backend_models:
            self._backend_models[extension] = self.discover_metamodel.use_transformation_m2m(
                self.fm_model, extension)
        return self._backend_models[extension]

    def _run_operation(
        self, descriptor: OperationDescriptor, call_kwargs: Dict[str, Any]
    ) -> Any:
        """Resolve model + operation, wire inputs, execute, and marshal the result.

        Preserves the facade's historical contract: any :class:`FlamaException` is logged and the
        call returns ``None``.
        """
        try:
            backend_arg = call_kwargs.pop('backend', None)
            model = self._model_for(descriptor, backend_arg)
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
            operation.execute(model)
            result = operation.get_result()
            if descriptor.result_adapter is not None:
                result = descriptor.result_adapter(result)
            return result
        except FlamaException as exception:
            logger.error("Error: %s", exception)
            return None


# One discovery instance, reused to install the operations and to run producers (which have no
# per-facade instance to hold their own).
_DISCOVERY = DiscoverMetamodels()


def _run_producer(descriptor: OperationDescriptor, call_kwargs: Dict[str, Any]) -> Any:
    """Run a 'producer' operation — one that *creates* a model instead of analysing one.

    Producers take no input model, so the operation is instantiated directly and executed with no
    model. Same FlamaException -> None contract as :meth:`FLAMAFeatureModel._run_operation`.
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
        logger.error("Error: %s", exception)
        return None


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
    method.__doc__ = descriptor.doc
    method.__signature__ = signature  # type: ignore[attr-defined]
    # Let the CLI/REST/tests tell analysis ops from producers/transformers without re-discovering.
    setattr(method, '_facade_kind', descriptor.kind)
    setattr(method, '_facade_descriptor', descriptor)
    return method


def _install_operations(cls: type) -> None:
    for name, descriptor in _DISCOVERY.available_operations().items():
        method = _make_operation_method(descriptor)
        setattr(cls, name, staticmethod(method) if descriptor.kind == 'producer' else method)


_install_operations(FLAMAFeatureModel)
