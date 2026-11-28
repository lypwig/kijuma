"""Vérifie que la tôle des cadrans, une fois dépliée, ne se superpose pas."""

from math import hypot

import pytest
from build123d import *

from kijuma import values as v
from kijuma.dial import (
    dial,
    dial_sheet,
    flap_angles,
    flap_pocket,
    flap_teeth,
    flap_teeth_points,
)

AREA_TOLERANCE = 1e-3  # mm²


def flat_pattern(index: int) -> tuple[Face, list[Face], Sketch, Vector]:
    """Retourne la plaque, la languette dépliée, son empreinte et l'origine du cadran."""
    extra = (len(v.dials) - 1 - index) * v.cardboard_thickness
    _, sheet = dial_sheet(index * v.dial_tab_step, index * v.dial_slot_step, extra)
    flat, _ = unfold(sheet.sheet_local, sheet_parameters=sheet.sheet_parameters)
    plate, *flap = sorted(flat.faces(), key=lambda f: -f.area)

    # Le dépliage est translaté : on retrouve l'origine du cadran grâce au trou du rivet
    rivet = next(
        e
        for e in plate.edges()
        if e.geom_type == GeomType.CIRCLE
        and abs(e.radius - v.rivet_diam / 2) < AREA_TOLERANCE
        and e.length > v.rivet_diam
    )
    flap_start, slot_length = flap_angles(index * v.dial_slot_step)
    pocket = flap_pocket(flap_start, slot_length, v.dial_flap_depth + extra)
    return plate, flap, pocket, rivet.arc_center


@pytest.mark.parametrize("index", range(len(v.dials)))
def test_flap_does_not_overlap_plate(index: int) -> None:
    """La languette dépliée retombe dans le vide du disque, pas sur de la tôle."""
    plate, flap, pocket, origin = flat_pattern(index)
    footprint = pocket.face().moved(Location(origin))
    kept = [f & footprint for f in flap]  # le bout est ensuite taillé selon le secteur
    overlap = sum((plate & f).area for f in kept)
    assert overlap < AREA_TOLERANCE, f"{overlap:.4f} mm² de tôle superposée"


@pytest.mark.parametrize("index", range(len(v.dials)))
def test_pocket_is_covered_by_flap(index: int) -> None:
    """Le vide taillé dans le disque n'est pas plus grand que la languette dépliée."""
    _, flap, pocket, origin = flat_pattern(index)
    footprint = pocket.face().moved(Location(origin))
    covered = sum((footprint & f).area for f in flap)
    # Seules les dents, taillées dans le bout de la languette, ne recouvrent pas le vide
    extra = (len(v.dials) - 1 - index) * v.cardboard_thickness
    start, end = flap_angles(index * v.dial_slot_step)
    teeth = flap_teeth(start, end, v.dial_flap_depth + extra)
    teeth_area = teeth.area if teeth is not None else 0
    assert footprint.area - covered < teeth_area + AREA_TOLERANCE


TOLERANCE = 0.01  # mm


@pytest.mark.parametrize("index", range(len(v.dials)))
def test_flap_tip_has_teeth(index: int) -> None:
    """Le bout rabattu de la languette de chaque cadran est denté de bord à bord."""
    extra = (len(v.dials) - 1 - index) * v.cardboard_thickness
    start, end = flap_angles(index * v.dial_slot_step)
    depth = v.dial_flap_depth + extra
    points = flap_teeth_points(start, end, depth)
    part = dial(index * v.dial_tab_step, index * v.dial_slot_step, extra)
    # Le bout rabattu est la face la plus avancée : la tôle y est à `depth + 2 e + r`
    tip_y = -(depth + 2 * v.cardboard_thickness + v.bend_radius)
    # Un côté de dent va du sommet au creux, un demi-pas plus loin et plus profond
    side = hypot(v.dial_flap_teeth_step / 2, v.dial_flap_teeth_depth)
    sides = [
        e
        for e in part.edges()
        if e.geom_type == GeomType.LINE
        and pytest.approx(tip_y, abs=TOLERANCE) == e.center().Y
        and pytest.approx(side, abs=TOLERANCE) == e.length
    ]
    assert points
    # Les côtés sont les segments en pente du zigzag, hors les deux fonds prolongés
    assert len(sides) == len(points) - 3
