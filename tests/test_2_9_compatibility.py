"""2.9, the release after 2.6.0, keeps the 2.6 behaviour of existing calls; the new knobs follow
the facade's precedence rules (per call > model > environment), and the manifests agree with the
operation classes."""
import importlib

import pytest

from flamapy.core.discover import DiscoverMetamodels
from flamapy.core.exceptions import FlamaException
from flamapy.interfaces.python.flamapy_feature_model import FLAMAFeatureModel

VALID_MODEL = "./resources/models/simple/valid_model.uvl"
CONFIG = {"eCommerce": True, "Server": True}


@pytest.mark.parametrize("default", ["bdd", "z3", "sat"])
def test_newly_selectable_operations_ignore_the_default_backend(default, monkeypatch):
    reference = FLAMAFeatureModel(VALID_MODEL)
    expected_sets = reference.atomic_sets()
    expected_commonality = reference.commonality(CONFIG)
    assert FLAMAFeatureModel(VALID_MODEL, default).atomic_sets() == expected_sets
    assert FLAMAFeatureModel(VALID_MODEL, default).commonality(CONFIG) == expected_commonality
    monkeypatch.setenv("FLAMAPY_BACKEND", default)
    assert FLAMAFeatureModel(VALID_MODEL).atomic_sets() == expected_sets
    assert FLAMAFeatureModel(VALID_MODEL).commonality(CONFIG) == expected_commonality


def test_per_call_backend_still_selects_them():
    model = FLAMAFeatureModel(VALID_MODEL)
    assert model.commonality(CONFIG, backend="bdd") == model.commonality(CONFIG)
    model.atomic_sets(backend="sat")
    assert model.last_result is not None and model.last_result.backend == "pysat"


def test_explicit_false_overrides_the_environment(monkeypatch):
    monkeypatch.setenv("FLAMAPY_ALLOW_APPROXIMATE", "1")
    assert FLAMAFeatureModel(VALID_MODEL)._approximate_allowed(None) is True
    assert FLAMAFeatureModel(VALID_MODEL, allow_approximate=False)._approximate_allowed(None) is False
    monkeypatch.setenv("FLAMAPY_RAISE_ERRORS", "1")
    lenient = FLAMAFeatureModel(VALID_MODEL, raise_errors=False)
    assert lenient.satisfiable(backend="no_such_backend") is None
    with pytest.raises(FlamaException):
        FLAMAFeatureModel(VALID_MODEL).satisfiable(backend="no_such_backend")


def test_flags_are_keyword_only():
    with pytest.raises(TypeError):
        FLAMAFeatureModel(VALID_MODEL, None, True)  # type: ignore[misc]


def test_producers_follow_flamapy_raise_errors(monkeypatch):
    assert FLAMAFeatureModel.generate_random_feature_model(language_level="nonsense") is None
    monkeypatch.setenv("FLAMAPY_RAISE_ERRORS", "1")
    with pytest.raises(FlamaException, match="language level"):
        FLAMAFeatureModel.generate_random_feature_model(language_level="nonsense")


def test_selectable_docstrings_explain_allow_approximate():
    assert "allow_approximate" in FLAMAFeatureModel.core_features.__doc__
    assert "allow_approximate" not in (FLAMAFeatureModel.leaf_features.__doc__ or "")


def test_manifest_exactness_matches_the_operation_classes():
    """The planner reads exactness from the manifests, the result envelope from the classes."""
    mismatches = []
    for plugin in DiscoverMetamodels().plugins:
        for operation in plugin.operations:
            descriptor = getattr(operation, "facade", None)
            if descriptor is None:
                continue
            declared = plugin.manifest.capability(descriptor.name).exact
            if getattr(operation, "exact", True) != declared:
                mismatches.append(f"{operation.__name__}: class {getattr(operation, 'exact', True)},"
                                  f" manifest {declared}")
    assert not mismatches


def test_metrics_skip_a_metamodel_whose_manifest_refuses_the_model(monkeypatch):
    import dataclasses  # noqa: PLC0415
    bdd = importlib.import_module("flamapy.metamodels.bdd_metamodel")
    monkeypatch.setattr(bdd, "MANIFEST", dataclasses.replace(bdd.MANIFEST, max_features=3))
    discover = DiscoverMetamodels()
    feature_model = discover.use_transformation_t2m(VALID_MODEL, "fm")
    sat_model = discover.use_transformation_m2m(feature_model, "pysat")
    metrics = discover.get_operation(sat_model, "PySATMetrics")
    metrics.execute(sat_model)
    assert "bdd" in metrics.get_skipped()
    assert "limit of 3" in metrics.get_skipped()["bdd"]
