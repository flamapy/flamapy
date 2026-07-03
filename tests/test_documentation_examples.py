"""Executable versions of every code example in the documentation.

Each operation page under ``flamapy_docs/_operations`` ships up to three runnable
snippets: the easy-to-use Python facade, the ``DiscoverMetamodels`` framework call
and the advanced (manual transformation) flow.  The tests below mirror those
snippets so the documentation stays runnable and any regression in a documented
operation is caught here.

The Z3 operations run against a model with typed attributes; ``flamapy-z3`` is a
dependency of the ``flamapy`` distribution, so they are always exercised.
"""
import pytest

from flamapy.core.discover import DiscoverMetamodels
from flamapy.interfaces.python.flamapy_feature_model import FLAMAFeatureModel

VALID_MODEL = "./resources/models/simple/valid_model.uvl"
VALID_CONFIG = "./resources/configurations/valid_configuration.csvconf"
# Feature model carrying typed attributes (Integer feature + Real attributes),
# required by the Z3 examples.
TYPED_MODEL = "./resources/models/simple/typed_attributes.uvl"


# ---------------------------------------------------------------------------
# Python facade examples (flamapy_docs/_operations/*.md, "facade usage")
# ---------------------------------------------------------------------------

def test_facade_atomic_sets():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert len(fm.atomic_sets()) == 17


def test_facade_average_branching_factor():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert fm.average_branching_factor() == 2.45


def test_facade_count_leafs():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert fm.count_leafs() == 17


def test_facade_estimated_number_of_configurations():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert fm.estimated_number_of_configurations() == 1904


def test_facade_feature_ancestors():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert fm.feature_ancestors("v74") == ["PHP", "Server", "eCommerce"]


def test_facade_leaf_features():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert len(fm.leaf_features()) == 17


def test_facade_max_depth():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert fm.max_depth() == 4


def test_facade_core_features():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert len(fm.core_features()) == 12


def test_facade_dead_features():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert fm.dead_features() == []


def test_facade_false_optional_features():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert fm.false_optional_features() == []


def test_facade_filter():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert len(fm.filter(VALID_CONFIG)) == 68


def test_facade_configurations_number():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert fm.configurations_number() == 816


def test_facade_configurations():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert len(fm.configurations()) == 816


def test_facade_commonality():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert isinstance(fm.commonality(VALID_CONFIG), float)


def test_facade_satisfiable_configuration():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert fm.satisfiable_configuration(VALID_CONFIG, False) is True


def test_facade_satisfiable():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert fm.satisfiable() is True


def test_facade_metrics():
    fm = FLAMAFeatureModel(VALID_MODEL)
    result = fm.metrics()
    assert isinstance(result, list) and len(result) == 61
    assert all("name" in entry and "result" in entry for entry in result)


def test_facade_variation_points():
    fm = FLAMAFeatureModel(VALID_MODEL)
    result = fm.variation_points()
    assert isinstance(result, dict) and len(result) == 7
    # Keys and values are feature-name strings.
    assert all(isinstance(k, str) for k in result)
    assert all(isinstance(v, str) for variants in result.values() for v in variants)


def test_facade_backbone():
    fm = FLAMAFeatureModel(VALID_MODEL)
    result = fm.backbone()
    assert isinstance(result, dict)
    assert set(result.keys()) == {"core", "dead"}


def test_facade_homogeneity():
    fm = FLAMAFeatureModel(VALID_MODEL)
    result = fm.homogeneity()
    assert isinstance(result, float) and 0.0 <= result <= 1.0


def test_facade_product_distribution():
    fm = FLAMAFeatureModel(VALID_MODEL)
    result = fm.product_distribution()
    assert isinstance(result, list)
    # The distribution sums to the total number of configurations.
    assert sum(result) == 816


def test_facade_variability():
    fm = FLAMAFeatureModel(VALID_MODEL)
    result = fm.variability()
    assert isinstance(result, tuple) and len(result) == 2


def test_facade_variant_features():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert len(fm.variant_features()) == 16


def test_facade_unique_features():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert fm.unique_features() == []


def test_facade_pure_optional_features():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert sorted(fm.pure_optional_features()) == ["ADVANCED", "BASIC", "CreditCard", "Mobile"]


def test_facade_feature_inclusion_probability():
    fm = FLAMAFeatureModel(VALID_MODEL)
    result = fm.feature_inclusion_probability()
    assert isinstance(result, dict)
    assert all(0.0 <= p <= 1.0 for p in result.values())


def test_facade_configurations_with_n_features():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert isinstance(fm.configurations_with_n_features(5), list)


def test_facade_sampling():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert len(fm.sampling(5)) == 5


def test_facade_diagnosis():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert isinstance(fm.diagnosis(VALID_CONFIG, VALID_CONFIG), list)


def test_facade_conflict():
    fm = FLAMAFeatureModel(VALID_MODEL)
    assert isinstance(fm.conflict(VALID_CONFIG, VALID_CONFIG), list)


# ---------------------------------------------------------------------------
# Framework examples (flamapy_docs/_operations/*.md, "framework usage")
# `dm.use_operation_from_file(...)` for operations that need no configuration.
# ---------------------------------------------------------------------------

FRAMEWORK_OPERATIONS = [
    "AtomicSets",                       # base-class name resolves to FMAtomicSets
    "FMAverageBranchingFactor",
    "FMCountLeafs",
    "FMEstimatedConfigurationsNumber",
    "FMLeafFeatures",
    "FMMaxDepthTree",
    "FMMetrics",
    "FMVariationPoints",
    "PySATBackbone",
    "PySATConfigurations",
    "PySATConfigurationsNumber",
    "PySATCoreFeatures",
    "PySATDeadFeatures",
    "PySATFalseOptionalFeatures",
    "PySATSatisfiable",
    "BDDFeatureInclusionProbability",
    "BDDHomogeneity",
    "BDDProductDistribution",
    "BDDPureOptionalFeatures",
    "BDDUniqueFeatures",
    "BDDVariability",
    "BDDVariantFeatures",
    "Sampling",                         # base-class name resolves to a Sampling op
]


@pytest.mark.parametrize("operation_name", FRAMEWORK_OPERATIONS)
def test_framework_use_operation_from_file(operation_name):
    dm = DiscoverMetamodels()
    result = dm.use_operation_from_file(operation_name, VALID_MODEL)
    assert result is not None


def test_framework_diagnosis_requires_configuration():
    # Diagnosis/conflict are OperationWithConfiguration: they need configuration_file.
    dm = DiscoverMetamodels()
    result = dm.use_operation_from_file(
        "PySATDiagnosis", VALID_MODEL, configuration_file=VALID_CONFIG
    )
    assert isinstance(result, list)


def test_framework_conflict_requires_configuration():
    dm = DiscoverMetamodels()
    result = dm.use_operation_from_file(
        "PySATConflict", VALID_MODEL, configuration_file=VALID_CONFIG
    )
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Advanced framework examples (manual transformation + get_operation)
# ---------------------------------------------------------------------------

def test_advanced_dead_features():
    dm = DiscoverMetamodels()
    feature_model = dm.use_transformation_t2m(VALID_MODEL, "fm")
    sat_model = dm.use_transformation_m2m(feature_model, "pysat")
    operation = dm.get_operation(sat_model, "PySATDeadFeatures")
    operation.execute(sat_model)
    assert operation.get_result() == []


def test_advanced_homogeneity():
    dm = DiscoverMetamodels()
    feature_model = dm.use_transformation_t2m(VALID_MODEL, "fm")
    bdd_model = dm.use_transformation_m2m(feature_model, "bdd")
    operation = dm.get_operation(bdd_model, "BDDHomogeneity")
    operation.execute(bdd_model)
    assert isinstance(operation.get_result(), float)


def test_advanced_configurations_with_n_features():
    dm = DiscoverMetamodels()
    feature_model = dm.use_transformation_t2m(VALID_MODEL, "fm")
    bdd_model = dm.use_transformation_m2m(feature_model, "bdd")
    operation = dm.get_operation(bdd_model, "BDDConfigurationsWithNFeatures")
    operation.set_n_features(5)
    operation.execute(bdd_model)
    assert isinstance(list(operation.get_result()), list)


def test_advanced_diagnosis_with_configuration_and_test_case():
    dm = DiscoverMetamodels()
    feature_model = dm.use_transformation_t2m(VALID_MODEL, "fm")
    sat_model = dm.use_transformation_m2m(feature_model, "pysat_diagnosis")
    configuration = dm.use_transformation_t2m(VALID_CONFIG, "configuration")
    test_case = dm.use_transformation_t2m(VALID_CONFIG, "configuration")
    operation = dm.get_operation(sat_model, "PySATDiagnosis")
    operation.set_configuration(configuration)
    operation.set_test_case(test_case)
    operation.execute(sat_model)
    assert isinstance(operation.get_result(), list)


def test_advanced_conflict_with_configuration_and_test_case():
    dm = DiscoverMetamodels()
    feature_model = dm.use_transformation_t2m(VALID_MODEL, "fm")
    sat_model = dm.use_transformation_m2m(feature_model, "pysat_diagnosis")
    configuration = dm.use_transformation_t2m(VALID_CONFIG, "configuration")
    test_case = dm.use_transformation_t2m(VALID_CONFIG, "configuration")
    operation = dm.get_operation(sat_model, "PySATConflict")
    operation.set_configuration(configuration)
    operation.set_test_case(test_case)
    operation.execute(sat_model)
    assert isinstance(operation.get_result(), list)


# ---------------------------------------------------------------------------
# Z3 examples (optional plugin; require a model with typed attributes)
# ---------------------------------------------------------------------------

def test_facade_all_feature_bounds():
    fm = FLAMAFeatureModel(TYPED_MODEL)
    result = fm.all_feature_bounds()
    assert result["Scoops"]["min"] == 1
    assert result["Scoops"]["max"] == 5
    assert result["Scoops"]["bounded"] is True


def test_facade_feature_bounds():
    fm = FLAMAFeatureModel(TYPED_MODEL)
    result = fm.feature_bounds("Scoops")
    assert result["min"] == 1
    assert result["max"] == 5


def test_advanced_all_feature_bounds():
    dm = DiscoverMetamodels()
    feature_model = dm.use_transformation_t2m(TYPED_MODEL, "fm")
    z3_model = dm.use_transformation_m2m(feature_model, "z3")
    operation = dm.get_operation(z3_model, "Z3AllFeatureBounds")
    operation.execute(z3_model)
    assert "Scoops" in operation.get_result()


def test_advanced_variable_bounds():
    dm = DiscoverMetamodels()
    feature_model = dm.use_transformation_t2m(TYPED_MODEL, "fm")
    z3_model = dm.use_transformation_m2m(feature_model, "z3")
    operation = dm.get_operation(z3_model, "Z3VariableBounds")
    operation.set_variable_name("Scoops")
    operation.execute(z3_model)
    result = operation.get_result()
    assert result["min_bound"] == 1
    assert result["max_bound"] == 5


def test_advanced_attribute_optimization():
    from flamapy.metamodels.z3_metamodel.operations.interfaces import OptimizationGoal

    dm = DiscoverMetamodels()
    feature_model = dm.use_transformation_t2m(TYPED_MODEL, "fm")
    z3_model = dm.use_transformation_m2m(feature_model, "z3")
    operation = dm.get_operation(z3_model, "Z3AttributeOptimization")
    operation.set_attributes({"Price": OptimizationGoal.MINIMIZE})
    operation.execute(z3_model)
    assert isinstance(operation.get_result(), list)
