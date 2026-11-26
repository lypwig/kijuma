"""Create an assembly containing the base and the dials."""

from build123d import *

from . import values as v
from .base import base
from .dial import dial


def rivet(length: float = 8) -> Part:
    """Build the rivet used to maintain the dials in the base."""
    with BuildPart() as builder:
        align = (Align.CENTER, Align.CENTER, Align.MIN)
        Cylinder(v.rivet_head[0] / 2, v.rivet_head[1], align=align)
        Cylinder(v.rivet_diam / 2, length, align=(Align.CENTER, Align.CENTER, Align.MAX))

    part = builder.part
    part.label = "Screw"
    part.color = Color(0.3, 0.3, 0.3)
    return part


def assembly() -> Compound:
    """Return the compound of the assembly, with the dials configured in the values."""
    base_part = base()
    screw_part = rivet(v.sheet_gap + 2 * v.material_thickness)
    thickness = v.material_thickness

    # Base : siège de la vis sur la face avant de la 1ère tôle (y = 0), axe Z vers -Y
    RigidJoint("screw_seat", base_part, Location((0, 0, 0), (90, 0, 0)))
    # Vis : repère sous la tête
    RigidJoint("seat", screw_part, Location((0, 0, 0)))

    dials = []
    for i, (label, color) in enumerate(v.dials):
        dial_part = dial(i * v.tab_step)
        dial_part.label = label
        dial_part.color = Color(*color)
        # Vis : pivot du dial, une épaisseur de tôle plus un dial par rang sous la tête
        axis = Axis((0, 0, -(i + 1) * thickness), (0, 0, 1))
        RevoluteJoint(f"pivot {i + 1}", screw_part, axis=axis)
        # Dial : repère sur sa face avant (y = -épaisseur), axe Z vers -Y
        RigidJoint("pivot", dial_part, Location((0, -thickness, 0), (90, 0, 0)))
        dials.append(dial_part)

    # Les joints sont tous créés avant d'attacher les pièces, qui déplace la vis
    base_part.joints["screw_seat"].attach(screw_part.joints["seat"])
    for i, dial_part in enumerate(reversed(dials)):
        screw_part.joints[f"pivot {i + 1}"].attach(dial_part.joints["pivot"])

    return Compound(label="Assembly", children=[base_part, screw_part, *dials])
