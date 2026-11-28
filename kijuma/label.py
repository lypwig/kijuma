"""Le label de la proposition, en papier fin, tenu par les fentes verticales du rabat."""

from build123d import *

from . import utils as u
from . import values as v
from .base import wrap_fold


def label_size() -> tuple[float, float]:
    """Retourne la largeur du label (celle du rabat) et sa hauteur (celle des fentes)."""
    return v.base_wrap_length, v.base_wrap_slot_v_length


def label_outline() -> Face:
    """Construit le contour du label, centré sur l'origine."""
    width, height = label_size()
    with BuildSketch() as sketch:
        Rectangle(width, height)
        fillet(sketch.vertices(), v.fillet)
    return sketch.sketch.face()


def label_text() -> ShapeList[Wire]:
    """Construit les contours du texte du label, centré sur l'origine."""
    with BuildSketch() as sketch:
        Text(v.proposal_text_content, v.proposal_font_size, font=v.proposal_font)
    return sketch.sketch.wires()


def label_location() -> Location:
    """
    Retourne la place du label sur l'assemblage.

    Il est plaqué contre la face avant du rabat replié, et centré sur l'espace entre les
    fentes verticales, c'est-à-dire sur le rabat en largeur, et sur les fentes en hauteur.
    Il suit le rabat quand celui-ci est ouvert.
    """
    width, height = label_size()
    _, bottom_margin = v.base_wrap_slot_margin
    # La carte graduée est entre le rabat et le label
    wrap_front = u.cover_offset + u.min_gap + v.cardboard_thickness + v.paper_thickness
    folded = Location(
        (
            v.base_size / 2 - width / 2,
            -(wrap_front + v.paper_thickness / 2),
            -v.base_size / 2 + bottom_margin + height / 2,
        ),
    )
    return wrap_fold() * folded


def proposal() -> Compound:
    """Construit le label : le papier et son texte sur la face avant."""
    # Le plan XZ a sa normale vers -Y, vers l'avant : le papier est centré sur y = 0
    with BuildPart() as paper_builder:
        with BuildSketch(Plane.XZ.offset(v.paper_thickness * 2)):
            insert(label_outline())
        extrude(amount=-v.paper_thickness)
    paper = paper_builder.part
    paper.label = v.proposal_sheet[0]
    paper.color = Color(*v.proposal_sheet[1])

    # Le texte est lu depuis l'avant
    with BuildPart() as text_builder:
        with BuildSketch(Plane.XZ.offset(v.paper_thickness * 2)):
            Text(v.proposal_text_content, v.proposal_font_size, font=v.proposal_font)
        extrude(amount=v.paper_thickness / 10)
    text = text_builder.part
    text.label = v.proposal_text[0]
    text.color = Color(*v.proposal_text[1])

    group = Compound(label=v.proposal_group_label, children=[paper, text])
    group.locate(label_location())
    return group
