from click import Context, Parameter, ParamType
from click.shell_completion import CompletionItem

from . import completion
from .device import Query


class QueryParam(ParamType):
    name = "query"

    def convert(
        self, value: str, param: Parameter | None, context: Context | None
    ) -> Query:
        try:
            return Query.parse(value)
        except Query.ParseError as error:
            self.fail(str(error))

    def shell_complete(
        self, context: Context, param: Parameter, incomplete: str
    ) -> list[CompletionItem]:
        return completion.query(context, param, incomplete)
