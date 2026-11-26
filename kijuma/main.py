"""Main entry point to build and animate the model."""

from build123d import *
from ocp_viewer import Animation, show

from .assembly import assembly

show(assembly(tab_angle=20))

anim = Animation()
anim.add_track("/Assembly/Dial", "ry", [0, 1, 2], [0, 90, 180])
anim.animate(1)
