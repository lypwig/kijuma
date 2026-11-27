"""Vérifie la forme de la patte du support du socle."""

from math import atan2, degrees

import pytest
from build123d import *

from kijuma import values as v
from kijuma.base import base

TOLERANCE = 0.01  # mm ou degrés
VERTICES = 4  # sommets d'un parallélogramme
FLAT_NORMAL = 0.99  # composante minimale de la normale d'une face orientée selon X

Border = list[tuple[float, float]]  # sommets (y, z) d'un bord vertical de la patte


@pytest.fixture(scope="module")
def sides() -> tuple[Border, Border]:
    """Retourne les bords vertical côté panneau et côté bout de la patte de gauche."""
    body = max(base().solids(), key=lambda s: s.volume)
    outer_x = -(v.base_size / 2 + v.material_thickness / 2)  # au-delà du panneau arrière
    outer = [
        f
        for f in body.faces()
        if f.geom_type == GeomType.PLANE
        and f.normal_at().X < -FLAT_NORMAL
        and outer_x > f.center().X
    ]
    assert len(outer) == 1, "face extérieure de la patte introuvable"
    points = sorted((p.Y, p.Z) for p in outer[0].vertices())
    assert len(points) == VERTICES, "la patte doit avoir quatre sommets"
    return sorted(points[:2]), sorted(points[2:])


def test_support_sides_are_vertical(sides: tuple[Border, Border]) -> None:
    """Les deux bords de la patte sont verticaux et mesurent la hauteur voulue."""
    for side in sides:
        assert side[0][0] == pytest.approx(side[1][0], abs=TOLERANCE)
        assert side[1][1] - side[0][1] == pytest.approx(
            v.base_support_height,
            abs=TOLERANCE,
        )


def test_support_length(sides: tuple[Border, Border]) -> None:
    """La patte s'étend de la longueur voulue derrière le panneau arrière."""
    back = v.base_play + (len(v.dials) + 2) * v.material_thickness
    assert sides[1][0][0] - back == pytest.approx(v.base_support_length, abs=TOLERANCE)


def test_support_bottom_rises_by_tilt(sides: tuple[Border, Border]) -> None:
    """Le bas de la patte monte vers l'arrière de l'inclinaison du socle."""
    (near_y, near_z), (far_y, far_z) = sides[0][0], sides[1][0]
    angle = degrees(atan2(far_z - near_z, far_y - near_y))
    assert angle == pytest.approx(v.base_support_tilt, abs=TOLERANCE)
