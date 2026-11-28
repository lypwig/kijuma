"""La carte graduée, en papier fin, aux bouts arrondis, plaquée contre le rabat."""

from build123d import *

from . import utils as u
from . import values as v
from .base import wrap_fold, wrap_slot_drops


def card_centers_gap() -> float:
    """Retourne l'écart entre les centres des bouts : du rivet à la fente du bas."""
    return -min(wrap_slot_drops())


def card_outline() -> Face:
    """Construit le contour de la carte, debout, centré sur l'origine."""
    diameter = 2 * u.disc_radius
    with BuildSketch() as sketch:
        SlotOverall(card_centers_gap() + diameter, diameter, rotation=90)
    return sketch.sketch.face()


def card_location() -> Location:
    """
    Retourne la place de la carte sur l'assemblage.

    Elle est plaquée contre la face avant du rabat replié, et son bout du haut est centré
    sur le rivet : il épouse ainsi l'arrondi du disque des cadrans. Elle suit le rabat quand
    celui-ci est ouvert.
    """
    wrap_front = u.cover_offset + u.min_gap + v.cardboard_thickness
    folded = Location((0, -(wrap_front + v.paper_thickness), -card_centers_gap() / 2))
    return wrap_fold() * folded


def card() -> Part:
    """Construit la carte graduée en papier."""
    # Le plan XZ a sa normale vers -Y, vers l'avant : le papier est centré sur y = 0
    with BuildPart() as builder:
        with BuildSketch(Plane.XZ.offset(v.paper_thickness)):
            insert(card_outline())
        extrude(amount=-v.paper_thickness)
    part = builder.part
    part.label = v.card[0]
    part.color = Color(*v.card[1])
    part.locate(card_location())
    return part
