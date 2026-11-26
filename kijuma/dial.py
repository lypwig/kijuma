"""Construit le cadran servant à afficher le profil de mérite."""

from math import hypot

from build123d import *

from . import values as v
from .utils import polar_vertices


def dial(tab_angle: int) -> Part:
    """Retourne le cadran configuré pour l'angle de languette donné."""
    with BuildPart() as builder:
        with BuildSketch(Plane.XZ) as sketch:
            Circle(v.disc_diam / 2)
            Circle(v.dial_diam / 2 - v.dial_tab_height, -180, None)
            Circle(v.dial_diam / 2, -180 + tab_angle, None)

            with BuildSketch(Rotation(90, 0, v.dial_slot_start), mode=Mode.SUBTRACT):
                Circle(v.disc_diam / 2, v.dial_slot_length, None)
                Circle(v.disc_diam / 2 - v.dial_slot_width, mode=Mode.SUBTRACT)

            # Congés sur le disque central, la fente et le bout de la languette
            center = [p for p in sketch.vertices() if hypot(p.X, p.Y) < v.disc_diam / 2 + 1]
            radii = v.dial_diam / 2, v.dial_diam / 2 - v.dial_tab_height
            tab_end = polar_vertices(sketch.vertices(), tab_angle - 180, radii)
            fillet(center + tab_end, v.fillet)
            Circle(v.rivet_diam / 2, mode=Mode.SUBTRACT)

            # Entailles aux deux bouts du bord plat, pour dégager la languette du socle
            with Locations((v.base_strip_pos, 0), (-v.base_strip_pos, 0)):
                align = (Align.CENTER, Align.MAX)
                Rectangle(*v.dial_notch_size, align=align, mode=Mode.SUBTRACT)

            with Locations(v.dial_stop_loc):
                SlotOverall(*v.dial_stop_size)

        extrude(amount=v.material_thickness)

    part = builder.part
    part.label = "Dial"
    part.color = Color(0, 0.5, 0.5)
    return part
