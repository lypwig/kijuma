"""
Construit le modèle du socle du profil de mérite, qui reçoit les cadrans.

Les esquisses et pièces auxiliaires sont construites dans leur propre fonction,
puis ajoutées à base() : un constructeur imbriqué n'agit sur son parent que s'il est
créé dans la même fonction que lui.
"""

from math import asin, cos, radians, sin, sqrt

from build123d import *

from . import utils as u
from . import values as v

base_view_angle = len(v.dials) * v.dial_tab_step
base_left_strip_pos = 10  # position horiz. du centre de la languette depuis le bord gauche


def front_cutter() -> Sketch:
    """Construit l'esquisse à retirer du panneau avant : moitié haute, disque et fente."""
    with BuildSketch() as sketch:
        align = (Align.CENTER, Align.MIN)
        Rectangle(v.base_size, v.base_size / 2, align=align)
        Circle(v.dial_disc_diam / 2, mode=Mode.SUBTRACT, align=None)
        with BuildSketch(Rotation(90, 0, 0)):
            Circle(v.dial_disc_diam / 2, 180 + len(v.dials) * v.dial_slot_step, align=None)
        Circle(v.dial_disc_diam / 2 - v.dial_slot_width, mode=Mode.SUBTRACT)
    return sketch.sketch_local


def view_radii() -> tuple[float, float]:
    """Construit les rayons extérieur et intérieur de la fenêtre en arc de cercle."""
    outer = v.dial_diam / 2 + v.base_view_width - v.dial_tab_height
    return outer, outer - v.base_view_width


def window_bottom() -> tuple[float, float]:
    """Construit le point le plus bas de la fenêtre en arc de cercle, congé compris."""
    # Le congé du bout de la fenêtre est un cercle tangent à l'arc extérieur : son centre
    # est à (rayon - congé) du centre du cadran, un peu avant le bout de la fenêtre.
    ring = view_radii()[0] - v.fillet
    angle = radians(base_view_angle) - asin(v.fillet / ring)
    return -ring * cos(angle), -ring * sin(angle) - v.fillet


def left_strip_edge_y() -> float:
    """Construit la hauteur du bord de la languette de gauche."""
    # Le bord est à hauteur du bas de la fenêtre, tangent à son congé : pas de ressaut.
    return window_bottom()[1]


def view_tip() -> Sketch:
    """Construit l'esquisse de la pointe de matière laissée par la fenêtre, à retirer."""
    # La fenêtre sort du bord gauche du socle en laissant une pointe de matière effilée.
    # On retire cette pointe jusqu'au bord de la languette de gauche, mais seulement
    # hors du cercle extérieur de la fenêtre : on ne touche pas au panneau côté cadran.
    half, outer = v.base_size / 2, view_radii()[0]
    top = -sqrt(outer**2 - half**2) + 1  # un peu au-dessus de la pointe
    bottom = left_strip_edge_y()
    with BuildSketch() as sketch:
        with Locations((-half / 2 - 0.5, (top + bottom) / 2)):
            Rectangle(half + 1, top - bottom)
        Circle(outer, mode=Mode.SUBTRACT)
        # Prolongement du bord jusqu'au point le plus bas du congé de la fenêtre
        left, right = -half - 1, window_bottom()[0]
        with Locations(((left + right) / 2, bottom + 0.5)):
            Rectangle(right - left, 1)
    return sketch.sketch_local


def view_window() -> Sketch:
    """Construit la fenêtre en arc de cercle, décalée vers l'extérieur du cadran."""
    outer, inner = view_radii()
    with BuildSketch() as sketch:
        with BuildSketch(Rotation(90, 0, -180)):
            Circle(outer, base_view_angle, None)
        Circle(inner, mode=Mode.SUBTRACT)
    return sketch.sketch_local


def front_corners(vertices: ShapeList[Vertex]) -> list[Vertex]:
    """Retourne les sommets du panneau avant à arrondir, sauf au bas de la fenêtre."""
    min_pos, max_pos = -v.base_size / 2 + 1, v.base_size
    corners = vertices.filter_by_position(Axis.Y, min_pos, max_pos)
    window_bottom = u.polar_vertices(
        corners,
        180 + len(v.dials) * v.dial_slot_step,
        (v.dial_disc_diam / 2, v.dial_disc_diam / 2 - v.dial_slot_width),
    )
    return [p for p in corners if p not in window_bottom]


def strip_fit(edge: Edge, x: float, width: float) -> tuple[float, float]:
    """Construit le retrait des deux bouts de la pliure, pour la largeur et la position."""
    # La pliure ne garde que la largeur voulue, centrée en x sur le bord libre
    start, end = edge.position_at(0).X, edge.position_at(1).X
    low, high = (
        max(0, x - width / 2 - min(start, end)),
        max(0, max(start, end) - x - width / 2),
    )
    return (low, high) if start < end else (high, low)


def strip_neck(spacing: float, x: float, edge_y: float, width: float) -> Part:
    """Construit la tête de la languette, jusqu'à l'extérieur du panneau arrière."""
    thickness, radius = v.material_thickness, v.bend_radius
    start = radius + thickness
    length = 2 * (radius + thickness) + spacing - start
    width = width - 2 * v.base_strip_stop - 2 * v.base_strip_clearance
    z = edge_y + radius + thickness / 2
    with BuildPart() as builder, Locations((x, start + length / 2, z)):
        Box(width, length, thickness)
    return builder.part


def base() -> Part:
    """Construit la pièce correspondant au socle."""
    thickness, radius = v.material_thickness, v.bend_radius
    # Longueur plane ajoutée entre les deux pliages, pour écarter les deux panneaux
    spacing = v.base_play + len(v.dials) * v.material_thickness - 2 * radius
    # Languettes (x du centre, y du bord, hauteur de l'échancrure, largeur) : à droite juste
    # sous l'axe du cadran, à gauche sur le bord plat laissé sous la pointe de la fenêtre
    left = base_left_strip_pos - v.base_size / 2
    strips = [
        (
            u.base_right_strip_pos,
            -u.base_right_strip_drop,
            u.base_right_strip_drop,
            v.base_right_strip_width,
        ),
        (left, left_strip_edge_y(), 0, v.base_left_strip_width),
    ]
    necks = []

    with BuildPart() as builder:
        with BuildSheet(Plane.XZ, thickness=thickness, bend_radius=radius) as sheet:
            with BuildSketch():
                Rectangle(v.base_size, v.base_size)
            bottom = sheet.rims().group_by(Axis.Y)[0]
            if spacing:  # deux pliages à 90° avec une paroi plane entre eux
                flange(bottom, angle=-90, length=spacing)
                bottom = sheet.rims().filter_by(Axis.X).sort_by(Axis.Z)[0]
                flange(bottom, angle=-90, length=v.base_size)

            with BuildSketch(mode=Mode.SUBTRACT):
                insert(front_cutter())

            fillet(front_corners(sheet.vertices()), v.fillet)

            with BuildSketch(mode=Mode.SUBTRACT):
                Circle(v.rivet_diam / 2)
            with Locations(Plane(sheet.flats().sort_by(Axis.Z)[0])):
                Circle(v.rivet_diam / 2, mode=Mode.SUBTRACT)

            # Fenêtre du panneau avant, pour voir le bout des languettes, avec ses congés
            with BuildSketch(mode=Mode.SUBTRACT):
                insert(view_window())
            window_end = u.polar_vertices(
                sheet.vertices(),
                base_view_angle - 180,
                view_radii(),
            )
            fillet(window_end, v.fillet)

            # Chanfrein horizontal de la pointe de la fenêtre au bord gauche, avec congés
            with BuildSketch(mode=Mode.SUBTRACT):
                insert(view_tip())
            tip_y = left_strip_edge_y()
            tip_corners = sheet.vertices().filter_by_position(
                Axis.Y,
                tip_y - v.tolerance,
                tip_y + v.tolerance,
            )
            fillet(
                tip_corners.filter_by_position(Axis.X, -v.base_size, -v.base_size / 2 + 1),
                v.fillet,
            )

            for x, edge_y, notch_height, width in strips:
                # Le panneau avant est échancré pour abaisser la bande sous son bord
                if notch_height:
                    notch_pos = x, edge_y + notch_height / 2
                    with BuildSketch(mode=Mode.SUBTRACT), Locations(notch_pos):
                        Rectangle(width, notch_height)

                # Bande pliée vers l'arrière depuis le bord libre.
                # Sa base vient en butée contre le panneau arrière, sa tête traverse la
                # fenêtre de la tôle arrière, qui retient la base de la languette.
                edge = sheet.rims().filter_by(Axis.X).sort_by_distance((x, edge_y, 0))[0]
                flange(edge, radius + spacing, -90, gaps=strip_fit(edge, x, width))
                necks.append((x, edge_y, width))

                back_z = sheet.flats().sort_by(Face.area)[-1].center().Z
                wall_z = edge_y + radius + thickness / 2
                with Locations((x, wall_z, back_z)):
                    window = (
                        width - 2 * v.base_strip_stop,
                        thickness + 2 * v.base_strip_clearance,
                    )
                    Rectangle(*window, mode=Mode.SUBTRACT)
        thicken()
        for x, edge_y, width in necks:
            insert(strip_neck(spacing, x, edge_y, width))

    part = builder.part
    part.label = v.base[0]
    part.color = Color(v.base[1])
    return part
