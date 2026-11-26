"""Main entry point to build and animate the model."""

from build123d import *
from ocp_viewer import Animation, show

from .assembly import assembly

animated_dial = 1  # number of the dial to animate, from 1 (front) to len(tab_angles)

show(assembly())

anim = Animation()
anim.add_track(f"/Assembly/Dial {animated_dial}", "ry", [0, 1, 2], [0, 90, 180])
anim.animate(1)
