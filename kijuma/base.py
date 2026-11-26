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

            # The front sheet is notched so that the strip stands lower than the dial axis
            notch_pos = v.strip_pos, -v.strip_drop / 2
            with BuildSketch(mode=Mode.SUBTRACT), Locations(notch_pos):
                Rectangle(v.strip_width, v.strip_drop)

            # Strip folded backwards from the bottom of the notch.
            # Its head stops against the back sheet, its neck goes through the window.
            edge = sheet.rims().filter_by(Axis.X).sort_by_distance((*notch_pos, 0))[0]
            flange(edge, radius, -90)

            # Window in the back sheet holding the neck of the strip
            back_sheet = sheet.flats().sort_by(Face.area)[-1]
            wall_z = radius + thickness / 2 - v.strip_drop
            with Locations((v.strip_pos, wall_z, back_sheet.center().Z)):
                height = thickness + 2 * v.strip_clearance
                Rectangle(v.window_width, height, mode=Mode.SUBTRACT)
        thicken()

        # Neck of the strip, from the head to the outside of the back sheet
        neck_start = radius + thickness
        neck_length = 2 * (radius + thickness) + v.strip_protrusion - neck_start
        neck_width = v.window_width - 2 * v.strip_clearance
        with Locations((v.strip_pos, neck_start + neck_length / 2, wall_z)):
            Box(neck_width, neck_length, thickness)

    part = builder.part
    part.label = "Base"
    part.color = Color(0.6, 0.6, 0.2)
    return part
