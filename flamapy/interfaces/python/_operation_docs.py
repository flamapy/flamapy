"""Operation help text (CLI ``--help`` + REST swagger descriptions).

Auto-extracted once from the pre-refactor ``FLAMAFeatureModel`` method docstrings. The facade
now generates its methods from OperationDescriptors and falls back to this map for their
``__doc__``; a new plugin operation should instead set ``doc=`` on its OperationDescriptor.
"""

OPERATION_DOCS = {
    'all_feature_bounds': (
        'Returns the value bounds for all typed (Integer, Real, String) attribute\\n'
        "features in the model. Each entry maps a feature name to a dict with 'min',\\n"
        "'max', and 'bounded' keys. Requires the z3 metamodel plugin."
    ),
    'atomic_sets': (
        'This operation is used to find the atomic sets in a model: It returns the atomic\\n'
        'sets if they are found in the model. If the model does not follow the UVL\\n'
        'specification, an exception is raised and the operation returns False.'
    ),
    'attribute_optimization': (
        'Returns the configuration(s) that optimize one or more numeric feature\\n'
        'attributes.\\n'
        '\\n'
        '``objectives`` is either a single attribute name (defaults to minimizing it) or\\n'
        'a mapping ``{attribute_name: "Minimize"|"Maximize"}``. ``backend`` selects the\\n'
        'plugin: "sat" performs single-objective MaxSAT optimization; "z3" additionally\\n'
        'supports typed attributes and multi-objective (Pareto) optimization. Defaults to\\n'
        '"sat".'
    ),
    'average_branching_factor': (
        'This refers to the average number of child features that a parent feature has in\\n'
        "a feature model. It's calculated by dividing the total number of child features\\n"
        'by the total number of parent features. A high average branching factor\\n'
        'indicates a complex feature model with many options, while a low average\\n'
        'branching factor indicates a simpler model.'
    ),
    'backbone': (
        'Returns the backbone of the feature model: the set of features that must always\\n'
        'be selected (core) and those that must never be selected (dead) across all valid\\n'
        "configurations, grouped under 'core' and 'dead' keys."
    ),
    'commonality': (
        'This is a measure of how often a feature appears in the products of a product\\n'
        "line. It's usually expressed as a percentage. A feature with 100 per cent\\n"
        'commonality is a core feature, as it appears in all products.\\n'
        '\\n'
        '``configuration_path`` accepts a configuration file path, a ``{feature: value}``\\n'
        'mapping, or a Configuration object.'
    ),
    'configurations': (
        'These are the individual outcomes that can be produced from a feature model.\\n'
        'Each product is a combination of features that satisfies all the constraints and\\n'
        'dependencies in the feature model.\\n'
        '\\n'
        '``backend`` selects the analysis plugin ("sat", "bdd" or "z3"); defaults to bdd.'
    ),
    'configurations_number': (
        'This is the total number of different full configurations that can be produced\\n'
        "from a feature model. It's calculated by considering all possible combinations\\n"
        'of features, taking into account the constraints and dependencies between\\n'
        'features.\\n'
        '\\n'
        '``backend`` selects the analysis plugin ("sat", "bdd", "z3", or "sharpsat" for a\\n'
        'scalable approximate count via the optional flamapy-sharpsat plugin); defaults\\n'
        'to bdd.'
    ),
    'configurations_with_n_features': (
        'Returns all valid configurations that have exactly n features selected.'
    ),
    'conflict': (
        'Returns a list of conflict sets: minimal subsets of the model constraints that\\n'
        'are inconsistent with the given configuration. Requires the pysat_diagnosis\\n'
        'plugin.\\n'
        '\\n'
        '``configuration_path`` accepts a configuration file path, a ``{feature: value}``\\n'
        'mapping, or a Configuration object. ``test_case_path`` is optional and, when\\n'
        'given, looks for conflicts against that expected outcome instead; same input\\n'
        'types.'
    ),
    'core_features': (
        'These are the features that are present in all products of a product line. In a\\n'
        'feature model, they are the features that are mandatory and not optional. Core\\n'
        'features define the commonality among all products in a product line.\\n'
        '\\n'
        '``backend`` selects the analysis plugin ("sat", "bdd" or "z3"); defaults to sat.'
    ),
    'count_leafs': (
        'This operation counts the number of leaf features in a feature model. Leaf\\n'
        'features are those that do not have any child features. They represent the most\\n'
        'specific options in a product line.'
    ),
    'dead_features': (
        'These are features that, due to the constraints and dependencies in the feature\\n'
        'model, cannot be included in any valid product. Dead features are usually a sign\\n'
        'of an error in the feature model.\\n'
        '\\n'
        '``backend`` selects the analysis plugin ("sat", "bdd" or "z3"); defaults to sat.'
    ),
    'diagnosis': (
        'Returns a list of diagnoses explaining why a configuration is not valid against\\n'
        'the feature model: each diagnosis is a minimal set of constraints whose removal\\n'
        'would resolve the inconsistency. Requires the pysat_diagnosis plugin.\\n'
        '\\n'
        '``configuration_path`` accepts a configuration file path, a ``{feature: value}``\\n'
        'mapping, or a Configuration object. ``test_case_path`` is optional and, when\\n'
        'given, diagnoses against that expected outcome instead; it accepts the same\\n'
        'input types.'
    ),
    'estimated_number_of_configurations': (
        'This is an estimate of the total number of different products that can be\\n'
        "produced from a feature model. It's calculated by considering all possible\\n"
        'combinations of features. This can be a simple multiplication if all features\\n'
        'are independent, but in most cases, constraints and dependencies between\\n'
        'features need to be taken into account.'
    ),
    'false_optional_features': (
        'These are features that appear to be optional in the feature model, but due to\\n'
        'the constraints and dependencies, must be included in every valid product. Like\\n'
        'dead features, false optional features are usually a sign of an error in the\\n'
        'feature model.\\n'
        '\\n'
        '``backend`` selects the analysis plugin ("sat", "bdd" or "z3"); defaults to sat.'
    ),
    'feature_ancestors': (
        'These are the features that are directly or indirectly the parent of a given\\n'
        'feature in a feature model. Ancestors of a feature are found by traversing up\\n'
        'the feature hierarchy. This information can be useful to understand the context\\n'
        'and dependencies of a feature.'
    ),
    'feature_bounds': (
        'Returns the value bounds for a specific typed attribute feature. The result dict\\n'
        "contains 'min', 'max', and 'bounded' keys. Requires the z3 metamodel plugin."
    ),
    'feature_inclusion_probability': (
        'Returns a mapping from each feature name to its inclusion probability: the\\n'
        'fraction of valid configurations in which that feature is selected. Core\\n'
        'features have probability 1.0 and dead features have probability 0.0.'
    ),
    'filter': (
        'This operation selects a subset of the products of a product line based on\\n'
        'certain criteria. For example, you might filter the products to only include\\n'
        'those that contain a certain feature.\\n'
        '\\n'
        '``configuration_path`` accepts a configuration file path, a ``{feature: value}``\\n'
        'mapping, or a Configuration object.'
    ),
    'homogeneity': (
        'Measures how similar the products of the feature model are to each other. It is\\n'
        'computed as the average commonality factor across all features. A value of 1.0\\n'
        'means all products are identical; lower values indicate more diversity.'
    ),
    'language_level': (
        'Return the UVL language level.'
    ),
    'leaf_features': (
        'This operation is used to find leaf features in a model: It returns the leaf\\n'
        'features if they are found in the model. If the model does not follow the UVL\\n'
        'specification, an exception is raised and the operation returns False.\\n'
        '\\n'
        'Traditionally you would use the flama tool by features =\\n'
        "discover_metamodel.use_operation_from_file('OperationString', model) however, in\\n"
        'this tool we know that this operation is from the fm metamodel, so we avoid to\\n'
        'execute the transformation if possible'
    ),
    'max_depth': (
        'This operation is used to find the max depth of the tree in a model: It returns\\n'
        'the max depth of the tree. If the model does not follow the UVL specification,\\n'
        'an exception is raised and the operation returns False.'
    ),
    'metrics': (
        'Returns a collection of structural metrics for the feature model, such as number\\n'
        'of features, constraints, relations, and complexity indicators.'
    ),
    'minimum_configuration': (
        'Returns a valid configuration with the fewest selected features (the minimum\\n'
        'working configuration).\\n'
        '\\n'
        '``backend`` selects the analysis plugin; only "sat" implements this operation.'
    ),
    'product_distribution': (
        'Returns the distribution of products by number of activated features. The value\\n'
        'at index i is the count of valid configurations that have exactly i features\\n'
        'selected.'
    ),
    'pure_optional_features': (
        'Returns features with a feature inclusion probability of exactly 0.5, meaning\\n'
        'they are selected in exactly half of the valid configurations. These are the\\n'
        'most unconstrained optional features.'
    ),
    'sampling': (
        'Returns a random sample of valid configurations of the given size. When\\n'
        'with_replacement is True, the same configuration may appear more than once.\\n'
        '\\n'
        '``backend`` selects the analysis plugin; defaults to bdd. sat and bdd implement\\n'
        '(deterministic/enumerating) sampling; "sharpsat" provides almost-uniform\\n'
        'sampling via the optional flamapy-sharpsat plugin.'
    ),
    'satisfiable': (
        'In the context of feature models, this usually refers to whether the feature\\n'
        'model itself satisfies all the constraints and dependencies. A a valid feature\\n'
        'model is one that does encodes at least a single valid product.\\n'
        '\\n'
        '``backend`` selects the analysis plugin ("sat", "bdd" or "z3"); defaults to sat.'
    ),
    'satisfiable_configuration': (
        'This is a product that is produced from a valid configuration of features. A\\n'
        'valid product satisfies all the constraints and dependencies in the feature\\n'
        'model.\\n'
        '\\n'
        '``configuration_path`` accepts a configuration file path, a ``{feature: value}``\\n'
        'mapping, or a Configuration object. ``backend`` selects the analysis plugin\\n'
        '("sat", "bdd" or "z3"); defaults to sat.'
    ),
    't_wise_sampling': (
        'Returns a t-wise (combinatorial) sample: a set of valid configurations that\\n'
        'covers every satisfiable combination of ``t`` feature selections (pairwise for\\n'
        '``t = 2``).\\n'
        '\\n'
        '``backend`` selects the analysis plugin; only "sat" implements t-wise sampling.'
    ),
    'unique_features': (
        'Returns features that appear in exactly one valid configuration. These features\\n'
        'uniquely identify a single product in the product line.'
    ),
    'variability': (
        'Returns a tuple of (total_variability, partial_variability). Total variability\\n'
        'is the ratio of valid configurations to the theoretical maximum; partial\\n'
        'variability is the ratio relative to only the variant features.'
    ),
    'variant_features': (
        'Returns the features that are neither core nor dead — they appear in some but\\n'
        'not all valid configurations. These are the features that actually vary across\\n'
        'products.'
    ),
    'variation_points': (
        'Returns the variation points of the feature model. A variation point is a\\n'
        'feature that has at least one non-mandatory child, representing a decision point\\n'
        'in the model. The result maps each variation point name to the list of its\\n'
        'variant feature names.'
    ),
}
