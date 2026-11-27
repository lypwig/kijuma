"""Construit le cadran servant à afficher le profil de mérite."""

from math import cos, floor, hypot, radians, sin, tan

from build123d import *

from . import utils as u
from . import values as v


def flap_angles(slot_extra: float) -> tuple[float, float]:
    """Retourne les angles du début et de la fin de la fenêtre de la languette."""
    slot_length = 180 + slot_extra + v.dial_slot_step
    return slot_length - v.dial_slot_step, slot_length


def flap_hinge(start: float, end: float) -> tuple[float, float, float]:
    """Retourne l'angle médian, le demi-angle et le rayon de la corde de la languette."""
    half = radians((end - start) / 2)
    return radians((start + end) / 2), half, u.disc_radius * cos(half)


def flap_window(start: float, end: float) -> Sketch:
    """Construit le bout de la fente, dont le bord extérieur est une corde et non un arc."""
    outer, inner = u.slot_radii
    points = [
        (r * cos(radians(a)), r * sin(radians(a)))
        for r, a in ((inner, start), (outer, start), (outer, end), (inner, end))
    ]
    with BuildSketch() as sketch:
        Polygon(*points, align=None)
    return sketch.sketch_local


def fold_flap(sheet: BuildSheet, edge: Edge | ShapeList[Edge], depth: float) -> None:
    """Plie la languette vers l'avant depuis le bord, puis rabat son bout vers le centre."""
    flange(edge, depth, -90, gaps=v.dial_flap_gap, length_from=LengthFrom.INNER_SHARP)
    tip = sheet.rims().filter_by(GeomType.LINE).sort_by(Axis.Z)[0]
    flange(tip, v.dial_flap_fold, 90)


def flap_span(depth: float) -> tuple[float, float]:
    """Retourne la longueur développée de la languette et son retrait une fois repliée."""
    # Mesuré sur une tôle d'essai pliée comme le cadran : le dépliage tient compte des
    # rayons de pliage, et le retrait est la distance entre la charnière et le bout.
    size = 10
    thickness, radius = v.material_thickness, v.bend_radius
    with BuildSheet(Plane.XZ, thickness=thickness, bend_radius=radius) as sheet:
        with BuildSketch():
            Rectangle(size, size)
        fold_flap(sheet, sheet.rims().group_by(Axis.Y)[0], depth)
        reach = -size / 2 - min(p.Y for p in sheet.vertices())
        flat, _ = unfold()
    box = flat.bounding_box()
    return box.max.Y - box.min.Y - size, reach


def flap_pocket(flap_start: float, end: float, depth: float) -> Sketch:
    """Construit l'empreinte de la languette dépliée, à retirer du disque central."""
    # Dépliée, la languette repartirait de sa charnière vers le centre du cadran, sur le
    # disque : sans ce vide, la tôle se superposerait à elle-même. Le bout rabattu est
    # taillé selon les côtés radiaux du secteur, l'empreinte suit donc le même trapèze.
    mid, half, hinge = flap_hinge(flap_start, end)
    slope = sin(half) / cos(half)  # demi-largeur du secteur par unité de rayon
    width = (
        u.disc_radius * sin(half) - v.dial_flap_gap
    )  # la pliure est retirée à chaque bout
    length, reach = flap_span(depth)
    # Le bout rabattu rétrécit dès que le secteur devient plus étroit que la languette
    bend = max(0, length - reach + v.dial_flap_gap / slope)
    tip = min(width, (hinge - reach) * slope)  # demi-largeur au bout de la languette
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


def flap_teeth_points(start: float, end: float, depth: float) -> list[tuple[float, float]]:
    """Retourne les points (abscisse, profondeur) du zigzag des dents du bout rabattu."""
    # Le bout rabattu est un segment perpendiculaire à la direction médiane du secteur,
    # à la distance `charnière - retrait` du centre, aussi large que le secteur à ce rayon
    _, half, hinge = flap_hinge(start, end)
    _, reach = flap_span(depth)
    width = 2 * (hinge - reach) * tan(half)
    step, tooth = v.dial_flap_teeth_step, v.dial_flap_teeth_depth
    # Dents entières, centrées : il reste au moins un demi-pas lisse à chaque bout
    count = max(0, floor(width / step) - 1)
    points = []
    for i in range(count):
        points += [((i - count / 2) * step, 0), ((i + 0.5 - count / 2) * step, tooth)]
    return [*points, ((count / 2) * step, 0)] if count else []


def flap_teeth(start: float, end: float, depth: float) -> Part | None:
    """Construit la matière à retirer du bout de la languette pour y faire des dents."""
    points = flap_teeth_points(start, end, depth)
    if not points:
        return None
    mid, _, hinge = flap_hinge(start, end)
    radius = hinge - flap_span(depth)[1]  # distance du bout de la languette au centre

    # Les dents sont creusées vers la charnière, le zigzag est refermé côté extérieur
    def place(offset: float, across: float) -> tuple[float, float]:
        along = radius + offset
        return (
            along * cos(mid) - across * sin(mid),
            along * sin(mid) + across * cos(mid),
        )

    zigzag = [place(tooth, across) for across, tooth in points]
    outline = zigzag + [place(-1, across) for across, _ in reversed(points)]
    # Le bout rabattu est la tôle la plus éloignée du cadran : on ne coupe que là
    thickness = v.material_thickness
    top = depth + thickness + v.bend_radius - 0.5
    with BuildPart() as builder:
        with BuildSketch(Plane.XZ.offset(top)):
            Polygon(*outline, align=None)
        extrude(amount=thickness + 1)
    return builder.part


def flap_clip(start: float, end: float) -> Part:
    """Construit le volume à retirer sous le cadran, hors du secteur de la languette."""
    # Les côtés du secteur sont radiaux : les bouts rabattus de deux languettes voisines,
    # qui convergent vers le centre, se touchent ainsi sur toute leur longueur.
    size = v.dial_diam
    points = [(0, 0)] + [
        (size * cos(radians(a)), size * sin(radians(a)))
        for a in (start, (start + end) / 2, end)
    ]
    with BuildPart() as builder:
        # Sous la tôle du cadran (de 0 à -épaisseur), là où il n'y a que la languette
        with Locations((0, -v.material_thickness - size / 2, 0)):
            Box(2 * size, size, 2 * size)
        with BuildSketch(Plane.XZ):
            Polygon(*points, align=None)
        extrude(amount=size * 2, mode=Mode.SUBTRACT)
    return builder.part


def rounded_corners(
    vertices: ShapeList[Vertex],
    tab_angle: float,
    slot_ends: tuple[float, ...],
) -> list[Vertex]:
    """Retourne les sommets à arrondir : disque central et bout de la languette."""
    # Pas de congés sur les bouts de la fente
    slot = [p for a in slot_ends for p in u.polar_vertices(vertices, a, u.slot_radii)]
    center = [p for p in vertices if hypot(p.X, p.Y) < u.disc_radius + 1]
    tab_radii = u.dial_radius, u.dial_radius - v.dial_tab_height
    tab_end = u.polar_vertices(vertices, tab_angle - 180, tab_radii)
    return [p for p in center if p not in slot] + tab_end


def notch_corners() -> list[tuple[float, float]]:
    """Retourne les coins du bord plat qui bordent l'entrée des entailles."""
    half = u.notch_half(v.base_right_strip_width)
    return [
        (sign * u.base_right_strip_pos + side * half, 0)
        for sign in (-1, 1)
        for side in (-1, 1)
    ]


def dial_sheet(
    tab_angle: int,
    slot_extra: float = 0,
    flap_extra: float = 0,
) -> tuple[Part, BuildSheet]:
    """
    Construit la tôle du cadran, côté +Y et avant le taillage du bout de la languette.

    Retourne la pièce épaissie et la tôle de référence, que l'on peut déplier.
    """
    flap_start, slot_length = flap_angles(slot_extra)
    depth = v.dial_flap_depth + flap_extra
    thickness, radius = v.material_thickness, v.bend_radius
    with BuildPart() as builder:
        with BuildSheet(Plane.XZ, thickness=thickness, bend_radius=radius) as sheet:
            with BuildSketch() as sketch:
                Circle(u.disc_radius)
                Circle(u.dial_radius - v.dial_tab_height, -180, None)
                Circle(u.dial_radius, -180 + tab_angle, None)

                with BuildSketch(Rotation(90, 0, 0), mode=Mode.SUBTRACT):
                    Circle(u.disc_radius, flap_start, None)
                    Circle(u.slot_radii[1], mode=Mode.SUBTRACT)
                with BuildSketch(mode=Mode.SUBTRACT):
                    insert(flap_window(flap_start, slot_length))

                slot_ends = 0, flap_start, slot_length
                fillet(rounded_corners(sketch.vertices(), tab_angle, slot_ends), v.fillet)
                Circle(v.rivet_diam / 2, mode=Mode.SUBTRACT)

                # Vide du disque central où la languette se déplierait, sans congés
                with BuildSketch(mode=Mode.SUBTRACT):
                    insert(flap_pocket(flap_start, slot_length, depth))

                # Entailles aux deux bouts du bord plat, pour dégager la languette du socle
                with Locations((u.base_right_strip_pos, 0), (-u.base_right_strip_pos, 0)):
                    Rectangle(
                        2 * u.notch_half(v.base_right_strip_width),
                        u.base_right_strip_drop,
                        align=(Align.CENTER, Align.MAX),
                        mode=Mode.SUBTRACT,
                    )
                fillet(u.point_vertices(sketch.vertices(), notch_corners()), v.light_fillet)

                with Locations((u.dial_radius - v.dial_stop_loc, 0)):
                    SlotOverall(*v.dial_stop_size)

            # Languette pliée à 90° vers l'avant, sur la corde qui ferme le bout de la fente
            mid, _, hinge = flap_hinge(flap_start, slot_length)
            edge = (
                sheet.rims()
                .filter_by(GeomType.LINE)
                .sort_by_distance((hinge * cos(mid), hinge * sin(mid), 0))[0]
            )
            fold_flap(sheet, edge, depth)
        thicken()
    return builder.part, sheet


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
    flap_start, slot_length = flap_angles(slot_extra)
    sheet_part, _ = dial_sheet(tab_angle, slot_extra, flap_extra)

    # La tôle est construite côté +Y : on la retourne pour que la languette soit à l'avant
    # Le bout rabattu est ensuite taillé en trapèze, selon les côtés radiaux du secteur
    part = Part(sheet_part.mirror(Plane.XZ) - flap_clip(flap_start, slot_length))
    teeth = flap_teeth(flap_start, slot_length, v.dial_flap_depth + flap_extra)
    if teeth is not None:
        part = Part(part - teeth)
    part.label = "Dial"
    part.color = Color(0, 0.5, 0.5)
    return part
