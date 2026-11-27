"""Vérifie la forme de la patte du support du socle."""

from math import atan2, cos, degrees, radians

import pytest
from build123d import *

from kijuma import values as v
from kijuma.base import base

TOLERANCE = 0.01  # mm ou degrés
FLAT_NORMAL = 0.99  # composante minimale de la normale d'une face orientée selon X


@pytest.fixture(scope="module")
def outline() -> list[Edge]:
    """Retourne les arêtes de la face extérieure de la patte, côté gauche."""
    body = max(base().solids(), key=lambda s: s.volume)
    outer_x = -(v.base_size / 2 + v.material_thickness / 2)  # au-delà du panneau arrière
    faces = [
        f
        for f in body.faces()
        if f.geom_type == GeomType.PLANE
        and f.normal_at().X < -FLAT_NORMAL
        and outer_x > f.center().X
    ]
    assert len(faces) == 1, "face extérieure de la patte introuvable"
    return list(faces[0].edges())


def direction(edge: Edge) -> tuple[float, float]:
    """Retourne la direction (y, z) d'une arête droite, orientée vers l'arrière."""
    delta = edge.end_point() - edge.start_point()
    sign = 1 if delta.Y > 0 else -1
    return sign * delta.Y / edge.length, sign * delta.Z / edge.length


def lines(outline: list[Edge]) -> tuple[Edge, Edge, Edge, Edge]:
    """Retourne les côtés droits : panneau, bas, haut, bout."""
    straight = [e for e in outline if e.geom_type == GeomType.LINE]
    near = min(straight, key=lambda e: abs(direction(e)[0]))
    others = [e for e in straight if e is not near]
    end = min(others, key=lambda e: e.length)
    sides = sorted((e for e in others if e is not end), key=lambda e: e.center().Z)
    return near, sides[0], sides[1], end


def test_support_has_two_rounded_corners(outline: list[Edge]) -> None:
    """Seuls les deux coins du bout sont arrondis, avec le rayon des angles."""
    arcs = [e for e in outline if e.geom_type == GeomType.CIRCLE]
    assert len(arcs) == 2  # noqa: PLR2004
    for arc in arcs:
        assert arc.radius == pytest.approx(v.fillet, abs=TOLERANCE)


def test_support_panel_side_is_vertical(outline: list[Edge]) -> None:
    """Le côté du panneau est vertical et mesure la hauteur voulue."""
    near = lines(outline)[0]
    assert direction(near)[0] == pytest.approx(0, abs=TOLERANCE)
    assert near.length == pytest.approx(v.base_support_height, abs=TOLERANCE)


def test_support_bottom_rises_by_tilt(outline: list[Edge]) -> None:
    """Le bas et le haut de la patte montent vers l'arrière de l'inclinaison du socle."""
    _, bottom, top, _ = lines(outline)
    for edge in (bottom, top):
        dy, dz = direction(edge)
        assert degrees(atan2(dz, dy)) == pytest.approx(v.base_support_tilt, abs=TOLERANCE)


def test_support_end_is_square(outline: list[Edge]) -> None:
    """Le bout est à angle droit avec le bas et le haut."""
    _, bottom, _, end = lines(outline)
    (by, bz), (ey, ez) = direction(bottom), direction(end)
    assert by * ey + bz * ez == pytest.approx(0, abs=TOLERANCE)


def test_support_length(outline: list[Edge]) -> None:
    """Le bas de la patte s'étend de la longueur voulue derrière le panneau arrière."""
    near, bottom, _, _ = lines(outline)
    back = v.base_play + (len(v.dials) + 2) * v.material_thickness
    # Le congé retire `fillet` de chaque côté du coin vif (angle droit)
    reach = (bottom.length + v.fillet) * cos(radians(v.base_support_tilt))
    assert near.center().Y + reach == pytest.approx(
        back + v.base_support_length,
        abs=TOLERANCE,
    )
