import rich_click as click

from .shared_state import SharedState

pass_shared_state = click.make_pass_decorator(SharedState, ensure=True)
"""Decorator for passing SharedState to a function."""
