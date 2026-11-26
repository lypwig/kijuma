"""
Construit le modèle du socle du profil de mérite, qui reçoit les cadrans.

Les esquisses et pièces auxiliaires sont construites dans leur propre fonction,
puis ajoutées à base() : un constructeur imbriqué n'agit sur son parent que s'il est
créé dans la même fonction que lui.
"""

from build123d import *

from . import values as v
from .utils import polar_vertices


def front_cutter() -> Sketch:
    """Retourne l'esquisse à retirer du panneau avant : moitié haute, disque et fente."""
    with BuildSketch() as sketch:
        align = (Align.CENTER, Align.MIN)
        Rectangle(v.base_size[0], v.base_size[1] / 2, align=align)
        Circle(v.disc_diam / 2, mode=Mode.SUBTRACT, align=None)
        with BuildSketch(Rotation(90, 0, v.dial_slot_start)):
            Circle(v.disc_diam / 2, v.dial_slot_length, align=None)
        Circle(v.disc_diam / 2 - v.dial_slot_width, mode=Mode.SUBTRACT)
    return sketch.sketch_local


def view_radii() -> tuple[float, float]:
    """Retourne les rayons extérieur et intérieur de la fenêtre en arc de cercle."""
    outer = v.dial_diam / 2 + v.base_view_offset
    return outer, outer - v.base_view_width


def view_window() -> Sketch:
    """Retourne la fenêtre en arc de cercle, décalée vers l'extérieur du cadran."""
    outer, inner = view_radii()
    with BuildSketch() as sketch:
        # La fenêtre dépasse de 5° au-delà du bord gauche, pour s'ouvrir sur celui-ci
        with BuildSketch(Rotation(90, 0, -180 - 5)):
            Circle(outer, v.base_view_angle + 5, None)
        Circle(inner, mode=Mode.SUBTRACT)
    return sketch.sketch_local


def strip_neck(spacing: float) -> Part:
    """Retourne la tête de la languette, jusqu'à l'extérieur du panneau arrière."""
    thickness, radius = v.material_thickness, v.bend_radius
    start = radius + thickness
    length = 2 * (radius + thickness) + spacing - start
    width = v.base_strip_window_width - 2 * v.base_strip_clearance
    z = radius + thickness / 2 - v.base_strip_drop
    with BuildPart() as builder, Locations((v.base_strip_pos, start + length / 2, z)):
        Box(width, length, thickness)
    return builder.part


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
                insert(front_cutter())

            min_pos, max_pos = -v.base_size[1] / 2 + 1, v.base_size[1]
            fillet(sheet.vertices().filter_by_position(Axis.Y, min_pos, max_pos), v.fillet)

            with BuildSketch(mode=Mode.SUBTRACT):
                Circle(v.rivet_diam / 2)
            with Locations(Plane(sheet.flats().sort_by(Axis.Z)[0])):
                Circle(v.rivet_diam / 2, mode=Mode.SUBTRACT)

            # Fenêtre du panneau avant, pour voir le bout des languettes, avec ses congés
            with BuildSketch(mode=Mode.SUBTRACT):
                insert(view_window())
            window_end = polar_vertices(
                sheet.vertices(),
                v.base_view_angle - 180,
                view_radii(),
            )
            fillet(window_end, v.fillet)

            # Le panneau avant est échancré pour abaisser la bande sous l'axe du cadran
            notch_pos = v.base_strip_pos, -v.base_strip_drop / 2
            with BuildSketch(mode=Mode.SUBTRACT), Locations(notch_pos):
                Rectangle(v.base_strip_width, v.base_strip_drop)

            # Bande pliée vers l'arrière depuis le fond de l'échancrure.
            # Sa base vient en butée contre le panneau arrière, sa tête traverse la fenêtre.
            edge = sheet.rims().filter_by(Axis.X).sort_by_distance((*notch_pos, 0))[0]
            flange(edge, radius + spacing, -90)

            # Fenêtre de la tôle arrière, qui retient la base de la languette
            back_sheet = sheet.flats().sort_by(Face.area)[-1]
            wall_z = radius + thickness / 2 - v.base_strip_drop
            with Locations((v.base_strip_pos, wall_z, back_sheet.center().Z)):
                height = thickness + 2 * v.base_strip_clearance
                Rectangle(v.base_strip_window_width, height, mode=Mode.SUBTRACT)
        thicken()
        insert(strip_neck(spacing))

    part = builder.part
    part.label = v.base[0]
    part.color = Color(v.base[1])
    return part
