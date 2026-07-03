"""Phase-2 guard: the discovered OperationDescriptors must reproduce, one-for-one, the operation
surface of the hand-written facade (name + default backend + input names).

The current ``FLAMAFeatureModel`` is the oracle: every public method on it is an operation, and
each must be backed by exactly one descriptor with the matching default backend and inputs. When
the facade is later made descriptor-driven (phase 3) this test keeps the two in lock-step.
"""
import inspect

from flamapy.core.discover import DiscoverMetamodels
from flamapy.interfaces.python.flamapy_feature_model import FLAMAFeatureModel

# name -> (default_backend, (input names in order)). Captured from today's facade.
EXPECTED = {
    # fm-level operations (run on the feature model directly)
    'atomic_sets': (None, ()),
    'language_level': (None, ()),
    'average_branching_factor': (None, ()),
    'count_leafs': (None, ()),
    'estimated_number_of_configurations': (None, ()),
    'feature_ancestors': (None, ('feature_name',)),
    'leaf_features': (None, ()),
    'max_depth': (None, ()),
    'metrics': (None, ()),
    'variation_points': (None, ()),
    # backend-selectable interface operations
    'core_features': ('sat', ()),
    'dead_features': ('sat', ()),
    'false_optional_features': ('sat', ()),
    'satisfiable': ('sat', ()),
    'satisfiable_configuration': ('sat', ('configuration_path', 'full_configuration')),
    'attribute_optimization': ('sat', ('objectives',)),
    'configurations_number': ('bdd', ()),
    'configurations': ('bdd', ()),
    'sampling': ('bdd', ('size', 'with_replacement')),
    # bespoke sat operations
    'filter': ('sat', ('configuration_path',)),
    'commonality': ('sat', ('configuration_path',)),
    'backbone': ('sat', ()),
    't_wise_sampling': ('sat', ('t',)),
    'minimum_configuration': ('sat', ()),
    # bespoke bdd operations
    'homogeneity': ('bdd', ()),
    'product_distribution': ('bdd', ()),
    'variability': ('bdd', ()),
    'variant_features': ('bdd', ()),
    'unique_features': ('bdd', ()),
    'pure_optional_features': ('bdd', ()),
    'feature_inclusion_probability': ('bdd', ()),
    'configurations_with_n_features': ('bdd', ('n',)),
    # z3 operations
    'all_feature_bounds': ('z3', ()),
    'feature_bounds': ('z3', ('variable_name',)),
    # diagnosis operations
    'diagnosis': ('pysat_diagnosis',
                  ('configuration_path', 'test_case_path', 'max_diagnoses')),
    'conflict': ('pysat_diagnosis',
                 ('configuration_path', 'test_case_path', 'max_conflicts')),
}


# Operations whose facade method exposes a backend= kwarg (backend-selectable).
SELECTABLE = {
    'core_features', 'dead_features', 'false_optional_features', 'satisfiable',
    'configurations_number', 'configurations', 'satisfiable_configuration', 'sampling',
    'attribute_optimization', 't_wise_sampling', 'minimum_configuration',
}


def _facade_operation_methods():
    return {name for name, _ in inspect.getmembers(FLAMAFeatureModel, predicate=inspect.isfunction)
            if not name.startswith('_')}


def test_expected_table_matches_the_facade_surface():
    # The oracle table must describe exactly the public methods of the current facade.
    assert _facade_operation_methods() == set(EXPECTED)


def test_every_facade_operation_has_a_descriptor():
    available = DiscoverMetamodels().available_operations()
    missing = set(EXPECTED) - set(available)
    assert not missing, f"facade operations without a descriptor: {sorted(missing)}"


def test_descriptors_match_expected_backend_and_inputs():
    available = DiscoverMetamodels().available_operations()
    mismatches = {}
    for name, (backend, input_names) in EXPECTED.items():
        descriptor = available[name]
        actual = (descriptor.default_backend, tuple(i.name for i in descriptor.inputs))
        if actual != (backend, input_names):
            mismatches[name] = {'expected': (backend, input_names), 'actual': actual}
    assert not mismatches, mismatches


def test_selectable_flag_matches():
    available = DiscoverMetamodels().available_operations()
    assert {name for name, d in available.items() if d.selectable_backend} == SELECTABLE


def test_generated_method_signatures_match_descriptors():
    # The descriptor-generated facade methods must expose exactly (self, *inputs[, backend]).
    for name, (_, input_names) in EXPECTED.items():
        signature = inspect.signature(getattr(FLAMAFeatureModel, name))
        params = [p for p in signature.parameters if p != 'self']
        expected = list(input_names) + (['backend'] if name in SELECTABLE else [])
        assert params == expected, {'op': name, 'actual': params, 'expected': expected}


def test_every_descriptor_has_doc_and_returns():
    available = DiscoverMetamodels().available_operations()
    assert all((d.doc or '').strip() for d in available.values())
    assert all((d.returns or '').strip() for d in available.values())


def test_type_stub_is_in_sync():
    # The shipped flamapy_feature_model.pyi must match what the generator produces from the
    # current descriptors. Regenerate with: python -m flamapy.interfaces.python._stub
    import pathlib

    from flamapy.interfaces.python import _stub

    stub_path = pathlib.Path(_stub.__file__).with_name('flamapy_feature_model.pyi')
    assert stub_path.read_text(encoding='utf-8') == _stub.render_stub(), (
        'flamapy_feature_model.pyi is out of date; regenerate it with '
        '`python -m flamapy.interfaces.python._stub`')
