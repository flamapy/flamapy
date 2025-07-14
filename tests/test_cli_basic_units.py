import subprocess
import pytest

VALID_MODEL = "./resources/models/simple/valid_model.uvl"
NON_VALID_MODEL = "./resources/models/simple/invalid_model.uvl"

VALID_CONFIG = "./resources/configurations/valid_configuration.csvconf"


def _test_cli_op(operation: str, model: str, config: str = None):
    if config:
        result = subprocess.run(
            ["flamapy", operation, model, config], capture_output=True, text=True
        )
    else:
        result = subprocess.run(["flamapy", operation, model], capture_output=True, text=True)
    return result


@pytest.mark.parametrize(
    "operation, model, config, res_type, expected_output",
    [
        (
            "atomic_sets",
            VALID_MODEL,
            None,
            "list",
            "[['PHP', 'Search', 'Catalog', 'Security', 'Payment', 'eCommerce', 'Shopping', 'Web', 'Storage', 'v74', 'Cart', 'Server'], ['LOW'], ['ENOUGH'], ['BASIC'], ['ADVANCED'], ['PayPal'], ['CreditCard'], ['Mobile'], ['HIGH'], ['STANDARD'], ['Backup'], ['Marketing'], ['SEO'], ['Socials'], ['Twitter'], ['Facebook'], ['YouTube']]",
        ),
        ("average_branching_factor", VALID_MODEL, None, "float", "2.45"),
        (
            "core_features",
            VALID_MODEL,
            None,
            "list",
            "['eCommerce', 'Server', 'Web', 'Catalog', 'Search', 'Shopping', 'Security', 'Cart', 'Payment', 'PHP', 'Storage', 'v74']",
        ),
        ("count_leafs", VALID_MODEL, None, "int", "17"),
        ("estimated_number_of_configurations", VALID_MODEL, None, "int", "1904"),
        ("feature_ancestors", VALID_MODEL, "v74", "list", "['PHP', 'Server', 'eCommerce']"),
        (
            "leaf_features",
            VALID_MODEL,
            None,
            "list",
            "['v74', 'LOW', 'ENOUGH', 'Catalog', 'BASIC', 'ADVANCED', 'Cart', 'PayPal', 'CreditCard', 'Mobile', 'HIGH', 'STANDARD', 'Backup', 'SEO', 'Twitter', 'Facebook', 'YouTube']",
        ),
        ("max_depth", VALID_MODEL, None, "int", "4"),
        ("dead_features", VALID_MODEL, None, "list", "[]"),
        ("false_optional_features", VALID_MODEL, None, "list", "[]"),
        ("filter", VALID_MODEL, VALID_CONFIG, "len", "68"),
        ("configurations_number", VALID_MODEL, None, "int", "816"),
        ("commonality", VALID_MODEL, VALID_CONFIG, "float", "1.0"),
        ("satisfiable_configuration", VALID_MODEL, VALID_CONFIG, "bool", "True"),
        ("satisfiable", VALID_MODEL, None, "bool", "True"),
    ],
)
def test_cli_operations(operation, model, config, res_type, expected_output):
    result = _test_cli_op(operation, model, config)
    assert result.returncode == 0
    if res_type == "list":
        assert len(expected_output) == len(result.stdout[:-1])
    elif res_type == "float" or res_type == "int" or res_type == "bool":
        assert expected_output == result.stdout[:-1]
    elif res_type == "len":
        cleaned_res = str(result.stdout[:-1])
        assert int(expected_output) == int(cleaned_res.count("[") - 1)
