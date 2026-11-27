"""Vérifie que la tôle des cadrans, une fois dépliée, ne se superpose pas."""

import pytest
from build123d import *

from kijuma import values as v
from kijuma.dial import dial_sheet, flap_angles, flap_pocket

AREA_TOLERANCE = 1e-3  # mm²


def flat_pattern(index: int) -> tuple[Face, list[Face], Sketch, Vector]:
    """Retourne la plaque, la languette dépliée, son empreinte et l'origine du cadran."""
    extra = (len(v.dials) - 1 - index) * v.material_thickness
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
    assert footprint.area - covered < AREA_TOLERANCE
