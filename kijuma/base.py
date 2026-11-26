"""Build the base model for the merit profile, on which the dials will be added."""

from build123d import *

from . import values as v


def base() -> Part:
    """Return the base model part."""
    thickness, radius = v.material_thickness, v.bend_radius

    with BuildPart() as builder:
        with BuildSheet(Plane.XZ, thickness=thickness, bend_radius=radius) as sheet:
            with BuildSketch():
                Rectangle(*v.base_size)
            flange(sheet.rims().group_by(Axis.Y)[0], angle=-180, length=v.base_size[1])

            with BuildSketch(mode=Mode.SUBTRACT):
                align = (Align.CENTER, Align.MIN)
                Rectangle(v.base_size[0], v.base_size[1] / 2, align=align)
                Circle(v.disc_diam / 2, mode=Mode.SUBTRACT, align=None)
                with BuildSketch(Rotation(90, 0, v.slot_start)):
                    Circle(v.disc_diam / 2, v.slot_length, align=None)
                Circle(v.disc_diam / 2 - v.slot_width, mode=Mode.SUBTRACT)

            min_pos, max_pos = -v.base_size[1] / 2 + 1, v.base_size[1]
            fillet(sheet.vertices().filter_by_position(Axis.Y, min_pos, max_pos), v.fillet)

            with BuildSketch(mode=Mode.SUBTRACT):
                Circle(v.rivet_diam / 2)
            with Locations(Plane(sheet.flats().sort_by(Axis.Z)[0])):
                Circle(v.rivet_diam / 2, mode=Mode.SUBTRACT)

            # Strip folded backwards from the horizontal edge of the front sheet
            edge = sheet.rims().filter_by(Axis.X).sort_by_distance((v.strip_pos, 0, 0))[0]
            start, end = edge.position_at(0).X, edge.position_at(1).X
            tab_width = v.strip_width - 2 * v.strip_clearance

            gap1 = max(start, end) - (v.strip_pos + tab_width / 2)
            gap2 = (v.strip_pos - tab_width / 2) - min(start, end)
            flange(edge, radius + thickness, -90, gaps=(gap1, gap2))

            # Window in the back sheet holding the strip
            back_sheet = sheet.flats().sort_by(Face.area)[-1]
            with Locations((v.strip_pos, radius + thickness / 2, back_sheet.center().Z)):
                height = thickness + 2 * v.strip_clearance
                Rectangle(v.strip_width, height, mode=Mode.SUBTRACT)
        thicken()

    part = builder.part
    part.label = "Base"
    part.color = Color(0.6, 0.6, 0.2)
    return part
