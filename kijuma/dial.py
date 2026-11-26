"""Construit le cadran servant à afficher le profil de mérite."""

from math import hypot

from build123d import *

from . import values as v
from .utils import polar_vertices


def dial(tab_angle: int, slot_shift: float = 0) -> Part:
    """
    Construit le cadran configuré pour l'angle de languette donné.

    La fente en arc de cercle est décalée de `slot_shift` degrés.
    """
    with BuildPart() as builder:
        with BuildSketch(Plane.XZ) as sketch:
            Circle(v.disc_diam / 2)
            Circle(v.dial_diam / 2 - v.dial_tab_height, -180, None)
            Circle(v.dial_diam / 2, -180 + tab_angle, None)

            with BuildSketch(Rotation(90, 0, slot_shift), mode=Mode.SUBTRACT):
                Circle(v.disc_diam / 2, v.dial_slot_length, None)
                Circle(v.disc_diam / 2 - v.dial_slot_width, mode=Mode.SUBTRACT)

            # Congés sur le disque central et le bout de la languette, pas sur la fente
            slot_radii = v.disc_diam / 2, v.disc_diam / 2 - v.dial_slot_width
            slot_ends = [slot_shift, slot_shift + v.dial_slot_length]
            slot = [
                p
                for a in slot_ends
                for p in polar_vertices(sketch.vertices(), a, slot_radii)
            ]
            center = [p for p in sketch.vertices() if hypot(p.X, p.Y) < v.disc_diam / 2 + 1]
            tab_radii = v.dial_diam / 2, v.dial_diam / 2 - v.dial_tab_height
            tab_end = polar_vertices(sketch.vertices(), tab_angle - 180, tab_radii)
            fillet([p for p in center if p not in slot] + tab_end, v.fillet)
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
