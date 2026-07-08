"""The opt-in query planner: routing under backend='auto' / FLAMAPY_BACKEND=auto.

The bridge invariant is asserted throughout: without the opt-in switch, results and
provenance are identical to the historical behavior.
"""
from flamapy.interfaces.python.flamapy_feature_model import FLAMAFeatureModel

VALID_MODEL = './resources/models/simple/valid_model.uvl'
TYPED_MODEL = './resources/models/simple/typed_attributes.uvl'


def test_auto_keeps_historical_defaults_on_boolean_models():
    default = FLAMAFeatureModel(VALID_MODEL)
    auto = FLAMAFeatureModel(VALID_MODEL, backend='auto')

    assert auto.satisfiable() == default.satisfiable()
    assert auto.last_result.backend == default.last_result.backend == 'pysat'
    assert auto.last_result.planner.startswith('auto:')
    assert default.last_result.planner is None

    assert auto.configurations_number() == default.configurations_number() == 816
    assert auto.last_result.backend == default.last_result.backend == 'bdd'


def test_auto_routes_typed_models_to_z3():
    auto = FLAMAFeatureModel(TYPED_MODEL, backend='auto')
    assert auto.satisfiable() is True
    assert auto.last_result.backend == 'z3'
    assert 'z3' in auto.last_result.planner


def test_per_call_auto():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert fm.satisfiable(backend='auto') is True
    assert fm.last_result.planner.startswith('auto:')
    # Next call without auto reverts to historical behavior.
    assert fm.satisfiable() is True
    assert fm.last_result.planner is None


def test_explicit_backend_beats_auto_and_is_recorded():
    fm = FLAMAFeatureModel(VALID_MODEL, backend='auto')
    assert fm.satisfiable(backend='bdd') is True
    assert fm.last_result.backend == 'bdd'
    assert fm.last_result.planner == 'explicit'


def test_env_var_engages_the_planner(monkeypatch):
    monkeypatch.setenv('FLAMAPY_BACKEND', 'auto')
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert fm.satisfiable() is True
    assert fm.last_result.planner.startswith('auto:')


def test_fixed_backend_operations_ignore_auto():
    # explain_void_model is not backend-selectable; auto must not interfere.
    fm = FLAMAFeatureModel(VALID_MODEL, backend='auto')
    assert fm.explain_void_model() == []
    assert fm.last_result.backend == 'pysat_diagnosis'


def test_plan_helper_reports_choice_and_alternatives():
    fm = FLAMAFeatureModel(VALID_MODEL)
    chosen = fm._plan_operation('configurations_number')
    assert chosen.target_extension == 'bdd'
    assert chosen.transformation_chain == (('fm', 'bdd'),)
    assert 'historical default backend' in chosen.rationale
    assert 'pysat_metamodel' in chosen.alternatives