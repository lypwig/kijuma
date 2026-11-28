"""Vérifie la carte graduée, en papier fin, plaquée contre le rabat."""

import pytest
from build123d import *

from kijuma import utils as u
from kijuma import values as v
from kijuma.base import base
from kijuma.card import card, card_centers_gap, card_outline
from kijuma.label import proposal_label


@pytest.fixture
def folded(monkeypatch: pytest.MonkeyPatch) -> None:
    """Écrit un rabat replié dans les valeurs."""
    monkeypatch.setattr(v, "base_wrap_angle", 180)


def test_card_is_a_slot_as_wide_as_the_dials_disc() -> None:
    """La carte est un rectangle aux bouts arrondis, de la largeur du disque des cadrans."""
    size = card_outline().bounding_box().size
    assert pytest.approx(2 * u.disc_radius) == size.X
    assert pytest.approx(card_centers_gap() + 2 * u.disc_radius) == size.Y


def test_card_centers_reach_lowest_slot() -> None:
    """Les centres des bouts sont du rivet à la fente horizontale du bas du rabat."""
    assert card_centers_gap() == pytest.approx(
        v.base_wrap_slot_drop + v.base_wrap_slot_step,
    )


@pytest.mark.usefixtures("folded")
def test_card_top_matches_the_disc() -> None:
    """Le haut de la carte est centré sur le rivet, avec le rayon du disque."""
    box = card().bounding_box()
    assert pytest.approx(u.disc_radius) == box.max.Z
    assert pytest.approx(0) == box.center().X


@pytest.mark.usefixtures("folded")
def test_card_rests_against_wrap_without_crossing_it() -> None:
    """La carte est plaquée contre la face avant du rabat, et le label contre la carte."""
    part, wrap = card(), base()
    assert pytest.approx(wrap.bounding_box().min.Y) == part.bounding_box().max.Y
    assert not part.intersect(wrap)
    paper = max(proposal_label().solids(), key=lambda s: s.volume)
    assert not paper.intersect(part)
    assert paper.distance_to(part) == pytest.approx(0, abs=1e-6)


@pytest.mark.parametrize("angle", [0, 90])
def test_card_follows_open_wrap(monkeypatch: pytest.MonkeyPatch, angle: float) -> None:
    """La carte suit le rabat ouvert, sans traverser le socle."""
    monkeypatch.setattr(v, "base_wrap_angle", angle)
    part = card()
    assert not part.intersect(base())
    assert part.distance_to(base()) < v.card_thickness
