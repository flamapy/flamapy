"""Facade tests for the newly exposed operations: attribute optimization, minimum
configuration, t-wise sampling, and the sharpsat backend."""
import itertools
import os
import tempfile

import pytest

from flamapy.interfaces.python.flamapy_feature_model import FLAMAFeatureModel

# flamapy-sharpsat is an optional extra; skip the sharpsat-backend tests when it is
# not installed (e.g. the umbrella CI installs flamapy without the sharpsat extra).
try:
    import flamapy.metamodels.sharpsat_metamodel  # noqa: F401
    _SHARPSAT_AVAILABLE = True
except ImportError:
    _SHARPSAT_AVAILABLE = False

requires_sharpsat = pytest.mark.skipif(
    not _SHARPSAT_AVAILABLE, reason="flamapy-sharpsat is not installed"
)

_ATTRIBUTED_UVL = """features
    Root {abstract}
        optional
            A {Cost 3}
            B {Cost 5}
            C {Cost 2}
constraints
    A | B
"""

_PLAIN_UVL = """features
    Root {abstract}
        optional
            A
            B
            C
            D
constraints
    (A | B) => (C <=> D)
    A => !B
"""


def _model(uvl):
    handle, path = tempfile.mkstemp(suffix='.uvl')
    with os.fdopen(handle, 'w') as file:
        file.write(uvl)
    return path


def _sel(configuration):
    return {name for name, value in configuration.elements.items() if value}


# --- attribute optimization -------------------------------------------------

def test_attribute_optimization_sat_minimize():
    fm = FLAMAFeatureModel(_model(_ATTRIBUTED_UVL))
    result = fm.attribute_optimization("Cost", backend="sat")
    assert [_sel(c) for c in result] == [{"A", "Root"}]


def test_attribute_optimization_sat_maximize():
    fm = FLAMAFeatureModel(_model(_ATTRIBUTED_UVL))
    result = fm.attribute_optimization({"Cost": "Maximize"}, backend="sat")
    assert [_sel(c) for c in result] == [{"A", "B", "C", "Root"}]


def test_attribute_optimization_sat_matches_z3():
    path = _model(_ATTRIBUTED_UVL)
    sat = FLAMAFeatureModel(path).attribute_optimization({"Cost": "Minimize"}, backend="sat")
    z3 = FLAMAFeatureModel(path).attribute_optimization({"Cost": "Minimize"}, backend="z3")
    assert {frozenset(_sel(c)) for c in sat} == {frozenset(_sel(c)) for c in z3}


# --- minimum configuration --------------------------------------------------

def test_minimum_configuration():
    # The attributed model has an "A | B" constraint, so the minimum working
    # configuration is Root plus exactly one of A/B.
    fm = FLAMAFeatureModel(_model(_ATTRIBUTED_UVL))
    selected = _sel(fm.minimum_configuration(backend="sat"))
    assert "Root" in selected
    assert len(selected) == 2 and len(selected & {"A", "B"}) == 1


# --- t-wise sampling --------------------------------------------------------

def test_t_wise_sampling_covers_valid_pairs():
    fm = FLAMAFeatureModel(_model(_PLAIN_UVL))
    sample = fm.t_wise_sampling(2, backend="sat")
    selected_sets = [_sel(c) for c in sample]
    # every satisfiable pair is covered; A&B is unsatisfiable (A => !B) so may be absent.
    features = ["A", "B", "C", "D"]
    for f1, f2 in itertools.combinations(features, 2):
        for v1, v2 in itertools.product((True, False), repeat=2):
            covered = any((f1 in s) == v1 and (f2 in s) == v2 for s in selected_sets)
            if not covered:
                assert (f1, f2, v1, v2) == ("A", "B", True, True)


# --- sharpsat backend -------------------------------------------------------

@requires_sharpsat
def test_sharpsat_backend_count_matches_bdd():
    path = _model(_PLAIN_UVL)
    exact = FLAMAFeatureModel(path).configurations_number(backend="bdd")
    approx = FLAMAFeatureModel(path).configurations_number(backend="sharpsat")
    assert approx == exact


@requires_sharpsat
def test_sharpsat_backend_sampling_returns_valid_configurations():
    path = _model(_PLAIN_UVL)
    fm = FLAMAFeatureModel(path)
    sample = fm.sampling(6, with_replacement=True, backend="sharpsat")
    assert len(sample) == 6
    # each sampled configuration is a valid full configuration
    for configuration in sample:
        elements = {f.name: (f.name in _sel(configuration))
                    for f in FLAMAFeatureModel(path).fm_model.get_features()}
        assert FLAMAFeatureModel(path).satisfiable_configuration(elements) is True
