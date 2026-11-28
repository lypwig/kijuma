"""Crée l'assemblage du profile de mérite, contenant le socle et les cadrans."""

from build123d import *

from . import utils as u
from . import values as v
from .base import base
from .card import card
from .dial import dial
from .label import proposal_label


def rivet(length: float) -> Part:
    """Construit le rivet qui maintient les cadrans au socle."""
    head_diam, head_thickness = v.rivet_head
    center = Align.CENTER, Align.CENTER
    with BuildPart() as builder:
        head = Cylinder(head_diam / 2, head_thickness, align=(*center, Align.MIN))
        fillet(head.edges().group_by(Axis.Z)[-1].filter_by(GeomType.CIRCLE), v.light_fillet)
        Cylinder(v.rivet_diam / 2, length, align=(*center, Align.MAX))

    part = builder.part
    part.label = v.rivet[0]
    part.color = Color(v.rivet[1])
    return part


def assembly() -> Compound:
    """Construit l'assemblage."""
    base_part = base()
    screw_part = rivet(v.rivet_length)
    thickness = v.material_thickness

    # Socle : siège de la vis sur la face avant du volet, axe Z vers -Y
    RigidJoint("screw_seat", base_part, Location((0, -u.cover_offset, 0), (90, 0, 0)))
    # Rivet : repère sous la tête
    RigidJoint("seat", screw_part, Location((0, 0, 0)))

    dials = []
    for i, (label, color) in enumerate(v.dials):
        flap_extra = (len(v.dials) - 1 - i) * thickness
        dial_part = dial(i * v.dial_tab_step, i * v.dial_slot_step, flap_extra)
        dial_part.label = label
        dial_part.color = Color(*color)
        # Rivet : pivot du cadran, sous la tête : volet, panneau avant, un cadran par rang
        depth = u.cover_offset + (i + 1) * thickness
        axis = Axis((0, 0, -depth), (0, 0, 1))
        RevoluteJoint(f"pivot {i + 1}", screw_part, axis=axis)
        # Cadran : repère sur sa face avant (y = -épaisseur), axe Z vers -Y
        RigidJoint("pivot", dial_part, Location((0, -thickness, 0), (90, 0, 0)))
        dials.append(dial_part)

    # Les joints sont tous créés avant d'attacher les pièces, qui déplace le rivet
    base_part.joints["screw_seat"].attach(screw_part.joints["seat"])
    for i, dial_part in enumerate(reversed(dials)):
        screw_part.joints[f"pivot {i + 1}"].attach(dial_part.joints["pivot"])

    dials_group = Compound(label=v.dials_label, children=dials)
    return Compound(
        label=v.assembly_label,
        children=[base_part, screw_part, dials_group, card(), proposal_label()],
    )
