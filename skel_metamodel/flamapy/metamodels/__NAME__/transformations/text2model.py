from flamapy.core.transformations import TextToModel

from flamapy.metamodels.__NAME___metamodel.models.models import __NAME__Model


class __NAME__TextToModel(TextToModel):
    @staticmethod
    def get_source_extension() -> str:
        return "__EXT__"

    def __init__(self, path: str):
        self.path = path
        self.model = __NAME__Model()

    def transform(self) -> __NAME__Model:
        # TODO: insert your code here
        return self.model
