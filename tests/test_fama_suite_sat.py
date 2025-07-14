import pytest

from collections import Counter

from flamapy.metamodels.fm_metamodel.transformations.xml_reader import XMLReader
from flamapy.metamodels.fm_metamodel.models.feature_model import Feature

from flamapy.metamodels.configuration_metamodel.models.configuration import Configuration

from flamapy.metamodels.pysat_metamodel.transformations.fm_to_pysat import FmToPysat
from flamapy.metamodels.pysat_metamodel.operations.pysat_core_features import PySATCoreFeatures
from flamapy.metamodels.pysat_metamodel.operations.pysat_dead_features import PySATDeadFeatures
from flamapy.metamodels.pysat_metamodel.operations.pysat_configurations_number import (
    PySATConfigurationsNumber,
)
from flamapy.metamodels.pysat_metamodel.operations.pysat_configurations import PySATConfigurations
from flamapy.metamodels.pysat_metamodel.operations.pysat_false_optional_features import (
    PySATFalseOptionalFeatures,
)
from flamapy.metamodels.pysat_metamodel.operations.pysat_satisfiable import PySATSatisfiable
from flamapy.metamodels.pysat_metamodel.operations.pysat_filter import PySATFilter
from flamapy.metamodels.pysat_metamodel.operations.pysat_satisfiable_configuration import (
    PySATSatisfiableConfiguration,
)


# This fixture is used to initialize the model, and it can be scoped to each function.
# You may also parameterize this fixture if you have different setups for different tests.
@pytest.fixture(scope="function")
def setup_model(request):
    model_path = request.param
    xmlreader = XMLReader(model_path)
    fm = xmlreader.transform()
    transform = FmToPysat(fm)
    return transform.transform()


# This test is parameterized to run different test cases with different inputs and expected outputs.
@pytest.mark.parametrize(
    "setup_model, expected_output",
    [
        (
            "./resources/models/fama_test_suite/error-guessing/false-optional-features/case1/fof-case1.xml",
            ["C"],
        ),
        (
            "./resources/models/fama_test_suite/error-guessing/false-optional-features/case2/fof-case2.xml",
            ["C", "D"],
        ),
        (
            "./resources/models/fama_test_suite/error-guessing/false-optional-features/case3/fof-case3.xml",
            ["C", "D"],
        ),
        (
            "./resources/models/fama_test_suite/error-guessing/false-optional-features/case4/fof-case4.xml",
            ["C"],
        ),
        (
            "./resources/models/fama_test_suite/error-guessing/false-optional-features/case5/fof-case5.xml",
            ["C"],
        ),
        (
            "./resources/models/fama_test_suite/error-guessing/false-optional-features/case6/fof-case6.xml",
            ["B", "E"],
        ),
    ],
    indirect=["setup_model"],
)
def test_false_optional_operation(setup_model, expected_output):
    model = setup_model
    operation = PySATFalseOptionalFeatures()
    operation.execute(model)
    result = operation.get_false_optional_features()
    result_names = [str(feature) for feature in result]

    assert result_names == expected_output, (
        f"The result {result_names} does not match with the expected output {expected_output}"
    )


@pytest.mark.parametrize(
    "setup_model, expected_output",
    [
        (
            "./resources/models/fama_test_suite/error-guessing/core-features/case1/cf-case1.xml",
            ["A", "B"],
        ),
        (
            "./resources/models/fama_test_suite/error-guessing/core-features/case2/cf-case2.xml",
            ["A", "B"],
        ),
        (
            "./resources/models/fama_test_suite/error-guessing/core-features/case3/cf-case3.xml",
            ["A", "B", "C"],
        ),
        (
            "./resources/models/fama_test_suite/error-guessing/core-features/case4/cf-case4.xml",
            ["A", "B", "C", "E"],
        ),
        (
            "./resources/models/fama_test_suite/error-guessing/core-features/case5/cf-case5.xml",
            ["A", "B", "C", "D"],
        ),
        ("./resources/models/fama_test_suite/error-guessing/core-features/case6/cf-case6.xml", []),
    ],
    indirect=["setup_model"],
)
def test_core_features_operation(setup_model, expected_output):
    model = setup_model
    operation = PySATCoreFeatures()
    operation.execute(model)
    result = operation.get_core_features()
    assert result == expected_output, (
        f"The result {result} does not match with the expected output {expected_output}"
    )


@pytest.mark.parametrize(
    "setup_model, expected_output",
    [
        (
            "./resources/models/fama_test_suite/error-guessing/dead-features/case1/df-case1.xml",
            ["D"],
        ),
        (
            "./resources/models/fama_test_suite/error-guessing/dead-features/case2/df-case2.xml",
            ["E"],
        ),
        (
            "./resources/models/fama_test_suite/error-guessing/dead-features/case3/df-case3.xml",
            ["D"],
        ),
        (
            "./resources/models/fama_test_suite/error-guessing/dead-features/case4/df-case4.xml",
            ["C"],
        ),
        (
            "./resources/models/fama_test_suite/error-guessing/dead-features/case5/df-case5.xml",
            ["A", "B", "C"],
        ),
        (
            "./resources/models/fama_test_suite/error-guessing/dead-features/case6/df-case6.xml",
            ["B"],
        ),
        (
            "./resources/models/fama_test_suite/error-guessing/dead-features/case7/df-case7.xml",
            ["A", "B", "C"],
        ),
        (
            "./resources/models/fama_test_suite/error-guessing/dead-features/case8/df-case8.xml",
            ["B"],
        ),
    ],
    indirect=["setup_model"],
)
def test_dead_features_operation(setup_model, expected_output):
    model = setup_model
    operation = PySATDeadFeatures()
    operation.execute(model)
    result = operation.get_dead_features()
    assert result == expected_output, (
        f"The result {result} does not match the expected output {expected_output}"
    )


@pytest.mark.parametrize(
    "setup_model, expected_output",
    [
        ("./resources/models/fama_test_suite/relationships/mandatory/mandatory.xml", 1),
        ("./resources/models/fama_test_suite/relationships/optional/optional.xml", 2),
        ("./resources/models/fama_test_suite/relationships/alternative/alternative.xml", 2),
        ("./resources/models/fama_test_suite/relationships/or/or.xml", 3),
        ("./resources/models/fama_test_suite/relationships/excludes/excludes.xml", 3),
        ("./resources/models/fama_test_suite/relationships/requires/requires.xml", 3),
        (
            "./resources/models/fama_test_suite/relationships/mandatory-optional/mandatory-optional.xml",
            4,
        ),
        ("./resources/models/fama_test_suite/relationships/mandatory-or/mandatory-or.xml", 9),
        (
            "./resources/models/fama_test_suite/relationships/mandatory-alternative/mandatory-alternative.xml",
            4,
        ),
        (
            "./resources/models/fama_test_suite/relationships/mandatory-requires/mandatory-requires.xml",
            1,
        ),
        (
            "./resources/models/fama_test_suite/relationships/mandatory-requires/mandatory-requires.xml",
            1,
        ),
        (
            "./resources/models/fama_test_suite/relationships/mandatory-excludes/mandatory-excludes.xml",
            0,
        ),
        ("./resources/models/fama_test_suite/relationships/optional-or/optional-or.xml", 20),
        (
            "./resources/models/fama_test_suite/relationships/optional-alternative/optional-alternative.xml",
            9,
        ),
        ("./resources/models/fama_test_suite/relationships/or-alternative/or-alternative.xml", 20),
        ("./resources/models/fama_test_suite/relationships/or-requires/or-requires.xml", 2),
        ("./resources/models/fama_test_suite/relationships/or-excludes/or-excludes.xml", 2),
        (
            "./resources/models/fama_test_suite/relationships/alternative-requires/alternative-requires.xml",
            1,
        ),
        (
            "./resources/models/fama_test_suite/relationships/alternative-excludes/alternative-excludes.xml",
            2,
        ),
        (
            "./resources/models/fama_test_suite/relationships/requires-excludes/requires-excludes.xml",
            2,
        ),
        (
            "./resources/models/fama_test_suite/relationships/allrelationships/allrelationships.xml",
            4,
        ),
        (
            "./resources/models/fama_test_suite/refinement/alternative-oddChildren/alternative-oddChildren.xml",
            0,
        ),
    ],
    indirect=["setup_model"],
)
def test_number_of_configurations_operation(setup_model, expected_output):
    model = setup_model
    operation = PySATConfigurationsNumber()
    operation.execute(model)
    result = operation.get_configurations_number()
    assert result == expected_output, (
        f"The result {result} does not match the expected output {expected_output}"
    )


@pytest.mark.parametrize(
    "setup_model, expected_output",
    [
        ("./resources/models/fama_test_suite/relationships/mandatory/mandatory.xml", [["A", "B"]]),
        (
            "./resources/models/fama_test_suite/relationships/optional/optional.xml",
            [["A"], ["A", "B"]],
        ),
        (
            "./resources/models/fama_test_suite/relationships/alternative/alternative.xml",
            [["A", "B"], ["A", "C"]],
        ),
        (
            "./resources/models/fama_test_suite/relationships/or/or.xml",
            [["A", "B"], ["A", "B", "C"], ["A", "C"]],
        ),
        (
            "./resources/models/fama_test_suite/relationships/excludes/excludes.xml",
            [["A"], ["A", "C"], ["A", "B"]],
        ),
        (
            "./resources/models/fama_test_suite/relationships/requires/requires.xml",
            [["A"], ["A", "C"], ["A", "B", "C"]],
        ),
        (
            "./resources/models/fama_test_suite/relationships/mandatory-optional/mandatory-optional.xml",
            [["A", "B"], ["A", "B", "C", "E"], ["A", "B", "D", "C", "E"], ["A", "B", "D"]],
        ),
        (
            "./resources/models/fama_test_suite/relationships/mandatory-or/mandatory-or.xml",
            [
                ["A", "B", "E", "C"],
                ["A", "B", "E", "F", "C"],
                ["A", "B", "E", "F", "C", "D", "G"],
                ["A", "B", "F", "C"],
                ["A", "B", "E", "C", "D", "G"],
                ["A", "B", "E", "D", "G"],
                ["A", "B", "E", "F", "D", "G"],
                ["A", "B", "F", "C", "D", "G"],
                ["A", "B", "F", "D", "G"],
            ],
        ),
        (
            "./resources/models/fama_test_suite/relationships/mandatory-alternative/mandatory-alternative.xml",
            [
                ["A", "B", "E", "D"],
                ["A", "B", "E", "C", "G"],
                ["A", "B", "F", "C", "G"],
                ["A", "B", "F", "D"],
            ],
        ),
        (
            "./resources/models/fama_test_suite/relationships/mandatory-requires/mandatory-requires.xml",
            [["A", "B", "C"]],
        ),
        (
            "./resources/models/fama_test_suite/relationships/mandatory-excludes/mandatory-excludes.xml",
            [],
        ),
        (
            "./resources/models/fama_test_suite/relationships/optional-or/optional-or.xml",
            [
                ["A", "C"],
                ["A", "C", "D"],
                ["A", "C", "D", "G"],
                ["A", "C", "G"],
                ["A", "B", "F", "C", "G"],
                ["A", "B", "E", "F", "C", "G"],
                ["A", "B", "E", "F", "C"],
                ["A", "B", "E", "F", "C", "D"],
                ["A", "B", "E", "C", "D"],
                ["A", "B", "F", "C", "D"],
                ["A", "B", "F", "C", "D", "G"],
                ["A", "B", "F", "D"],
                ["A", "B", "F", "C"],
                ["A", "B", "E", "C"],
                ["A", "B", "E", "C", "G"],
                ["A", "B", "E", "C", "D", "G"],
                ["A", "B", "E", "D"],
                ["A", "B", "E", "F", "D"],
                ["A", "B", "E", "F", "C", "D", "G"],
                ["A", "D"],
            ],
        ),
        (
            "./resources/models/fama_test_suite/relationships/optional-alternative/optional-alternative.xml",
            [
                ["A", "C"],
                ["A", "D"],
                ["A", "B", "E", "C"],
                ["A", "B", "E", "D"],
                ["A", "B", "E", "D", "G"],
                ["A", "B", "F", "D", "G"],
                ["A", "B", "F", "D"],
                ["A", "D", "G"],
                ["A", "B", "F", "C"],
            ],
        ),
        (
            "./resources/models/fama_test_suite/relationships/or-alternative/or-alternative.xml",
            [
                ["A", "C", "D"],
                ["A", "C", "D", "E", "H"],
                ["A", "C", "D", "E", "I"],
                ["A", "B", "F", "D", "E", "I"],
                ["A", "B", "F", "G", "D", "E", "I"],
                ["A", "B", "F", "G", "D"],
                ["A", "B", "G", "D"],
                ["A", "B", "G", "D", "E", "I"],
                ["A", "B", "F", "D"],
                ["A", "B", "F", "E", "I"],
                ["A", "B", "F", "E", "H"],
                ["A", "B", "F", "D", "E", "H"],
                ["A", "C", "E", "H"],
                ["A", "C", "E", "I"],
                ["A", "B", "G", "E", "I"],
                ["A", "B", "F", "G", "E", "I"],
                ["A", "B", "F", "G", "D", "E", "H"],
                ["A", "B", "F", "G", "E", "H"],
                ["A", "B", "G", "E", "H"],
                ["A", "B", "G", "D", "E", "H"],
            ],
        ),
        (
            "./resources/models/fama_test_suite/relationships/or-requires/or-requires.xml",
            [["A", "C"], ["A", "C", "B"]],
        ),
        (
            "./resources/models/fama_test_suite/relationships/or-excludes/or-excludes.xml",
            [["A", "C"], ["A", "B"]],
        ),
        (
            "./resources/models/fama_test_suite/relationships/alternative-requires/alternative-requires.xml",
            [["A", "C"]],
        ),
        (
            "./resources/models/fama_test_suite/relationships/alternative-excludes/alternative-excludes.xml",
            [["A", "C"], ["A", "B"]],
        ),
        (
            "./resources/models/fama_test_suite/relationships/requires-excludes/requires-excludes.xml",
            [["A"], ["A", "C"]],
        ),
        (
            "./resources/models/fama_test_suite/relationships/allrelationships/allrelationships.xml",
            [
                ["A", "B", "D"],
                ["A", "B", "D", "C", "F"],
                ["A", "B", "E", "C", "F"],
                ["A", "B", "E", "C", "F", "G"],
            ],
        ),
        (
            "./resources/models/fama_test_suite/refinement/alternative-oddChildren/alternative-oddChildren.xml",
            [],
        ),
    ],
    indirect=["setup_model"],
)
def test_configurations_operation(setup_model, expected_output):
    model = setup_model
    operation = PySATConfigurations()

    operation.execute(model)
    result = operation.get_configurations()

    result = [tuple(sorted(inner_list)) for inner_list in result]
    expected_output = [tuple(sorted(inner_list)) for inner_list in expected_output]

    assert sorted(result) == sorted(expected_output), (
        f"The result {result} does not match the expected output {expected_output}"
    )


@pytest.mark.parametrize(
    "setup_model, expected_output",
    [
        ("./resources/models/fama_test_suite/relationships/mandatory/mandatory.xml", True),
        ("./resources/models/fama_test_suite/relationships/optional/optional.xml", True),
        ("./resources/models/fama_test_suite/relationships/alternative/alternative.xml", True),
        ("./resources/models/fama_test_suite/relationships/or/or.xml", True),
        ("./resources/models/fama_test_suite/relationships/excludes/excludes.xml", True),
        ("./resources/models/fama_test_suite/relationships/requires/requires.xml", True),
        (
            "./resources/models/fama_test_suite/relationships/mandatory-optional/mandatory-optional.xml",
            True,
        ),
        ("./resources/models/fama_test_suite/relationships/mandatory-or/mandatory-or.xml", True),
        (
            "./resources/models/fama_test_suite/relationships/mandatory-alternative/mandatory-alternative.xml",
            True,
        ),
        (
            "./resources/models/fama_test_suite/relationships/mandatory-requires/mandatory-requires.xml",
            True,
        ),
        (
            "./resources/models/fama_test_suite/relationships/mandatory-excludes/mandatory-excludes.xml",
            False,
        ),
        ("./resources/models/fama_test_suite/relationships/optional-or/optional-or.xml", True),
        (
            "./resources/models/fama_test_suite/relationships/optional-alternative/optional-alternative.xml",
            True,
        ),
        (
            "./resources/models/fama_test_suite/relationships/or-alternative/or-alternative.xml",
            True,
        ),
        ("./resources/models/fama_test_suite/relationships/or-requires/or-requires.xml", True),
        ("./resources/models/fama_test_suite/relationships/or-excludes/or-excludes.xml", True),
        (
            "./resources/models/fama_test_suite/relationships/alternative-requires/alternative-requires.xml",
            True,
        ),
        (
            "./resources/models/fama_test_suite/relationships/alternative-excludes/alternative-excludes.xml",
            True,
        ),
        (
            "./resources/models/fama_test_suite/relationships/requires-excludes/requires-excludes.xml",
            True,
        ),
        (
            "./resources/models/fama_test_suite/relationships/allrelationships/allrelationships.xml",
            True,
        ),
        (
            "./resources/models/fama_test_suite/refinement/alternative-noOr/alternative-noOr.xml",
            False,
        ),
        (
            "./resources/models/fama_test_suite/refinement/or-noAlternative/or-noAlternative.xml",
            True,
        ),
        (
            "./resources/models/fama_test_suite/refinement/alternative-noParentLastChild/alternative-noParentLastChild.xml",
            False,
        ),
        (
            "./resources/models/fama_test_suite/refinement/alternative-oddChildren/alternative-oddChildren.xml",
            False,
        ),
    ],
    indirect=["setup_model"],
)
def test_valid_model_operation(setup_model, expected_output):
    model = setup_model
    operation = PySATSatisfiable()

    operation.execute(model)
    result = operation.is_satisfiable()

    assert result == expected_output, (
        f"The result {result} does not match the expected output {expected_output}"
    )


@pytest.mark.parametrize(
    "setup_model, expected_output, configuration",
    [
        (
            "./resources/models/fama_test_suite/relationships/allrelationships/allrelationships.xml",
            True,
            Configuration({"A": True, "B": True, "C": True}),
        ),
        (
            "./resources/models/fama_test_suite/relationships/allrelationships/allrelationships.xml",
            False,
            Configuration({"E": True, "F": False}),
        ),
        (
            "./resources/models/fama_test_suite/relationships/allrelationships/allrelationships.xml",
            True,
            Configuration({"E": True, "F": True}),
        ),
        (
            "./resources/models/fama_test_suite/relationships/allrelationships/allrelationships.xml",
            True,
            Configuration({"E": False, "F": False}),
        ),
        (
            "./resources/models/fama_test_suite/relationships/allrelationships/allrelationships.xml",
            True,
            Configuration({"D": False, "G": True}),
        ),
        (
            "./resources/models/fama_test_suite/relationships/allrelationships/allrelationships.xml",
            False,
            Configuration({"D": True, "G": True}),
        ),
        (
            "./resources/models/fama_test_suite/relationships/allrelationships/allrelationships.xml",
            True,
            Configuration({"D": True, "G": False}),
        ),
        (
            "./resources/models/fama_test_suite/relationships/allrelationships/allrelationships.xml",
            False,
            Configuration({"B": False}),
        ),
    ],
    indirect=["setup_model"],
)
def test_valid_configuration_operation(setup_model, expected_output, configuration):
    model = setup_model
    operation = PySATSatisfiableConfiguration()
    configuration.is_full = False
    operation.set_configuration(configuration)
    operation.execute(model)
    result = operation.is_satisfiable()

    assert result == expected_output, (
        f"The result {result} does not match the expected output {expected_output}"
    )


@pytest.mark.parametrize(
    "setup_model, expected_output, configuration",
    [
        (
            "./resources/models/fama_test_suite/relationships/allrelationships/allrelationships.xml",
            True,
            Configuration({"A": True, "B": True, "D": True}),
        ),
        (
            "./resources/models/fama_test_suite/relationships/allrelationships/allrelationships.xml",
            True,
            Configuration({"A": True, "B": True, "D": True, "C": True, "F": True}),
        ),
        (
            "./resources/models/fama_test_suite/relationships/allrelationships/allrelationships.xml",
            True,
            Configuration({"A": True, "B": True, "E": True, "C": True, "F": True}),
        ),
        (
            "./resources/models/fama_test_suite/relationships/allrelationships/allrelationships.xml",
            False,
            Configuration({"A": True, "B": True, "D": True, "C": True, "F": True, "G": True}),
        ),
        (
            "./resources/models/fama_test_suite/relationships/allrelationships/allrelationships.xml",
            False,
            Configuration({"A": True, "B": True, "E": True, "C": True, "F": True, "D": True}),
        ),
        (
            "./resources/models/fama_test_suite/relationships/allrelationships/allrelationships.xml",
            False,
            Configuration(
                {"A": True, "B": True, "E": True, "C": True, "F": True, "G": True, "D": True}
            ),
        ),
        (
            "./resources/models/fama_test_suite/relationships/allrelationships/allrelationships.xml",
            True,
            Configuration({"A": True, "B": True, "E": True, "C": True, "F": True, "G": True}),
        ),
    ],
    indirect=["setup_model"],
)
def test_valid_product_operation(setup_model, expected_output, configuration):
    model = setup_model
    operation = PySATSatisfiableConfiguration()
    configuration.is_full = True
    operation.set_configuration(configuration)
    operation.execute(model)
    result = operation.is_satisfiable()

    assert result == expected_output, (
        f"The result {result} does not match the expected output {expected_output, str(configuration)}"
    )


"""
@pytest.mark.parametrize("setup_model, expected_output", [
    ("./resources/models/fama_test_suite/error-guessing/dead-features/case1/df-case1.xml", True, Configuration({"A":True,"B":True,"D":True})),
    ("./resources/models/fama_test_suite/error-guessing/dead-features/case2/df-case2.xml", True, Configuration({"A":True,"B":True,"D":True,"C":True,"F":True})),
    ("./resources/models/fama_test_suite/error-guessing/dead-features/case3/df-case3.xml", True, Configuration({"A":True,"B":True,"D":True,"C":True,"F":True})),
    ("./resources/models/fama_test_suite/error-guessing/dead-features/case4/df-case4.xml", True, Configuration({"A":True,"B":True,"D":True,"C":True,"F":True})),
    ("./resources/models/fama_test_suite/error-guessing/dead-features/case5/df-case5.xml", True, Configuration({"A":True,"B":True,"D":True,"C":True,"F":True})),
    ("./resources/models/fama_test_suite/error-guessing/dead-features/case6/df-case6.xml", True, Configuration({"A":True,"B":True,"D":True,"C":True,"F":True})),
    ("./resources/models/fama_test_suite/error-guessing/dead-features/case7/df-case7.xml", True, Configuration({"A":True,"B":True,"D":True,"C":True,"F":True})),
    ("./resources/models/fama_test_suite/error-guessing/dead-features/case8/df-case8.xml", True, Configuration({"A":True,"B":True,"D":True,"C":True,"F":True})),
   ], indirect=["setup_model"])
def test_valid_product_operation(setup_model, expected_output):
    model = setup_model
    operation = PySAT3Diagnosis()

    operation.execute(model)
    result = operation.is_valid()

    assert result == expected_output, f"The result {result} does not match the expected output {expected_output, str(configuration)}"
"""
