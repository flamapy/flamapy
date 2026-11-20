"""Forcing a backend that cannot represent the model's language level (e.g. 'sat'/'bdd' on a
model with arithmetic constraints) silently drops those constraints. The facade must then warn
that the result is not exact, instead of reporting a confidently-wrong result. A model the
backend *can* handle must not warn. Regression test for flamapy/flamapy#3.
"""
import warnings

import pytest

from flamapy.interfaces.python.flamapy_feature_model import FLAMAFeatureModel

# B is mandatory with Fun=8, so `B.Fun < 7` is constant-false: the model is UNSAT. The sat/bdd
# backends only support BOOLEAN+GROUP_CARDINALITY, so they drop the arithmetic constraint.
ARITHMETIC_MODEL = (
    "features\n"
    "    A\n"
    "        mandatory\n"
    "            B {Fun 8}\n"
    "constraints\n"
    "    B.Fun < 7\n"
)
BOOLEAN_MODEL = (
    "features\n"
    "    A\n"
    "        mandatory\n"
    "            B\n"
)


def _model(tmp_path, text: str) -> FLAMAFeatureModel:
    path = tmp_path / "model.uvl"
    path.write_text(text)
    return FLAMAFeatureModel(str(path))


def _warning_messages(call) -> list[str]:
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        call()
    return [str(w.message) for w in recorded]


def test_sat_on_arithmetic_model_warns(tmp_path) -> None:
    fm = _model(tmp_path, ARITHMETIC_MODEL)
    with pytest.warns(UserWarning, match="not exact"):
        fm.satisfiable(backend="sat")


def test_bdd_on_arithmetic_model_warns(tmp_path) -> None:
    fm = _model(tmp_path, ARITHMETIC_MODEL)
    with pytest.warns(UserWarning, match="not exact"):
        fm.configurations_number(backend="bdd")


def test_sat_on_boolean_model_does_not_warn(tmp_path) -> None:
    fm = _model(tmp_path, BOOLEAN_MODEL)
    messages = _warning_messages(lambda: fm.satisfiable(backend="sat"))
    assert not any("not exact" in m for m in messages)
