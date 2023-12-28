from typing import Any, Callable

import click
from click import Context, Parameter, ParamType
from click.shell_completion import CompletionItem

from . import completion
from .device import Query


class QueryParam(ParamType):
    """Click parameter type for parsing Query arguments."""

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


class QueryOrLabelParam(ParamType):
    """Click parameter type for Query arguments, represented by either Query
    syntax or the name of an existing device label."""

    name = "label_or_query"

    def convert(
        self, value: str | Query, param: Parameter | None, context: Context | None
    ) -> Query:
        if isinstance(value, Query):
            return value
        try:
            if ":" in value:
                return Query.parse(value)
        except Query.ParseError as error:
            self.fail(str(error))
        return Query("", "", "")

    def shell_complete(
        self, context: Context, param: Parameter, incomplete: str
    ) -> list[CompletionItem]:
        return completion.device_label(context, param, incomplete) + completion.query(
            context, param, incomplete
        )


AnyCallable = Callable[..., Any]


def label_or_query_argument(
    name: str,
    *args: Any,
    **kwargs: Any,
) -> Callable[[AnyCallable], AnyCallable]:
    """Decorator that accepts a device label or a raw query string, and passes
    an argument of type Query to the command."""

    # The return value will be a Query, likely with the name 'query', but we
    # want to communicate to the user that either a device label or query string
    # works.
    kwargs.setdefault("metavar", "LABEL_OR_QUERY")
    return click.argument(name, *args, type=QueryOrLabelParam(), **kwargs)
