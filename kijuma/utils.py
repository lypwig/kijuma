"""Valeurs dérivées et fonctions utilitaires."""

from collections.abc import Iterable as Itr
from math import cos, hypot, radians, sin

from build123d import *

from . import values as v

disc_radius = v.dial_disc_diam / 2  # rayon du disque central
dial_radius = v.dial_diam / 2  # rayon extérieur du cadran
slot_radii = (
    disc_radius,
    disc_radius - v.dial_slot_width,
)  # rayons de la fente, ext. et int.
base_slot_angle = (
    180 + len(v.dials) * v.dial_slot_step
)  # angle du bout de la fente du socle

# Position horiz. de la languette de droite : centrée entre le disque central et le cadran
base_right_strip_pos = (v.dial_disc_diam + v.dial_diam) / 4
base_right_strip_drop = (v.material_thickness + v.bend_radius) / 2  # abaissement languette

# Distance de la face avant du volet à celle du panneau avant, une fois le volet replié
cover_offset = 2 * v.bend_radius + v.material_thickness


def notch_half(strip_width: float) -> float:
    """Retourne la demi-largeur de l'entaille qui reçoit une languette de cette largeur."""
    return strip_width / 2 + v.dial_notch_size


def point_vertices(vertices: Itr[Vertex], points: Itr[tuple[float, float]]) -> list[Vertex]:
    """Retourne les sommets situés aux points (x, y) donnés."""
    points = list(points)
    return [
        p
        for p in vertices
        if any(hypot(p.X - px, p.Y - py) < v.tolerance for px, py in points)
    ]


def polar_vertices(vertices: Itr[Vertex], angle: float, radii: Itr[float]) -> list[Vertex]:
    """Retourne les sommets situés à l'angle (en degrés) et aux rayons donnés."""
    return point_vertices(
        vertices,
        [(r * cos(radians(angle)), r * sin(radians(angle))) for r in radii],
    )
