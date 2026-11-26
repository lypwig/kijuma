"""Main entry point to build and animate the model."""

from build123d import *
from ocp_viewer import Animation, show

from . import values as v
from .assembly import assembly

animated_dial = 1  # number of the dial to animate, from 1 to len(dials)

show(assembly())

anim = Animation()
label = v.dials[animated_dial - 1][0]
anim.add_track(f"/Assembly/{label}", "ry", [0, 1, 2], [0, 90, 180])
anim.animate(1)
