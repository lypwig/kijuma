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
    back = (len(v.dials) + 2) * v.material_thickness
    # Le congé retire `fillet` de chaque côté du coin vif (angle droit)
    reach = (bottom.length + v.fillet) * cos(radians(v.base_support_tilt))
    assert near.center().Y + reach == pytest.approx(
        back + v.base_support_length,
        abs=TOLERANCE,
    )


def test_cover_is_folded_over_front_face() -> None:
    """Le volet recouvre la face avant, du bas du panneau et jusqu'au disque du rivet."""
    body = max(base().solids(), key=lambda s: s.volume)
    front_y = -v.material_thickness  # le panneau avant occupe y de 0 à l'épaisseur
    covers = [
        f
        for f in body.faces()
        if f.geom_type == GeomType.PLANE
        and f.normal_at().Y < -FLAT_NORMAL
        and front_y > f.center().Y
    ]
    assert len(covers) == 1, "face extérieure du volet introuvable"
    box = covers[0].bounding_box()
    disc = v.base_cover_disc_diam / 2
    assert pytest.approx(v.base_size / 2, abs=TOLERANCE) == box.max.X
    assert pytest.approx(-v.base_size / 2, abs=TOLERANCE) == box.min.Z
    # Le disque déborde du volet, à gauche et en haut, autour du rivet à l'origine
    assert pytest.approx(-disc, abs=TOLERANCE) == box.min.X
    assert pytest.approx(disc, abs=TOLERANCE) == box.max.Z


def test_cover_has_rivet_hole() -> None:
    """Le volet est percé d'un trou du diamètre du rivet, centré sur l'origine."""
    body = max(base().solids(), key=lambda s: s.volume)
    holes = [
        e
        for e in body.edges()
        if e.geom_type == GeomType.CIRCLE
        and pytest.approx(v.rivet_diam / 2, abs=TOLERANCE) == e.radius
        and pytest.approx(0, abs=TOLERANCE) == e.arc_center.X
        and e.arc_center.Y < 0
    ]
    assert holes, "trou du rivet introuvable dans le volet"


def test_cover_left_side_goes_down_at_45_degrees() -> None:
    """Depuis le point le plus bas du disque, le bord du volet descend à 45° à droite."""
    body = max(base().solids(), key=lambda s: s.volume)
    outer_y = -(2 * v.bend_radius + v.material_thickness)  # face avant du volet
    # Arêtes obliques de la face avant du volet
    slanted = [
        e
        for e in body.edges()
        if e.geom_type == GeomType.LINE
        and pytest.approx(outer_y, abs=TOLERANCE) == e.center().Y
        and abs(e.end_point().X - e.start_point().X) > TOLERANCE
        and abs(e.end_point().Z - e.start_point().Z) > TOLERANCE
    ]
    assert len(slanted) == 1
    run = slanted[0].end_point().X - slanted[0].start_point().X
    rise = slanted[0].end_point().Z - slanted[0].start_point().Z
    assert pytest.approx(-1, abs=TOLERANCE) == rise / run
    # La droite passe par le point le plus bas du disque, à la verticale du rivet
    point = slanted[0].start_point()
    assert pytest.approx(-v.base_cover_disc_diam / 2, abs=TOLERANCE) == point.X + point.Z


def test_cover_has_three_rounded_corners() -> None:
    """Les trois angles libres du volet sont arrondis avec le rayon des angles."""
    body = max(base().solids(), key=lambda s: s.volume)
    outer_y = -(2 * v.bend_radius + v.material_thickness)  # face avant du volet
    # Le trou du rivet est exclu : son centre est sur l'axe, à l'origine
    arcs = [
        e
        for e in body.edges()
        if e.geom_type == GeomType.CIRCLE
        and pytest.approx(outer_y, abs=TOLERANCE) == e.center().Y
        and pytest.approx(v.fillet, abs=TOLERANCE) == e.radius
        and v.fillet**2 < e.arc_center.X**2 + e.arc_center.Z**2
    ]
    assert len(arcs) == 3  # noqa: PLR2004


def test_front_panel_corner_above_fold_is_sharp() -> None:
    """Le coin du panneau avant en haut du pli du volet n'est pas arrondi."""
    body = max(base().solids(), key=lambda s: s.volume)
    half = v.base_size / 2
    rounded = [
        f
        for f in body.faces()
        if f.geom_type == GeomType.CYLINDER
        and half - v.fillet <= f.center().X <= half
        and -v.fillet <= f.center().Z <= 0
        and 0 <= f.center().Y <= v.material_thickness
    ]
    assert not rounded
