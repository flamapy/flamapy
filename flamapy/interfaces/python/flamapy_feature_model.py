from typing import List, Any, Union
from flamapy.core.discover import DiscoverMetamodels
from flamapy.metamodels.fm_metamodel.models import FeatureModel
from flamapy.core.exceptions import FlamaException
from flamapy.metamodels.configuration_metamodel.models import Configuration


class FLAMAFeatureModel:
    def __init__(self, model_path: str):
        """
        This is the path in the filesystem where the model is located.
        Any model in UVL, FaMaXML or FeatureIDE format are accepted
        """
        self.model_path = model_path
        """
        Creating the interface witht he flama framework
        """
        self.discover_metamodel = DiscoverMetamodels()
        """
        We save the model for later ussage
        """
        self.fm_model = self._read(model_path)
        """
        We create a empty sat model and a bdd model to avoid double transformations
        """
        self.sat_model = None
        self.bdd_model = None

    def _read(self, model_path: str) -> FeatureModel:
        return self.discover_metamodel.use_transformation_t2m(model_path, "fm")

    def _transform_to_sat(self) -> None:
        if self.sat_model is None:
            self.sat_model = self.discover_metamodel.use_transformation_m2m(self.fm_model, "pysat")

    def _transform_to_bdd(self) -> None:
        if self.bdd_model is None:
            self.bdd_model = self.discover_metamodel.use_transformation_m2m(self.fm_model, "bdd")

    def atomic_sets(self) -> Union[None, List[List[Any]]]:
        """
        This operation is used to find the atomic sets in a model:
        It returns the atomic sets if they are found in the model.
        If the model does not follow the UVL specification, an
        exception is raised and the operation returns False.
        """

        # Try to use the Find operation, which returns the atomic sets if they are found
        try:
            atomic_sets = self.discover_metamodel.use_operation(
                self.fm_model, "FMAtomicSets"
            ).get_result()
            result = []
            for atomic_set in atomic_sets:
                partial_set = []
                for feature in atomic_set:
                    partial_set.append(feature.name)
                result.append(partial_set)
            return result
        except FlamaException as exception:
            print(f"Error: {exception}")
            return None

    def average_branching_factor(self) -> Union[None, float]:
        """
        This refers to the average number of child features that a parent feature has in a
        feature model. It's calculated by dividing the total number of child features by the
        total number of parent features. A high average branching factor indicates a complex
        feature model with many options, while a low average branching factor indicates a
        simpler model.
        """

        # Try to use the Find operation, which returns the atomic sets if they are found
        try:
            result = self.discover_metamodel.use_operation(
                self.fm_model, "FMAverageBranchingFactor"
            ).get_result()
            return result
        except FlamaException as exception:
            print(f"Error: {exception}")
            return None

    def count_leafs(self) -> Union[None, int]:
        """
        This operation counts the number of leaf features in a feature model. Leaf features
        are those that do not have any child features. They represent the most specific
        options in a product line.
        """

        # Try to use the Find operation, which returns the atomic sets if they are found
        try:
            result = self.discover_metamodel.use_operation(
                self.fm_model, "FMCountLeafs"
            ).get_result()
            return result
        except FlamaException as exception:
            print(f"Error: {exception}")
            return None

    def estimated_number_of_configurations(self) -> Union[None, int]:
        """
        This is an estimate of the total number of different products that can be produced
        from a feature model. It's calculated by considering all possible combinations of
        features. This can be a simple multiplication if all features are independent, but
        in most cases, constraints and dependencies between features need to be taken
        into account.
        """

        # Try to use the Find operation, which returns the atomic sets if they are found
        try:
            result = self.discover_metamodel.use_operation(
                self.fm_model, "FMEstimatedConfigurationsNumber"
            ).get_result()
            return result
        except FlamaException as exception:
            print(f"Error: {exception}")
            return None

    def feature_ancestors(self, feature_name: str) -> Union[None, List[str]]:
        """
        These are the features that are directly or indirectly the parent of a given feature in
        a feature model. Ancestors of a feature are found by traversing up the feature hierarchy.
        This information can be useful to understand the context and dependencies of a feature.
        """
        # Try to use the Find operation, which returns the atomic sets if they are found
        try:
            operation = self.discover_metamodel.get_operation(self.fm_model, "FMFeatureAncestors")
            operation.set_feature(self.fm_model.get_feature_by_name(feature_name))
            operation.execute(self.fm_model)
            flama_result = operation.get_result()
            result = []
            for res in flama_result:
                result.append(res.name)
            return result
        except FlamaException as exception:
            print(f"Error: {exception}")
            return None

    def leaf_features(self) -> Union[None, List[str]]:
        """
        This operation is used to find leaf features in a model:
        It returns the leaf features if they are found in the model.
        If the model does not follow the UVL specification, an
        exception is raised and the operation returns False.

        Traditionally you would use the flama tool by
        features = discover_metamodel.use_operation_from_file('OperationString', model)
        however, in this tool we know that this operation is from the fm metamodel,
        so we avoid to execute the transformation if possible
        """

        # Try to use the operation, which returns the leaf features if they are found
        try:
            features = self.discover_metamodel.use_operation(
                self.fm_model, "FMLeafFeatures"
            ).get_result()
            leaf_features = []
            for feature in features:
                leaf_features.append(feature.name)
            return leaf_features
        except FlamaException as exception:
            print(f"Error: {exception}")
            return None

    def max_depth(self) -> Union[None, int]:
        """
        This operation is used to find the max depth of the tree in a model:
        It returns the max depth of the tree.
        If the model does not follow the UVL specification, an
        exception is raised and the operation returns False.
        """

        # Try to use the Find operation, which returns the max depth of the tree
        try:
            return self.discover_metamodel.use_operation(
                self.fm_model, "FMMaxDepthTree"
            ).get_result()
        except FlamaException as exception:
            print(f"Error: {exception}")
            return None

    # The methods above rely on sat to be executed.
    def core_features(self) -> Union[None, List[str]]:
        """
        These are the features that are present in all products of a product line.
        In a feature model, they are the features that are mandatory and not optional.
        Core features define the commonality among all products in a product line.
        This call requires sat to be called, however, there is an implementation within
        flamapy that does not requires sat. please use the framework in case of needing it.
        """
        try:
            self._transform_to_sat()
            features = self.discover_metamodel.use_operation(
                self.sat_model, "PySATCoreFeatures"
            ).get_result()
            return features
        except FlamaException as exception:
            print(f"Error: {exception}")
            return None

    def dead_features(self) -> Union[None, List[str]]:
        """
        These are features that, due to the constraints and dependencies in the
        feature model, cannot be included in any valid product. Dead features are usually
        a sign of an error in the feature model.
        """
        try:
            self._transform_to_sat()
            features = self.discover_metamodel.use_operation(
                self.sat_model, "PySATDeadFeatures"
            ).get_result()
            return features
        except FlamaException as exception:
            print(f"Error: {exception}")
            return None

    def false_optional_features(self) -> Union[None, List[str]]:
        """
        These are features that appear to be optional in the feature model, but due to the
        constraints and dependencies, must be included in every valid product. Like dead features,
        false optional features are usually a sign of an error in the feature model.
        """
        try:
            self._transform_to_sat()
            operation = self.discover_metamodel.get_operation(
                self.sat_model, "PySATFalseOptionalFeatures"
            )
            operation.feature_model = self.fm_model
            operation.execute(self.sat_model)
            features = operation.get_result()
            return features
        except FlamaException as exception:
            print(f"Error: {exception}")
            return None

    def filter(self, configuration_path: str) -> Union[None, List[Configuration]]:
        """
        This operation selects a subset of the products of a product line based on certain
        criteria. For example, you might filter the products to only include those that
        contain a certain feature.
        """
        try:
            self._transform_to_sat()
            configuration = self.discover_metamodel.use_transformation_t2m(
                configuration_path, "configuration"
            )
            operation = self.discover_metamodel.get_operation(self.sat_model, "PySATFilter")
            operation.set_configuration(configuration)
            operation.execute(self.sat_model)
            result = operation.get_result()
            return result
        except FlamaException as exception:
            print(f"Error: {exception}")
            return None

    def configurations_number(self, with_sat: bool = False) -> Union[None, int]:
        """
        This is the total number of different full configurations that can be
        produced from a feature model. It's calculated by considering all possible
        combinations of features, taking into account the constraints and
        dependencies between features.
        """
        try:
            nop = 0
            if with_sat:
                self._transform_to_sat()
                nop = self.discover_metamodel.use_operation(
                    self.sat_model, "PySATConfigurationsNumber"
                ).get_result()
            else:
                self._transform_to_bdd()
                nop = self.discover_metamodel.use_operation(
                    self.bdd_model, "BDDConfigurationsNumber"
                ).get_result()
            return nop
        except FlamaException as exception:
            print(f"Error: {exception}")
            return None

    def configurations(self, with_sat: bool = False) -> Union[None, List[Configuration]]:
        """
        These are the individual outcomes that can be produced from a feature model. Each product
        is a combination of features that satisfies all the constraints and dependencies in the
        feature model.
        """
        try:
            products = []
            if with_sat:
                self._transform_to_sat()
                products = self.discover_metamodel.use_operation(
                    self.sat_model, "PySATConfigurations"
                ).get_result()
            else:
                self._transform_to_bdd()
                products = self.discover_metamodel.use_operation(
                    self.bdd_model, "BDDConfigurations"
                ).get_result()
            return products
        except FlamaException as exception:
            print(f"Error: {exception}")
            return None

    def commonality(self, configuration_path: str) -> Union[None, float]:
        """
        This is a measure of how often a feature appears in the products of a
        product line. It's usually expressed as a percentage. A feature with
        100 per cent commonality is a core feature, as it appears in all products.
        """
        try:
            self._transform_to_sat()
            configuration = self.discover_metamodel.use_transformation_t2m(
                configuration_path, "configuration"
            )

            operation = self.discover_metamodel.get_operation(self.sat_model, "PySATCommonality")
            operation.set_configuration(configuration)
            operation.execute(self.sat_model)
            return operation.get_result()
        except FlamaException as exception:
            print(f"Error: {exception}")
            return None

    def satisfiable_configuration(
        self, configuration_path: str, full_configuration: bool = False
    ) -> Union[None, bool]:
        """
        This is a product that is produced from a valid configuration of features. A valid
        product satisfies all the constraints and dependencies in the feature model.
        """
        try:
            self._transform_to_sat()
            configuration = self.discover_metamodel.use_transformation_t2m(
                configuration_path, "configuration"
            )
            operation = self.discover_metamodel.get_operation(
                self.sat_model, "PySATSatisfiableConfiguration"
            )

            if full_configuration:
                configuration.is_full = True
            else:
                configuration.is_full = False

            operation.set_configuration(configuration)
            operation.execute(self.sat_model)
            result = operation.get_result()
            return result
        except FlamaException as exception:
            print(f"Error: {exception}")
            return None

    def satisfiable(self) -> Union[None, bool]:
        """
        In the context of feature models, this usually refers to whether the feature model itself
        satisfies all the constraints and dependencies. A a valid feature model is one that
        does encodes at least a single valid product.
        """
        try:
            self._transform_to_sat()
            result = self.discover_metamodel.use_operation(
                self.sat_model, "PySATSatisfiable"
            ).get_result()
            return result
        except FlamaException as exception:
            print(f"Error: {exception}")
            return None
