"""
Construit le modèle du socle du profil de mérite, qui reçoit les cadrans.

Les esquisses et pièces auxiliaires sont construites dans leur propre fonction,
puis ajoutées à base() : un constructeur imbriqué n'agit sur son parent que s'il est
créé dans la même fonction que lui.
"""

from math import sqrt

from build123d import *

from . import values as v
from .utils import polar_vertices


def front_cutter() -> Sketch:
    """Construit l'esquisse à retirer du panneau avant : moitié haute, disque et fente."""
    with BuildSketch() as sketch:
        align = (Align.CENTER, Align.MIN)
        Rectangle(v.base_size[0], v.base_size[1] / 2, align=align)
        Circle(v.disc_diam / 2, mode=Mode.SUBTRACT, align=None)
        with BuildSketch(Rotation(90, 0, 0)):
            Circle(v.disc_diam / 2, 180 + len(v.dials) * v.dial_slot_step, align=None)
        Circle(v.disc_diam / 2 - v.dial_slot_width, mode=Mode.SUBTRACT)
    return sketch.sketch_local


def view_radii() -> tuple[float, float]:
    """Construit les rayons extérieur et intérieur de la fenêtre en arc de cercle."""
    outer = v.dial_diam / 2 + v.base_view_offset
    return outer, outer - v.base_view_width


def view_tip() -> tuple[tuple[float, float], tuple[float, float]]:
    """Construit le centre et la taille du rectangle qui coupe la pointe de la fenêtre."""
    # La fenêtre sort du bord gauche du socle en laissant une pointe de matière effilée.
    # Ce rectangle la coupe à l'horizontale, pour adoucir l'angle.
    half, outer = v.base_size[0] / 2, view_radii()[0]
    top = -sqrt(outer**2 - half**2) + 1  # un peu au-dessus de la pointe, dans la fenêtre
    bottom = -sqrt(outer**2 - half**2) - v.base_view_chamfer
    left, right = -half - 1, -sqrt(outer**2 - bottom**2) + 0.5
    return ((left + right) / 2, (top + bottom) / 2), (right - left, top - bottom)


def view_window() -> Sketch:
    """Construit la fenêtre en arc de cercle, décalée vers l'extérieur du cadran."""
    outer, inner = view_radii()
    with BuildSketch() as sketch:
        with BuildSketch(Rotation(90, 0, -180)):
            Circle(outer, v.base_view_angle, None)
        Circle(inner, mode=Mode.SUBTRACT)
    return sketch.sketch_local


def left_strip_edge() -> tuple[float, float]:
    """Construit la position (x, y) du bord de la languette de gauche."""
    # Le bord est placé assez bas pour reposer sur de la matière, à gauche de la fenêtre
    # en arc de cercle, donc loin du cadran, sans rien retirer d'autre que l'échancrure.
    right = -v.base_size[0] / 2 + v.base_strip_left_margin + v.base_strip_width
    x = right - v.base_strip_width / 2
    return x, -sqrt(view_radii()[0] ** 2 - (right + v.fillet) ** 2)


def strip_neck(spacing: float, x: float, edge_y: float) -> Part:
    """Construit la tête de la languette, jusqu'à l'extérieur du panneau arrière."""
    thickness, radius = v.material_thickness, v.bend_radius
    start = radius + thickness
    length = 2 * (radius + thickness) + spacing - start
    width = v.base_strip_window_width - 2 * v.base_strip_clearance
    z = edge_y + radius + thickness / 2
    with BuildPart() as builder, Locations((x, start + length / 2, z)):
        Box(width, length, thickness)
    return builder.part


def base() -> Part:
    """Construit la pièce correspondant au socle."""
    thickness, radius = v.material_thickness, v.bend_radius
    # Longueur plane ajoutée entre les deux pliages, pour écarter les deux panneaux
    spacing = v.base_gap - 2 * radius
    # Languettes (x, y du bord, hauteur de l'échancrure) : à droite juste sous l'axe du
    # cadran, à gauche en bas de la pointe de matière laissée par la fenêtre en arc
    left_x, left_y = left_strip_edge()
    strips = [
        (v.base_strip_pos, -v.base_strip_drop, v.base_strip_drop),
        (left_x, left_y, v.base_strip_left_notch),
    ]

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

            # Congés sur le panneau avant, sauf au bas de la fenêtre intérieure
            min_pos, max_pos = -v.base_size[1] / 2 + 1, v.base_size[1]
            corners = sheet.vertices().filter_by_position(Axis.Y, min_pos, max_pos)
            window_bottom = polar_vertices(
                corners,
                v.dial_slot_length + len(v.dials) * v.dial_slot_step,
                (v.disc_diam / 2, v.disc_diam / 2 - v.dial_slot_width),
            )
            fillet([p for p in corners if p not in window_bottom], v.fillet)

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

            # Chanfrein horizontal de la pointe de la fenêtre au bord gauche, avec congés
            tip_center, tip_size = view_tip()
            with BuildSketch(mode=Mode.SUBTRACT), Locations(tip_center):
                Rectangle(*tip_size)
            tip_bottom = tip_center[1] - tip_size[1] / 2
            tip_corners = sheet.vertices().filter_by_position(
                Axis.Y,
                tip_bottom - v.tolerance,
                tip_bottom + v.tolerance,
            )
            fillet(tip_corners, v.fillet)

            for x, edge_y, notch_height in strips:
                # Le panneau avant est échancré, assez haut pour déplier la bande
                notch_pos = x, edge_y + notch_height / 2
                with BuildSketch(mode=Mode.SUBTRACT), Locations(notch_pos):
                    Rectangle(v.base_strip_width, notch_height)

                # Bande pliée vers l'arrière depuis le fond de l'échancrure.
                # Sa base vient en butée contre le panneau arrière, sa tête traverse la
                # fenêtre de la tôle arrière, qui retient la base de la languette.
                edge = sheet.rims().filter_by(Axis.X).sort_by_distance((x, edge_y, 0))[0]
                flange(edge, radius + spacing, -90)
                back_sheet = sheet.flats().sort_by(Face.area)[-1]
                wall_z = edge_y + radius + thickness / 2
                with Locations((x, wall_z, back_sheet.center().Z)):
                    height = thickness + 2 * v.base_strip_clearance
                    Rectangle(v.base_strip_window_width, height, mode=Mode.SUBTRACT)
        thicken()
        for x, edge_y, _ in strips:
            insert(strip_neck(spacing, x, edge_y))

    part = builder.part
    part.label = v.base[0]
    part.color = Color(v.base[1])
    return part
