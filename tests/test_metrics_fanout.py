"""Metrics reach every installed metamodel from a backend model, through its source feature
model, so the framework API reports the same metrics whatever model the operation starts from."""
from flamapy.core.discover import DiscoverMetamodels

VALID_MODEL = "./resources/models/simple/valid_model.uvl"


def _names(metrics):
    return sorted(metric["name"] for metric in metrics)


def test_metrics_from_a_backend_model_report_every_metamodel():
    discover = DiscoverMetamodels()
    feature_model = discover.use_transformation_t2m(VALID_MODEL, "fm")
    from_fm = discover.use_operation(feature_model, "FMMetrics").get_result()
    sat_model = discover.use_transformation_m2m(feature_model, "pysat")
    from_sat = discover.use_operation(sat_model, "PySATMetrics").get_result()
    assert _names(from_sat) == _names(from_fm)
    assert len(from_fm) == 61
