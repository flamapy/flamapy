from flamapy.core.operations import Satisfiable

from flamapy.metamodels.__NAME___metamodel.models.models import __NAME__Model


class __NAME__Valid(Satisfiable):
    def __init__(self) -> None:
        self.result = False

    def execute(self, model: __NAME__Model) -> "__NAME__Valid":
        # TODO: insert your model code here
        return self

    def is_satisfiable(self) -> bool:
        return self.result

    def get_result(self) -> bool:
        return self.result
