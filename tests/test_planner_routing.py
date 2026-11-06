"""The opt-in query planner: routing under backend='auto' / FLAMAPY_BACKEND=auto.

The bridge invariant is asserted throughout: without the opt-in switch, results and
provenance are identical to the historical behavior.
"""
import pytest

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

# --- routing on the declared language levels, exactness and the models already built --------

GROUP_CARDINALITY_MODEL = './resources/models/simple/group_cardinalities.uvl'
STRING_MODEL = './resources/models/simple/string_constraints.uvl'


def _language_level(fm):
    return str(fm._language_level())


def test_auto_routes_group_cardinalities_like_boolean_models():
    fm = FLAMAFeatureModel(GROUP_CARDINALITY_MODEL, backend='auto')
    assert 'GROUP_CARDINALITY' in _language_level(fm)
    assert fm.satisfiable() is True and fm.last_result.backend == 'pysat'
    assert fm.configurations_number() == 16 and fm.last_result.backend == 'bdd'
    assert fm.dead_features() == [] and fm.last_result.backend == 'pysat'


def test_auto_routes_typed_models_with_strings_to_z3_and_never_to_the_structural_core():
    fm = FLAMAFeatureModel(STRING_MODEL, backend='auto')
    assert 'STRING_CONSTRAINTS' in _language_level(fm)
    assert fm.satisfiable() is True and fm.last_result.backend == 'z3'
    core = fm.core_features()
    assert fm.last_result.backend == 'z3'
    assert 'INFORMATION_TYPE' in core  # implied by a constraint: the structural core misses it


def test_structural_core_features_only_with_allow_approximate():
    typed = FLAMAFeatureModel(TYPED_MODEL, backend='auto')
    typed.core_features()
    assert typed.last_result.backend == 'z3'
    typed.core_features(allow_approximate=True)
    assert typed.last_result.backend == 'fm'
    assert 'approximate' in typed.last_result.planner


def test_approximate_counting_needs_permission():
    pytest.importorskip('flamapy.metamodels.sharpsat_metamodel')
    fm = FLAMAFeatureModel(VALID_MODEL, backend='auto')
    fm.configurations_number()
    assert fm.last_result.backend == 'bdd'
    chosen = fm._plan_operation('configurations_number', allow_approximate=True)
    assert 'sharpsat_metamodel' in chosen.alternatives  # a candidate now, still not the cheapest


def test_models_already_built_cost_nothing_to_the_planner():
    fm = FLAMAFeatureModel(VALID_MODEL, backend='auto')
    before = fm._plan_operation('configurations_number')
    fm.configurations_number()  # builds the BDD
    after = fm._plan_operation('configurations_number')
    assert 'bdd model already built' in after.rationale
    assert after.estimated_cost < before.estimated_cost


def test_plan_is_public_and_only_for_selectable_operations():
    from flamapy.core.exceptions import FlamaException

    fm = FLAMAFeatureModel(VALID_MODEL)
    chosen = fm.plan('configurations_number')
    assert chosen.target_extension == 'bdd'
    assert fm.plan('core_features', allow_approximate=True).plugin_name == 'pysat_metamodel'
    with pytest.raises(FlamaException):
        fm.plan('explain_void_model')  # fixed backend: nothing to plan


def test_raise_errors_opts_into_the_3_0_contract():
    from flamapy.core.exceptions import FlamaException

    lenient = FLAMAFeatureModel(VALID_MODEL)
    assert lenient.satisfiable(backend='sharpsat_is_not_a_backend') is None
    strict = FLAMAFeatureModel(VALID_MODEL, raise_errors=True)
    with pytest.raises(FlamaException):
        strict.satisfiable(backend='sharpsat_is_not_a_backend')
    assert strict.satisfiable() is True
