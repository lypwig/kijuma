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
    return part


def assembly(tab_angle: int = 20, dial_angle: float = 0) -> Compound:
    """Return the compound of the assembly."""
    base_part = base()
    dial_part = dial(tab_angle)
    screw_part = rivet()

    # Base : siège de la vis sur la face avant de la 1ère tôle (y = 0), axe Z vers -Y
    RigidJoint("screw_seat", base_part, Location((0, 0, 0), (90, 0, 0)))
    # Vis : repère sous la tête, et pivot du dial à une épaisseur de tôle sous la tête
    RigidJoint("seat", screw_part, Location((0, 0, 0)))
    RevoluteJoint("pivot", screw_part, axis=Axis((0, 0, -v.material_thickness), (0, 0, 1)))
    # Dial : repère sur sa face avant (y = -épaisseur), axe Z vers -Y
    RigidJoint("pivot", dial_part, Location((0, -v.material_thickness, 0), (90, 0, 0)))

    base_part.joints["screw_seat"].attach(screw_part.joints["seat"])
    screw_part.joints["pivot"].attach(dial_part.joints["pivot"], angle=dial_angle)

    return Compound(label="Assembly", children=[base_part, screw_part, dial_part])
