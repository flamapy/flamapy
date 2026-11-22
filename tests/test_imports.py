"""Models with imports are analysed as one tree: the imported models used to count as leaf
features, so their features and constraints were ignored (flamapy/fm_metamodel#110)."""
import warnings

import pytest

from flamapy.interfaces.python.flamapy_feature_model import FLAMAFeatureModel

SPIRITS = ('features\n    Spirits\n        alternative\n            Gin\n            Rum\n'
           '        optional\n            Ice\nconstraints\n    Rum => Ice\n')
BACKENDS = ['sat', 'bdd', 'z3']


def _model(tmp_path, main: str, **files: str) -> FLAMAFeatureModel:
    for name, text in {'Spirits': SPIRITS, 'Mix': main, **files}.items():
        (tmp_path / f'{name}.uvl').write_text(text)
    return FLAMAFeatureModel(str(tmp_path / 'Mix.uvl'), raise_errors=True)


def _two_parents(imports: str, first: str, second: str) -> str:
    return (f'imports\n{imports}features\n    Mix\n        optional\n'
            f'            Three\n                mandatory\n                    {first}.Spirits\n'
            f'            Two\n                mandatory\n                    {second}.Spirits\n')


@pytest.mark.parametrize('backend', BACKENDS)
def test_imported_features_and_constraints_are_analysed(tmp_path, backend):
    fm = _model(tmp_path, 'imports\n    Spirits as S\nfeatures\n    Mix\n        optional\n'
                          '            S.Spirits\n')
    # Mix alone, or with Spirits: Gin (with or without Ice) or Rum (which requires Ice).
    assert fm.configurations_number(backend=backend) == 4
    assert fm.last_result.exact is True


@pytest.mark.parametrize('backend', BACKENDS)
def test_the_same_model_under_two_aliases_gives_independent_subtrees(tmp_path, backend):
    fm = _model(tmp_path, _two_parents('    Spirits as S\n    Spirits as T\n', 'S', 'T'))
    assert fm.configurations_number(backend=backend) == 16  # (1 + 3) * (1 + 3)


@pytest.mark.parametrize('backend', BACKENDS)
def test_nested_imports_reached_through_two_models(tmp_path, backend):
    fm = _model(
        tmp_path,
        'imports\n    B as B\n    C as C\nfeatures\n    Mix\n        optional\n'
        '            B.B\n            C.C\n',
        B='imports\n    Spirits as S\nfeatures\n    B\n        mandatory\n            S.Spirits\n',
        C='imports\n    Spirits as S\nfeatures\n    C\n        mandatory\n            S.Spirits\n')
    assert fm.configurations_number(backend=backend) == 16


def test_a_model_without_imports_or_repeated_names_does_not_warn(tmp_path):
    with warnings.catch_warnings():
        warnings.simplefilter('error', UserWarning)
        _model(tmp_path, 'features\n    Mix\n        optional\n            A\n            B\n')


@pytest.mark.parametrize('main', [
    _two_parents('    Spirits as S\n', 'S', 'S'),  # the model of flamapy/fm_metamodel#110
    'features\n    Mix\n        optional\n            Three\n                mandatory\n'
    '                    Sp\n            Two\n                mandatory\n                    Sp\n',
])
def test_repeated_feature_names_warn(tmp_path, main):
    with pytest.warns(UserWarning, match='cannot be guaranteed') as record:
        fm = _model(tmp_path, main)
    assert record[0].filename == __file__
    # The backend does not approximate anything: the warning is the only signal.
    fm.satisfiable(backend='sat')
    assert fm.last_result.exact is True
