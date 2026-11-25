"""Build the base model for the merit profile, on which the dials will be added."""

from build123d import *


def base() -> BuildPart:
    """Return the base model builder."""
    with BuildPart() as part:
        with BuildSheet(Plane.XZ, thickness=1, bend_radius=2) as sheet:
            with BuildSketch():
                Rectangle(210, 210)
            flange(sheet.rims().group_by(Axis.Y)[0], angle=-180, length=210)

            with BuildSketch(mode=Mode.SUBTRACT):
                Rectangle(210, 210 / 2, align=(Align.CENTER, Align.MIN))
                Circle(40, mode=Mode.SUBTRACT)
                Circle(5 / 2)

            with Locations(Plane(sheet.flats().sort_by(Axis.Z)[0])):
                Circle(5 / 2, mode=Mode.SUBTRACT)

        thicken()

    return part
