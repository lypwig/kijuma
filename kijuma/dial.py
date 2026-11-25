"""Build the dial used to show the merit profile."""

from build123d import *

from . import values as v


def dial(tab_angle: int) -> BuildPart:
    """Return the dial builder configured for the given tab angle."""
    with BuildPart() as dial:
        with BuildSketch(Plane.XZ) as sketch:
            Circle(v.disc_diam / 2)
            Circle(v.dial_diam / 2, -180, None)
            Circle(v.dial_diam / 2 + 5, -180 + tab_angle, None)

            with BuildSketch(Rotation(90, 0, 180 - v.window_start), mode=Mode.SUBTRACT):
                Circle(v.disc_diam / 2, v.window_size, None)
                Circle(v.disc_diam / 2 - v.window_thickness, mode=Mode.SUBTRACT)

            fillet(sketch.vertices().sort_by(Axis.X)[:-1], v.fillet)
            Circle(v.rivet_diam / 2, mode=Mode.SUBTRACT)

            with Locations(v.stop_loc):
                SlotOverall(*v.stop_size)

        extrude(amount=v.material_thickness)

    return dial
