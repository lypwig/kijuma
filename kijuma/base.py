"""Construit le modèle du socle du profil de mérite, qui reçoit les cadrans."""

from build123d import *

from . import values as v


def base() -> Part:
    """Retourne la pièce correspondant au socle."""
    thickness, radius = v.material_thickness, v.bend_radius
    # Longueur plane ajoutée entre les deux pliages, pour écarter les deux panneaux
    spacing = v.base_gap - 2 * radius

    with BuildPart() as builder:
        with BuildSheet(Plane.XZ, thickness=thickness, bend_radius=radius) as sheet:
            with BuildSketch():
                Rectangle(*v.base_size)
            bottom = sheet.rims().group_by(Axis.Y)[0]
            if spacing:  # deux pliages à 90° avec une paroi plane entre eux
                flange(bottom, angle=-90, length=spacing)
                bottom = sheet.rims().filter_by(Axis.X).sort_by(Axis.Z)[0]
                flange(bottom, angle=-90, length=v.base_size[1])

            with BuildSketch(mode=Mode.SUBTRACT):
                align = (Align.CENTER, Align.MIN)
                Rectangle(v.base_size[0], v.base_size[1] / 2, align=align)
                Circle(v.disc_diam / 2, mode=Mode.SUBTRACT, align=None)
                with BuildSketch(Rotation(90, 0, v.dial_slot_start)):
                    Circle(v.disc_diam / 2, v.dial_slot_length, align=None)
                Circle(v.disc_diam / 2 - v.dial_slot_width, mode=Mode.SUBTRACT)

            min_pos, max_pos = -v.base_size[1] / 2 + 1, v.base_size[1]
            fillet(sheet.vertices().filter_by_position(Axis.Y, min_pos, max_pos), v.fillet)

            with BuildSketch(mode=Mode.SUBTRACT):
                Circle(v.rivet_diam / 2)
            with Locations(Plane(sheet.flats().sort_by(Axis.Z)[0])):
                Circle(v.rivet_diam / 2, mode=Mode.SUBTRACT)

            # Fenêtre en arc de cercle du panneau avant, pour voir le bout des languettes.
            # Elle suit le cercle du cadran et s'ouvre à gauche, sur le bord du panneau.
            # La fenêtre dépasse de 5° au-delà du bord, pour s'ouvrir sur celui-ci
            start, span = -180 - 5, v.base_view_angle + 5
            with BuildSketch(mode=Mode.SUBTRACT):
                with BuildSketch(Rotation(90, 0, start)):
                    Circle(v.dial_diam / 2, span, None)
                Circle(v.dial_diam / 2 - v.base_view_width, mode=Mode.SUBTRACT)

            # Le panneau avant est échancré pour abaisser la bande sous l'axe du cadran
            notch_pos = v.base_strip_pos, -v.base_strip_drop / 2
            with BuildSketch(mode=Mode.SUBTRACT), Locations(notch_pos):
                Rectangle(v.base_strip_width, v.base_strip_drop)

            # Bande pliée vers l'arrière depuis le fond de l'échancrure.
            # Sa base vient en butée contre le panneau arrière, sa tête traverse la fenêtre.
            edge = sheet.rims().filter_by(Axis.X).sort_by_distance((*notch_pos, 0))[0]
            flange(edge, radius + spacing, -90)

            # Fenêtre de la tôle arrière, qui retient le cou de la bande
            back_sheet = sheet.flats().sort_by(Face.area)[-1]
            wall_z = radius + thickness / 2 - v.base_strip_drop
            with Locations((v.base_strip_pos, wall_z, back_sheet.center().Z)):
                height = thickness + 2 * v.base_strip_clearance
                Rectangle(v.base_strip_window_width, height, mode=Mode.SUBTRACT)
        thicken()

        # languette, de la base jusqu'à la tête (extérieur de la tôle arrière)
        neck_start = radius + thickness
        neck_length = 2 * (radius + thickness) + spacing - neck_start
        neck_width = v.base_strip_window_width - 2 * v.base_strip_clearance
        with Locations((v.base_strip_pos, neck_start + neck_length / 2, wall_z)):
            Box(neck_width, neck_length, thickness)

    part = builder.part
    part.label = v.base[0]
    part.color = Color(v.base[1])
    return part
