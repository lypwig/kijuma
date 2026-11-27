"""Construit le cadran servant à afficher le profil de mérite."""

from math import cos, hypot, radians, sin

from build123d import *

from . import utils as u
from . import values as v


def flap_window(start: float, end: float) -> Sketch:
    """Construit le bout de la fente, dont le bord extérieur est une corde et non un arc."""
    inner, outer = v.dial_disc_diam / 2 - v.dial_slot_width, v.dial_disc_diam / 2
    points = [
        (r * cos(radians(a)), r * sin(radians(a)))
        for r, a in ((inner, start), (outer, start), (outer, end), (inner, end))
    ]
    with BuildSketch() as sketch:
        Polygon(*points, align=None)
    return sketch.sketch_local


def flap_span(depth: float) -> tuple[float, float]:
    """Retourne la longueur développée de la languette et son retrait une fois repliée."""
    # Mesuré sur une tôle d'essai pliée comme le cadran : le dépliage tient compte des
    # rayons de pliage, et le retrait est la distance entre la charnière et le bout.
    size = 10
    with BuildSheet(
        Plane.XZ,
        thickness=v.material_thickness,
        bend_radius=v.bend_radius,
    ) as sheet:
        with BuildSketch():
            Rectangle(size, size)
        flange(
            sheet.rims().group_by(Axis.Y)[0],
            depth,
            -90,
            gaps=0,
            length_from=LengthFrom.INNER_SHARP,
        )
        flange(
            sheet.rims().filter_by(GeomType.LINE).sort_by(Axis.Z)[0],
            v.dial_flap_fold,
            90,
        )
        reach = -size / 2 - min(p.Y for p in sheet.vertices())
        flat, _ = unfold()
    box = flat.bounding_box()
    return box.max.Y - box.min.Y - size, reach


def flap_pocket(flap_start: float, end: float, depth: float) -> Sketch:
    """Construit l'empreinte de la languette dépliée, à retirer du disque central."""
    # Dépliée, la languette repartirait de sa charnière vers le centre du cadran, sur le
    # disque : sans ce vide, la tôle se superposerait à elle-même. Le bout rabattu est
    # taillé selon les côtés radiaux du secteur, l'empreinte suit donc le même trapèze.
    half = radians((end - flap_start) / 2)
    mid = radians((flap_start + end) / 2)
    outer = v.dial_disc_diam / 2
    hinge, width = outer * cos(half), outer * sin(half)
    length, reach = flap_span(depth)
    bend = length - reach  # distance de la charnière où le bout commence à rétrécir
    tip = (hinge - reach) * sin(half) / cos(half)  # demi-largeur au bout de la languette
    outline = [
        (0, width),
        (bend, width),
        (length, tip),
        (length, -tip),
        (bend, -width),
        (0, -width),
    ]
    points = [
        (
            (hinge - s) * cos(mid) - h * sin(mid),
            (hinge - s) * sin(mid) + h * cos(mid),
        )
        for s, h in outline
    ]
    with BuildSketch() as sketch:
        Polygon(*points, align=None)
    return sketch.sketch_local


def flap_clip(start: float, end: float) -> Part:
    """Construit le volume à retirer sous le cadran, hors du secteur de la languette."""
    # Les côtés du secteur sont radiaux : les bouts rabattus de deux languettes voisines,
    # qui convergent vers le centre, se touchent ainsi sur toute leur longueur.
    reach = v.dial_diam
    points = [(0, 0)] + [
        (reach * cos(radians(a)), reach * sin(radians(a)))
        for a in (start, (start + end) / 2, end)
    ]
    with BuildPart() as builder:
        # Sous la tôle du cadran (de 0 à -épaisseur), là où il n'y a que la languette
        with Locations((0, -v.material_thickness - reach / 2, 0)):
            Box(2 * reach, reach, 2 * reach)
        with BuildSketch(Plane.XZ):
            Polygon(*points, align=None)
        extrude(amount=reach * 2, mode=Mode.SUBTRACT)
    return builder.part


def dial(tab_angle: int, slot_extra: float = 0, flap_extra: float = 0) -> Part:
    """
    Construit le cadran configuré pour l'angle de languette donné.

    La fente en arc de cercle démarre toujours à 0°, comme la fenêtre du panneau avant,
    et son extrémité est prolongée de `slot_extra` degrés. Une languette est pliée vers
    l'avant au bout de la fente : sa place est prise sur la fente, d'où l'allongement.
    Son bout est lui-même replié vers le centre du cadran ; `flap_extra` allonge la
    languette pour compenser l'épaisseur des cadrans placés devant, de sorte que ce
    second pli soit au même niveau pour tous les cadrans.
    """
    slot_length = 180 + slot_extra + v.dial_slot_step
    flap_start = slot_length - v.dial_slot_step
    thickness, radius = v.material_thickness, v.bend_radius
    with BuildPart() as builder:
        with BuildSheet(Plane.XZ, thickness=thickness, bend_radius=radius) as sheet:
            with BuildSketch() as sketch:
                Circle(v.dial_disc_diam / 2)
                Circle(v.dial_diam / 2 - v.dial_tab_height, -180, None)
                Circle(v.dial_diam / 2, -180 + tab_angle, None)

                with BuildSketch(Rotation(90, 0, 0), mode=Mode.SUBTRACT):
                    Circle(v.dial_disc_diam / 2, flap_start, None)
                    Circle(v.dial_disc_diam / 2 - v.dial_slot_width, mode=Mode.SUBTRACT)
                with BuildSketch(mode=Mode.SUBTRACT):
                    insert(flap_window(flap_start, slot_length))

                # Congés sur le disque central et le bout de la languette, pas sur la fente
                slot_radii = v.dial_disc_diam / 2, v.dial_disc_diam / 2 - v.dial_slot_width
                slot_ends = [0, flap_start, slot_length]
                slot = [
                    p
                    for a in slot_ends
                    for p in u.polar_vertices(sketch.vertices(), a, slot_radii)
                ]
                center = [
                    p
                    for p in sketch.vertices()
                    if hypot(p.X, p.Y) < v.dial_disc_diam / 2 + 1
                ]
                tab_radii = v.dial_diam / 2, v.dial_diam / 2 - v.dial_tab_height
                tab_end = u.polar_vertices(sketch.vertices(), tab_angle - 180, tab_radii)
                fillet([p for p in center if p not in slot] + tab_end, v.fillet)
                Circle(v.rivet_diam / 2, mode=Mode.SUBTRACT)

                # Vide du disque central où la languette se déplierait, sans congés
                depth = v.dial_flap_depth + flap_extra
                with BuildSketch(mode=Mode.SUBTRACT):
                    insert(flap_pocket(flap_start, slot_length, depth))

                # Entailles aux deux bouts du bord plat, pour dégager la languette du socle
                half = v.base_right_strip_width / 2 + v.dial_notch_size
                with Locations((u.base_right_strip_pos, 0), (-u.base_right_strip_pos, 0)):
                    align = (Align.CENTER, Align.MAX)
                    Rectangle(
                        2 * half,
                        u.base_right_strip_drop,
                        align=align,
                        mode=Mode.SUBTRACT,
                    )
                # Congés des coins du bord plat qui bordent l'entrée des entailles
                notch_corners = [
                    (sign * u.base_right_strip_pos + side * half, 0)
                    for sign in (-1, 1)
                    for side in (-1, 1)
                ]
                fillet(u.point_vertices(sketch.vertices(), notch_corners), v.light_fillet)

                with Locations((v.dial_diam / 2 - v.dial_stop_loc, 0)):
                    SlotOverall(*v.dial_stop_size)

            # Languette pliée à 90° vers l'avant, sur la corde qui ferme le bout de la fente
            mid = radians(flap_start + v.dial_slot_step / 2)
            chord = v.dial_disc_diam / 2 * cos(radians(v.dial_slot_step / 2))
            edge = (
                sheet.rims()
                .filter_by(GeomType.LINE)
                .sort_by_distance((chord * cos(mid), chord * sin(mid), 0))[0]
            )
            flange(
                edge,
                v.dial_flap_depth + flap_extra,
                -90,
                gaps=0,
                length_from=LengthFrom.INNER_SHARP,
            )
            # Second pli : le bout de la languette est rabattu vers le centre du cadran
            tip = sheet.rims().filter_by(GeomType.LINE).sort_by(Axis.Z)[0]
            flange(tip, v.dial_flap_fold, 90)
        thicken()

    # La tôle est construite côté +Y : on la retourne pour que la languette soit à l'avant
    # Le bout rabattu est ensuite taillé en trapèze, selon les côtés radiaux du secteur
    part = Part(builder.part.mirror(Plane.XZ) - flap_clip(flap_start, slot_length))
    part.label = "Dial"
    part.color = Color(0, 0.5, 0.5)
    return part
