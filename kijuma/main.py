"""Main entry point to build the model."""

from ocp_viewer import show

from .base import base
from .dial import dial

show(
    # dial(20),
    base(),
)
