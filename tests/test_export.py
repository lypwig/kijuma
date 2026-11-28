"""Vérifie le rangement des patrons sur la feuille et l'export SVG."""

from itertools import combinations
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from build123d import *

from kijuma import values as v
from kijuma.dial import dial_sheet
from kijuma.export import export_svg, flat_piece, flat_pieces, label_placement
from kijuma.nest import Placement, nest

ROTATION_STEP = 90  # pas grossier, pour que le test reste rapide


@pytest.fixture(scope="module")
def placements() -> list[Placement]:
    """Les patrons du socle et des cadrans, rangés sur la feuille."""
    return nest(flat_pieces(), step=ROTATION_STEP)


def placed_outlines(placements: list[Placement]) -> list[Face]:
    """Retourne les contours de découpe, à leur place sur la feuille."""
    return [p.placed().outline for p in placements]


def test_every_piece_is_placed(placements: list[Placement]) -> None:
    """Le socle et chaque cadran ont un patron sur la feuille."""
    labels = sorted(p.piece.label for p in placements)
    assert labels == sorted([v.base[0], *(label for label, _ in v.dials)])


def test_pieces_stay_apart(placements: list[Placement]) -> None:
    """Deux patrons sont séparés d'au moins l'écart demandé, à un pixel près."""
    outlines = placed_outlines(placements)
    gap = min(a.distance_to(b) for a, b in combinations(outlines, 2))
    assert gap >= v.export_gap - v.export_resolution


def test_pieces_stay_within_margins(placements: list[Placement]) -> None:
    """Les patrons restent dans la feuille, à distance de son bord."""
    length, width = v.export_sheet
    margin = v.export_margin - v.export_resolution
    for outline in placed_outlines(placements):
        box = outline.bounding_box()
        assert margin <= box.min.X <= box.max.X <= length - margin
        assert margin <= box.min.Y <= box.max.Y <= width - margin


def test_svg_has_cuts_and_folds(placements: list[Placement], tmp_path: Path) -> None:
    """Le SVG a un calque de découpe, un de pliage, et un cadre."""
    path = tmp_path / "kijuma.svg"
    export_svg(placements, str(path))
    root = ET.parse(path).getroot()  # noqa: S314
    layers = {g.get("id"): list(g) for g in root.iter("{http://www.w3.org/2000/svg}g")}
    assert set(layers) >= {"Cadre", "Decoupe", "Pliage"}
    assert layers["Decoupe"]
    assert layers["Pliage"]


def test_flap_sides_are_cut() -> None:
    """Les côtés de la languette dépliée, contre la tôle voisine, sont à découper."""
    piece = flat_piece("Cadran", dial_sheet(0)[1])
    contour = sum(
        w.length for w in (piece.outline.outer_wire(), *piece.outline.inner_wires())
    )
    cut = sum(w.length for w in piece.cuts)
    # Sans les côtés, la languette, fusionnée à la tôle, n'aurait aucun trait de découpe
    assert cut > contour + v.dial_flap_fold


def test_label_svg_has_outline_and_text(tmp_path: Path) -> None:
    """Le SVG du label a son contour à découper et son texte, sur deux calques."""
    path = tmp_path / "label.svg"
    export_svg([label_placement()], str(path))
    root = ET.parse(path).getroot()  # noqa: S314
    layers = {g.get("id"): list(g) for g in root.iter("{http://www.w3.org/2000/svg}g")}
    assert len(layers["Decoupe"]) == 1
    assert layers["Gravure"]
