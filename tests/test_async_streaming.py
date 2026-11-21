"""The additive async + streaming facade API (v2.9 / Track A phase 6)."""
import subprocess
import time
import warnings

import pytest

from flamapy.core.exceptions import FlamaException, OperationTimeout
from flamapy.interfaces.python.flamapy_feature_model import FLAMAFeatureModel

VALID_MODEL = './resources/models/simple/valid_model.uvl'


def test_run_async_matches_the_sync_result():
    fm = FLAMAFeatureModel(VALID_MODEL)
    job = fm.run_async('configurations_number')
    assert job.result(timeout=30) == fm.configurations_number() == 816


def test_run_async_applies_result_adapters_and_inputs():
    fm = FLAMAFeatureModel(VALID_MODEL)
    sync = fm.commonality({'Cart': True})
    job = fm.run_async('commonality', configuration_path={'Cart': True})
    assert job.result(timeout=30) == sync


def test_run_async_envelope_carries_provenance():
    fm = FLAMAFeatureModel(VALID_MODEL)
    job = fm.run_async('satisfiable')
    job.result(timeout=30)
    envelope = job.envelope()
    assert envelope.operation == 'satisfiable' and envelope.backend == 'pysat'


def test_run_async_rejects_non_operations():
    fm = FLAMAFeatureModel(VALID_MODEL)
    with pytest.raises(FlamaException):
        fm.run_async('run_async')
    with pytest.raises(FlamaException):
        fm.run_async('no_such_operation')


def test_run_async_timeout_covers_the_backend_transformation(monkeypatch):
    # The fm -> backend transformation (e.g. BDD compilation, the expensive step on large
    # models) must run inside the job, so run_async returns at once and the deadline
    # covers it.
    original_model_for = FLAMAFeatureModel._model_for

    def slow_model_for(self, *args, **kwargs):
        time.sleep(2)
        return original_model_for(self, *args, **kwargs)

    monkeypatch.setattr(FLAMAFeatureModel, '_model_for', slow_model_for)
    fm = FLAMAFeatureModel(VALID_MODEL)
    start = time.perf_counter()
    job = fm.run_async('configurations_number')
    assert time.perf_counter() - start < 1
    with pytest.raises(OperationTimeout):
        job.result(timeout=0.2)


def test_run_async_raises_preparation_errors_from_the_job():
    fm = FLAMAFeatureModel(VALID_MODEL)
    job = fm.run_async('configurations_number', backend='no_such_backend')
    with pytest.raises(FlamaException):
        job.result(timeout=30)


def test_iter_configurations_streams_and_matches_full_enumeration():
    fm = FLAMAFeatureModel(VALID_MODEL)
    iterator = fm.iter_configurations()
    first = next(iterator)  # arrives without exhausting the enumeration
    assert first is not None
    streamed = [first] + list(iterator)
    full = FLAMAFeatureModel(VALID_MODEL).configurations()
    as_sets = {frozenset(n for n, v in c.elements.items() if v) for c in streamed}
    full_sets = {frozenset(n for n, v in c.elements.items() if v) for c in full}
    assert as_sets == full_sets and len(streamed) == len(full) == 816


def test_cli_timeout_flag_expires_with_exit_124(tmp_path):
    # 40 independent optional features => 2**40 configurations: the enumeration cannot
    # finish, so the deadline reliably fires (and cooperative cancel stops the loop).
    features = '\n'.join(f'            F{i}' for i in range(40))
    model = tmp_path / 'huge.uvl'
    model.write_text(f'features\n    Root\n        optional\n{features}\n')
    completed = subprocess.run(
        ['flamapy', 'configurations', str(model), '--timeout', '0.5'],
        capture_output=True, text=True, check=False)
    assert completed.returncode == 124
    assert 'Timeout' in completed.stderr


def test_cli_timeout_flag_passes_fast_operations():
    completed = subprocess.run(
        ['flamapy', 'satisfiable', VALID_MODEL, '--timeout', '60'],
        capture_output=True, text=True, check=False)
    assert completed.returncode == 0
    assert completed.stdout.strip() == 'True'


# --- flamapy#3: a backend that ignores part of the model, through run_async --------------------

_ARITHMETIC_UNSAT = (
    "features\n"
    "    A\n"
    "        mandatory\n"
    "            B {Fun 8}\n"
    "constraints\n"
    "    B.Fun < 7\n"
)


def _arithmetic_model(tmp_path):
    path = tmp_path / "arithmetic.uvl"
    path.write_text(_ARITHMETIC_UNSAT)
    return FLAMAFeatureModel(str(path))


@pytest.mark.parametrize("backend", ['sat', 'bdd'])
def test_run_async_marks_a_result_beyond_the_backend_level_inexact(tmp_path, backend):
    fm = _arithmetic_model(tmp_path)
    # The warning comes from the run_async call itself, on the caller's thread and line.
    with pytest.warns(UserWarning, match='the result is not exact') as record:
        job = fm.run_async('satisfiable', backend=backend)
    assert record[0].filename == __file__
    envelope = job.envelope(timeout=30)
    assert envelope.exact is False and envelope.planner == 'explicit'


def test_run_async_envelope_matches_the_sync_provenance(tmp_path):
    fm = _arithmetic_model(tmp_path)
    for backend in ('z3', 'auto'):
        with warnings.catch_warnings():
            warnings.simplefilter('error', UserWarning)
            job = fm.run_async('satisfiable', backend=backend)
            assert job.result(timeout=30) is False
        fm.satisfiable(backend=backend)
        envelope = job.envelope()
        assert envelope.exact is True
        assert envelope.planner == fm.last_result.planner
        assert envelope.backend == fm.last_result.backend


def test_concurrent_jobs_do_not_share_their_provenance(tmp_path):
    # Many jobs on ONE facade, alternating a backend that ignores the arithmetic constraint
    # (inexact) with one that does not: each envelope must carry its own verdict.
    fm = _arithmetic_model(tmp_path)
    backends = ['sat', 'z3', 'bdd', 'auto'] * 6
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        jobs = [(backend, fm.run_async('satisfiable', backend=backend)) for backend in backends]
    for backend, job in jobs:
        envelope = job.envelope(timeout=60)
        inexact = backend in ('sat', 'bdd')
        assert envelope.exact is (not inexact), backend
        assert envelope.value is inexact, backend  # the dropped constraint makes it "sat"
        if backend == 'auto':
            assert envelope.planner.startswith('auto: ')
        else:
            assert envelope.planner == 'explicit'
