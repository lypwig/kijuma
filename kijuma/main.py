"""Main entry point to build the model."""

from ocp_viewer import show

# from .dial import dial
from .base import base

show(base())
