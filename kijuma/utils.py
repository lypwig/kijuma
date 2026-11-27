"""Fonctions utilitaires."""

from collections.abc import Iterable as Itr
from math import cos, hypot, radians, sin

from build123d import *

from . import values as v

# Position horiz. de la languette de droite : centrée entre le disque central et le cadran
base_right_strip_pos = (v.dial_disc_diam + v.dial_diam) / 4
base_right_strip_drop = (v.material_thickness + v.bend_radius) / 2  # abaissement languette


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
