"""Vérifie le label en papier fin tenu par les fentes verticales du rabat."""

import pytest
from build123d import *

from kijuma import values as v
from kijuma.base import base
from kijuma.label import label_outline, label_text, proposal_label


def paper_part() -> Solid:
    """Retourne le papier du label, à sa place sur l'assemblage."""
    return max(proposal_label().solids(), key=lambda s: s.volume)


@pytest.fixture
def paper(monkeypatch: pytest.MonkeyPatch) -> Solid:
    """Le papier du label, avec le rabat replié."""
    monkeypatch.setattr(v, "base_wrap_angle", 180)
    return paper_part()


def test_label_has_wrap_width_and_slot_height() -> None:
    """Le label est aussi large que le rabat, et aussi haut que les fentes."""
    size = label_outline().bounding_box().size
    assert pytest.approx(v.base_wrap_length) == size.X
    assert pytest.approx(v.base_wrap_slot_v_length) == size.Y


def test_label_is_thin_paper(paper: Solid) -> None:
    """Le label a l'épaisseur du papier, et le texte tient dedans."""
    assert pytest.approx(v.proposal_thickness) == paper.bounding_box().size.Y
    text = Compound(label_text()).bounding_box().size
    size = label_outline().bounding_box().size
    assert text.X < size.X
    assert text.Y < size.Y


def test_label_is_centered_between_slots(paper: Solid) -> None:
    """Le label est centré, en largeur, entre les fentes verticales du rabat."""
    half = v.base_size / 2
    side_margin, bottom_margin = v.base_wrap_slot_margin
    left = half - v.base_wrap_length + side_margin
    right = half - side_margin
    center = paper.bounding_box().center()
    assert pytest.approx((left + right) / 2) == center.X
    # En hauteur, il a celle des fentes, qui sont à `bottom_margin` du bas du socle
    box = paper.bounding_box()
    assert pytest.approx(-half + bottom_margin) == box.min.Z
    assert pytest.approx(-half + bottom_margin + v.base_wrap_slot_v_length) == box.max.Z


def test_label_rests_against_wrap(paper: Solid) -> None:
    """Le label est plaqué contre la carte graduée, elle-même contre le rabat."""
    front = base().bounding_box().min.Y
    assert pytest.approx(front - v.card_thickness) == paper.bounding_box().max.Y
    assert not paper.intersect(base())


@pytest.mark.parametrize("angle", [0, 45, 90, 135])
def test_label_follows_open_wrap(monkeypatch: pytest.MonkeyPatch, angle: float) -> None:
    """Le label suit le rabat ouvert : il reste contre lui, sans traverser le socle."""
    monkeypatch.setattr(v, "base_wrap_angle", angle)
    paper = paper_part()
    assert not paper.intersect(base())
    # Contre le rabat : à l'épaisseur de la carte près
    assert paper.distance_to(base()) < v.card_thickness + v.proposal_thickness
