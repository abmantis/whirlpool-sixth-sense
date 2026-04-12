"""Placeholder — legacy REST API does not support microwaves.

This module exists only so the top-level facade can typecheck against
a concrete Microwave class on the HTTP side. All abstract methods stay
abstract via inheritance, so attempting to instantiate this class
raises TypeError at runtime.
"""

from ..microwave import Microwave as MicrowaveABC


class Microwave(MicrowaveABC):
    """Not implemented. See module docstring."""
