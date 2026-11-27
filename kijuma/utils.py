"""Fonctions utilitaires."""

from collections.abc import Iterable as Itr
from math import cos, hypot, radians, sin

from build123d import *

from . import values as v

base_right_strip_pos = 75  # position horiz. du centre de la languette au centre du cadran
base_right_strip_drop = v.bend_radius * 2  # de combien la languette droite est abaissée


def polar_vertices(vertices: Itr[Vertex], angle: float, radii: Itr[float]) -> list[Vertex]:
    """Retourne les sommets situés à l'angle (en degrés) et aux rayons donnés."""
    points = [(r * cos(radians(angle)), r * sin(radians(angle))) for r in radii]
    return [
        p
        for p in vertices
        if any(hypot(p.X - px, p.Y - py) < v.tolerance for px, py in points)
    ]
