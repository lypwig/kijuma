"""Vérifie la forme de la patte du support du socle."""

from math import atan2, cos, degrees, hypot, pi, radians, sin, tan

import pytest
from build123d import *

from kijuma import utils as u
from kijuma import values as v
from kijuma.base import base, cover_teeth_points, wrap_wall_length

TOLERANCE = 0.01  # mm ou degrés
FLAT_NORMAL = 0.99  # composante minimale de la normale d'une face orientée selon X


@pytest.fixture(scope="module")
def body() -> Solid:
    """Retourne le corps du socle, construit une seule fois avec les valeurs courantes."""
    return max(base().solids(), key=lambda s: s.volume)


@pytest.fixture(scope="module")
def outline() -> list[Edge]:
    """Retourne les arêtes de la face extérieure de la patte, pliée à 90°."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(v, "base_support_angle", 90)
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


@pytest.fixture(scope="module")
def open_cover() -> Solid:
    """Retourne le corps du socle, avec le volet déplié à 90° du panneau avant."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(v, "base_cover_angle", 90)
        return max(base().solids(), key=lambda s: s.volume)


@pytest.fixture(scope="module")
def open_wrap() -> Solid:
    """Retourne le corps du socle, avec le rabat de la tranche déplié à plat (0°)."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(v, "base_wrap_angle", 0)
        return max(base().solids(), key=lambda s: s.volume)


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
    """Le côté du panneau est vertical, et plus long que la largeur de la patte."""
    near = lines(outline)[0]
    assert direction(near)[0] == pytest.approx(0, abs=TOLERANCE)
    width = v.base_support_height / cos(radians(v.base_support_tilt))
    assert near.length == pytest.approx(width, abs=TOLERANCE)


def test_support_width(outline: list[Edge]) -> None:
    """Le bout mesure la largeur voulue, moins les deux congés."""
    end = lines(outline)[3]
    expected = v.base_support_height - 2 * v.fillet
    assert end.length == pytest.approx(expected, abs=TOLERANCE)


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
    back = (len(v.dials) + 2) * v.material_thickness + v.bend_radius  # fin du pli
    # Le congé retire `fillet` de chaque côté du coin vif (angle droit)
    reach = (bottom.length + v.fillet) * cos(radians(v.base_support_tilt))
    assert near.center().Y + reach == pytest.approx(
        back + v.base_support_length,
        abs=TOLERANCE,
    )


def test_cover_is_folded_over_front_face(body: Solid) -> None:
    """Le volet recouvre la face avant, du bas du panneau et jusqu'au disque du rivet."""
    outer_y = -(2 * v.bend_radius + v.material_thickness)  # face avant du volet
    covers = [
        f
        for f in body.faces()
        if f.geom_type == GeomType.PLANE
        and f.normal_at().Y < -FLAT_NORMAL
        and pytest.approx(outer_y, abs=TOLERANCE) == f.center().Y
    ]
    assert len(covers) == 1, "face extérieure du volet introuvable"
    box = covers[0].bounding_box()
    disc = v.base_cover_disc_diam / 2
    # Le pli du volet est enfoncé dans le socle, pour laisser passer le rabat
    assert pytest.approx(v.base_size / 2 - u.cover_inset, abs=TOLERANCE) == box.max.X
    assert pytest.approx(-v.base_size / 2, abs=TOLERANCE) == box.min.Z
    # Le disque déborde du volet, à gauche et en haut, autour du rivet à l'origine
    assert pytest.approx(-disc, abs=TOLERANCE) == box.min.X
    assert pytest.approx(disc, abs=TOLERANCE) == box.max.Z


def test_cover_has_rivet_hole(body: Solid) -> None:
    """Le volet est percé d'un trou du diamètre du rivet, centré sur l'origine."""
    holes = [
        e
        for e in body.edges()
        if e.geom_type == GeomType.CIRCLE
        and pytest.approx(v.rivet_diam / 2, abs=TOLERANCE) == e.radius
        and pytest.approx(0, abs=TOLERANCE) == e.arc_center.X
        and e.arc_center.Y < 0
    ]
    assert holes, "trou du rivet introuvable dans le volet"


def test_cover_unfolds_to_its_angle(open_cover: Solid) -> None:
    """Déplié à 90°, le volet part vers l'avant, avec son disque et son trou du rivet."""
    # Le rivet est à la distance `base_size / 2` du pli, moins son enfoncement, et le disque
    # le déborde de son rayon
    # et le centre du pli est à `bend_radius` devant la face avant.
    rivet_y = -(v.bend_radius + v.base_size / 2 - u.cover_inset)
    disc = v.base_cover_disc_diam / 2
    assert pytest.approx(rivet_y - disc, abs=TOLERANCE) == open_cover.bounding_box().min.Y
    holes = [
        e
        for e in open_cover.edges()
        if e.geom_type == GeomType.CIRCLE
        and pytest.approx(v.rivet_diam / 2, abs=TOLERANCE) == e.radius
        and pytest.approx(rivet_y, abs=TOLERANCE) == e.arc_center.Y
    ]
    assert len(holes) == 2  # noqa: PLR2004


def wrap_outer_y() -> float:
    """Retourne l'ordonnée de la face avant du rabat, replié devant le volet."""
    inner_y = -(2 * v.bend_radius + v.material_thickness + v.base_wrap_gap)
    return inner_y - v.material_thickness


def test_wrap_is_folded_over_cover(body: Solid) -> None:
    """Le rabat contourne la tranche et recouvre le volet, du bas à la moitié du socle."""
    wraps = [
        f
        for f in body.faces()
        if f.geom_type == GeomType.PLANE
        and f.normal_at().Y < -FLAT_NORMAL
        and pytest.approx(wrap_outer_y(), abs=TOLERANCE) == f.center().Y
    ]
    assert len(wraps) == 1, "face extérieure du rabat introuvable"
    box = wraps[0].bounding_box()
    half, disc = v.base_size / 2, v.dial_disc_diam / 2
    # Replié, le rabat part de la tranche et va vers la gauche, le disque débordant au-delà
    # de son bout et de son bord haut
    tip = half - v.base_wrap_length
    assert pytest.approx(min(tip, -disc), abs=TOLERANCE) == box.min.X
    assert pytest.approx(-half, abs=TOLERANCE) == box.min.Z
    assert pytest.approx(max(v.base_wrap_height - half, disc), abs=TOLERANCE) == box.max.Z
    # La tranche contourne le bord, avec le même rayon de pli que les autres plis
    edge = body.bounding_box().max.X
    expected = half + v.bend_radius + v.material_thickness
    assert pytest.approx(expected, abs=TOLERANCE) == edge
    walls = [
        f
        for f in body.faces()
        if f.geom_type == GeomType.PLANE
        and f.normal_at().X > FLAT_NORMAL
        and pytest.approx(expected, abs=TOLERANCE) == f.center().X
    ]
    assert len(walls) == 1, "face extérieure de la tranche introuvable"
    wall = walls[0].bounding_box()
    assert pytest.approx(wrap_wall_length(), abs=TOLERANCE) == wall.max.Y - wall.min.Y


def test_wrap_has_disc_and_rivet_head_hole(body: Solid) -> None:
    """Le rabat a le disque des cadrans, et un trou pour la tête du rivet en son centre."""
    circles = [
        e
        for e in body.edges()
        if e.geom_type == GeomType.CIRCLE
        and pytest.approx(wrap_outer_y(), abs=TOLERANCE) == e.center().Y
    ]
    holes = [e for e in circles if v.rivet_head_hole / 2 == pytest.approx(e.radius)]
    assert len(holes) == 1
    assert pytest.approx(0, abs=TOLERANCE) == holes[0].arc_center.X
    assert pytest.approx(0, abs=TOLERANCE) == holes[0].arc_center.Z
    assert any(pytest.approx(v.dial_disc_diam / 2) == e.radius for e in circles)


def test_wrap_unfolds_to_its_angle(open_wrap: Solid) -> None:
    """Déplié à 0°, la tranche et le rabat prolongent à plat le panneau arrière."""
    box = open_wrap.bounding_box()
    # Les deux plis sont dépliés : le rabat part vers la droite, sans rien devant le volet
    reach = v.base_size / 2 + wrap_wall_length() + v.base_wrap_length
    # À 0,01° près : le pli ne peut pas être nul, ce qui dévie le bout du rabat
    assert pytest.approx(reach, abs=0.1) == box.max.X
    assert pytest.approx(-u.cover_offset, abs=0.1) == box.min.Y
    # Le trou du rivet suit le rabat : il est dans son plan, au bout de la tranche
    center = v.base_size + wrap_wall_length()
    holes = [
        e
        for e in open_wrap.edges()
        if e.geom_type == GeomType.CIRCLE
        and v.rivet_head_hole / 2 == pytest.approx(e.radius)
    ]
    assert len(holes) == 2  # noqa: PLR2004
    assert pytest.approx(center, abs=0.1) == holes[0].arc_center.X


def test_cover_left_side_goes_down_at_45_degrees(body: Solid) -> None:
    """Depuis le point le plus bas du disque, le bord du volet descend à 45° à droite."""
    outer_y = -(2 * v.bend_radius + v.material_thickness)  # face avant du volet
    # Arêtes obliques de la face avant du volet
    slanted = [
        e
        for e in body.edges()
        if e.geom_type == GeomType.LINE
        and pytest.approx(outer_y, abs=TOLERANCE) == e.center().Y
        and abs(e.end_point().X - e.start_point().X) > TOLERANCE
        and abs(e.end_point().Z - e.start_point().Z) > TOLERANCE
        and e.length > v.base_cover_disc_diam / 4  # hors des côtés des dents
    ]
    assert len(slanted) == 1
    run = slanted[0].end_point().X - slanted[0].start_point().X
    rise = slanted[0].end_point().Z - slanted[0].start_point().Z
    assert pytest.approx(-1, abs=TOLERANCE) == rise / run
    # La droite passe par le point le plus bas du disque, à la verticale du rivet
    point = slanted[0].start_point()
    assert pytest.approx(-v.base_cover_disc_diam / 2, abs=TOLERANCE) == point.X + point.Z


def test_cover_has_one_rounded_corner(body: Solid) -> None:
    """Seul l'angle entre la pente et le bas du volet est arrondi, au rayon des angles."""
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
    assert len(arcs) == 1


def test_front_panel_corner_above_fold_is_sharp(body: Solid) -> None:
    """Le coin du panneau avant en haut du pli du volet n'est pas arrondi."""
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


def support_area() -> float:
    """Retourne l'aire attendue de la face extérieure de la patte, quel que soit son pli."""
    # Dans le plan de la patte : x le long de la patte depuis la fin du pli, y vertical
    width, length = v.base_support_height, v.base_support_length
    tilt = radians(v.base_support_tilt)
    far = length, length * tan(tilt)
    top = far[0] - width * sin(tilt), far[1] + width * cos(tilt)
    points = [(0, 0), far, top, (0, width / cos(tilt))]
    shifted = [*points[1:], points[0]]
    pairs = zip(points, shifted, strict=True)
    double = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in pairs)
    # Chacun des deux coins du bout, à angle droit, perd `r² (1 - pi/4)`
    return abs(double) / 2 - 2 * v.fillet**2 * (1 - pi / 4)


@pytest.mark.parametrize("angle", [0, 45, 90, 175, 180])
def test_support_angle_is_configurable(
    angle: float,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """La patte garde le même contour dans son plan, quel que soit l'angle de pli."""
    monkeypatch.setattr(v, "base_support_angle", angle)
    part = base()
    assert part.is_valid
    body = max(part.solids(), key=lambda s: s.volume)
    rad = radians(max(angle, 0.01))
    normal = -sin(rad), -cos(rad)  # normale extérieure de la patte
    back_y = (len(v.dials) + 2) * v.material_thickness
    walls = [
        f
        for f in body.faces()
        if f.geom_type == GeomType.PLANE
        and pytest.approx(0, abs=TOLERANCE) == f.normal_at().Z
        and f.normal_at().X * normal[0] + f.normal_at().Y * normal[1] > FLAT_NORMAL
        # Hors du panneau arrière lui-même : à côté de lui, ou derrière lui
        and (-v.base_size / 2 - TOLERANCE > f.center().X or back_y + 0.2 < f.center().Y)
    ]
    assert len(walls) == 1, "face extérieure de la patte introuvable"
    assert pytest.approx(support_area(), abs=0.1) == walls[0].area


def test_cover_disc_arc_has_teeth(body: Solid) -> None:
    """L'arc du disque du volet est denté au pas exact, avec des dents entières."""
    outer_y = -(2 * v.bend_radius + v.material_thickness)  # face avant du volet
    radius, step = v.base_cover_disc_diam / 2, radians(v.base_cover_teeth_step)
    # Un côté de dent relie un sommet, sur le cercle, au creux à mi-pas, plus profond
    deep = radius - v.base_cover_teeth_depth
    side = hypot(radius - deep * cos(step / 2), deep * sin(step / 2))
    sides = [
        e
        for e in body.edges()
        if e.geom_type == GeomType.LINE
        and pytest.approx(outer_y, abs=TOLERANCE) == e.center().Y
        and pytest.approx(side, abs=TOLERANCE) == e.length
    ]
    # Chaque dent entière a deux côtés : un par segment du zigzag
    points = cover_teeth_points()
    assert len(sides) == len(points) - 1
    # Tous les sommets sont sur les multiples du pas
    peaks = [angle for angle, depth in points if depth == 0]
    assert all(
        angle % v.base_cover_teeth_step == pytest.approx(0, abs=1e-6) for angle in peaks
    )
