"""
Construit le modèle du socle du profil de mérite, qui reçoit les cadrans.

Les esquisses et pièces auxiliaires sont construites dans leur propre fonction,
puis ajoutées à base() : un constructeur imbriqué n'agit sur son parent que s'il est
créé dans la même fonction que lui.
"""

from math import asin, ceil, cos, degrees, floor, radians, sin, sqrt, tan
from typing import NamedTuple, cast

from build123d import *

from . import utils as u
from . import values as v

base_view_angle = len(v.dials) * v.dial_tab_step
MIN_BEND_ANGLE = 0.01  # angle minimal d'un pli, en °, car un pli de 0° est refusé


def front_cutter() -> Sketch:
    """Construit l'esquisse à retirer du panneau avant : moitié haute, bande et disque."""
    with BuildSketch() as sketch:
        align = (Align.CENTER, Align.MIN)
        Rectangle(v.base_size, v.base_size / 2, align=align)
        # Bande du bord droit, pour enfoncer le pli du volet dans le socle
        with Locations((v.base_size / 2 - u.cover_inset / 2 + 0.5, 0)):
            Rectangle(u.cover_inset + 1, v.base_size + 2)
        Circle(u.disc_radius, mode=Mode.SUBTRACT, align=None)
        with BuildSketch(Rotation(90, 0, 0)):
            Circle(u.disc_radius, u.base_slot_angle, align=None)
        Circle(u.slot_radii[1], mode=Mode.SUBTRACT)
    return sketch.sketch_local


def view_radii() -> tuple[float, float]:
    """Construit les rayons extérieur et intérieur de la fenêtre en arc de cercle."""
    outer = u.dial_radius + v.base_view_width - v.dial_tab_height
    return outer, outer - v.base_view_width


def window_bottom() -> tuple[float, float]:
    """Construit le point le plus bas de la fenêtre en arc de cercle, congé compris."""
    # Le congé du bout de la fenêtre est un cercle tangent à l'arc extérieur : son centre
    # est à (rayon - congé) du centre du cadran, un peu avant le bout de la fenêtre.
    ring = view_radii()[0] - v.fillet
    angle = radians(base_view_angle) - asin(v.fillet / ring)
    return -ring * cos(angle), -ring * sin(angle) - v.fillet


def left_strip_edge_y() -> float:
    """Construit la hauteur du bord de la languette de gauche."""
    # Le bord est à hauteur du bas de la fenêtre, tangent à son congé : pas de ressaut.
    return window_bottom()[1]


def left_strip_pos() -> float:
    """Construit l'abscisse du centre de la languette de gauche."""
    # Centrée sur la partie plate du bord, entre le congé du coin et celui de la fenêtre.
    return (-v.base_size / 2 + v.fillet + window_bottom()[0]) / 2


def support_gaps(edge: Edge, height: float) -> tuple[float, float]:
    """Construit le retrait des bouts du pli du support, pour ne garder que `height`."""
    # Le pli part du bas du bord, la hauteur est mesurée vers le haut
    start, end = edge.position_at(0).Y, edge.position_at(1).Y
    top = edge.length - height
    return (0, top) if start < end else (top, 0)


def support_angle() -> float:
    """Retourne l'angle du pli du support en radians, jamais nul (0° est refusé)."""
    return radians(max(v.base_support_angle, MIN_BEND_ANGLE))


def support_fold_length() -> float:
    """Retourne la longueur verticale du pli : la largeur de la patte, vue de biais."""
    return v.base_support_height / cos(radians(v.base_support_tilt))


def support_plane() -> Plane:
    """Retourne le plan moyen de la patte : x le long de la patte, y vertical."""
    thickness, radius = v.material_thickness, v.bend_radius
    angle = support_angle()
    # La patte s'éloigne du panneau dans la direction `along`, `outward` est sa normale
    # extérieure. Le centre du pliage est derrière la face arrière du panneau arrière.
    along = -cos(angle), sin(angle)
    outward = -sin(angle), -cos(angle)
    center = -v.base_size / 2, (len(v.dials) + 2) * thickness + radius
    # L'origine est à la fin du pli, sur le plan moyen de la patte : c'est de là que
    # est mesurée la longueur de la patte, ce qui reste valable de 0° à 180°.
    x = center[0] + (radius + thickness / 2) * outward[0]
    y = center[1] + (radius + thickness / 2) * outward[1]
    return Plane((x, y, 0), x_dir=(*along, 0), z_dir=(-outward[0], -outward[1], 0))


def trim_support(sheet: BuildSheet) -> None:
    """Taille la patte du support en parallélogramme au bout carré, aux coins arrondis."""
    # Posé sur son support, le socle est incliné de `tilt` vers l'arrière : le bas de la
    # patte est alors horizontal. Dans le modèle (qui ne pivote pas), il monte donc vers
    # l'arrière, de `tilt` mesuré dans le plan de la patte, quel que soit son angle de
    # pli. La patte est large de `width` entre le bas et le haut, la longueur du bas est
    # `length` le long de la patte, et le bout est perpendiculaire au bas et au haut. Le
    # côté du panneau, vertical, est donc plus long que `width`.
    width, length = v.base_support_height, v.base_support_length
    fold = support_fold_length()
    tilt = radians(v.base_support_tilt)
    slope = tan(tilt)  # montée par longueur de patte
    bottom = -v.base_size / 2
    # Coins du bout : le haut est à la distance perpendiculaire `width`
    far_bottom = length, bottom + length * slope
    far_top = far_bottom[0] - width * sin(tilt), far_bottom[1] + width * cos(tilt)
    with BuildSketch(mode=Mode.PRIVATE) as outline:
        Polygon((0, bottom), far_bottom, far_top, (0, bottom + fold), align=None)
        fillet(outline.vertices().sort_by(Axis.X)[-2:], v.fillet)
    with (
        BuildSketch(mode=Mode.PRIVATE) as flange_face,
        Locations((length / 2, bottom + fold / 2)),
    ):
        Rectangle(length, fold)
    # Le pli ne fait que la hauteur du côté du panneau : la patte est d'abord un
    # rectangle, que l'on rogne en bas et que l'on complète en haut pour en faire le
    # parallélogramme
    mid = u.to_sheet(support_plane())
    u.sketch_on(sheet, mid, flange_face.sketch - outline.sketch, Mode.SUBTRACT)
    u.sketch_on(sheet, mid, outline.sketch - flange_face.sketch)


def fold_support(sheet: BuildSheet) -> None:
    """Plie le bord gauche du panneau arrière, vu de face, vers l'arrière."""
    back_z = sheet.flats().sort_by(Face.area)[-1].center().Z
    target = -v.base_size / 2, 0, back_z
    edge = sheet.rims().filter_by(Axis.Y).sort_by_distance(target)[0]
    gaps = support_gaps(edge, support_fold_length())
    flange(
        edge,
        v.base_support_length,
        degrees(support_angle()),
        gaps=gaps,
        length_from=LengthFrom.TANGENT,
    )
    trim_support(sheet)


def cover_angle() -> float:
    """Retourne l'angle du pli du volet en degrés, jamais nul (0° est refusé)."""
    return max(v.base_cover_angle, MIN_BEND_ANGLE)


def rotation(axis: tuple[float, float], angle: float) -> Location:
    """Retourne la rotation de `angle` degrés autour de l'axe vertical par `axis`."""
    x, y = axis
    return Location((x, y, 0)) * Rotation(0, 0, angle) * Location((-x, -y, 0))


def cover_fold() -> Location:
    """Retourne le déplacement qui fait pivoter le volet, de replié à 180° à son angle."""
    # Le pli est vertical, à l'angle du bord droit du panneau avant, enfoncé dans le socle :
    # son centre est à `bend_radius` devant la face avant (y = 0)
    axis = v.base_size / 2 - u.cover_inset, -v.bend_radius
    return rotation(axis, 180 - cover_angle())


def bottom_gaps(edge: Edge, height: float) -> tuple[float, float]:
    """Construit le retrait des bouts d'un bord vertical, pour garder `height` du bas."""
    # Le pli part du bas du panneau, quels que soient les congés du bord
    low, high = sorted((edge.position_at(0).Y, edge.position_at(1).Y))
    gap_low = -v.base_size / 2 - low
    gap_high = high - (height - v.base_size / 2)
    flipped = edge.position_at(0).Y > edge.position_at(1).Y
    return (gap_high, gap_low) if flipped else (gap_low, gap_high)


def fold_cover(sheet: BuildSheet) -> None:
    """Plie le bord droit du panneau avant, vu de face, vers l'avant, à son angle."""
    target = v.base_size / 2 - u.cover_inset, 0, 0
    edge = sheet.rims().filter_by(Axis.Y).sort_by_distance(target)[0]
    gaps = bottom_gaps(edge, v.base_cover_height)
    # La longueur est mesurée depuis le bord du socle : le bout reste à la même place
    flange(edge, v.base_cover_length - u.cover_inset, cover_angle(), gaps=gaps)


def wrap_bend_angle() -> float:
    """Retourne l'angle de chacun des 2 plis du rabat en degrés, jamais nul."""
    # Le paramètre est l'angle du rabat entier : 180° replié, 0° à plat. Un pli de 0° est
    # refusé.
    return max(v.base_wrap_angle / 2, MIN_BEND_ANGLE)


def wrap_wall_length() -> float:
    """Retourne la longueur droite de la tranche du rabat, entre ses deux plis."""
    # Replié, le rabat va de la face avant du panneau arrière jusqu'à devant le volet : il
    # fait l'épaisseur du socle
    return (len(v.dials) + 2) * v.material_thickness + u.min_gap


def wrap_wall_end() -> tuple[float, float]:
    """Retourne la position (x, y) du bout de la tranche, sur son plan moyen."""
    thickness, radius = v.material_thickness, v.bend_radius
    # Le pli tourne autour d'un centre devant la face avant du panneau arrière
    angle = radians(wrap_bend_angle())
    center = v.base_size / 2, (len(v.dials) + 1) * thickness - radius
    reach = radius + thickness / 2
    start = center[0] + reach * sin(angle), center[1] + reach * cos(angle)
    length = wrap_wall_length()
    return start[0] + length * cos(angle), start[1] - length * sin(angle)


def wrap_tip() -> tuple[float, float]:
    """Retourne la position (x, y) du bout du rabat, sur son plan moyen."""
    thickness, radius = v.material_thickness, v.bend_radius
    angle = radians(wrap_bend_angle())
    reach = radius + thickness / 2
    # Le 2e pli tourne autour d'un centre du côté intérieur, et emporte le rabat de deux
    # fois l'angle d'un pli par rapport au panneau arrière
    end = wrap_wall_end()
    center = end[0] - reach * sin(angle), end[1] - reach * cos(angle)
    start = center[0] + reach * sin(2 * angle), center[1] + reach * cos(2 * angle)
    length = v.base_wrap_length
    return start[0] + length * cos(2 * angle), start[1] - length * sin(2 * angle)


def wrap_fold() -> Location:
    """Retourne le déplacement du rabat, de replié à son angle de pliure."""
    # Les deux plis sont verticaux. Le 2e pivote d'abord, autour de son centre, puis le
    # 1er emporte la tranche et le rabat autour de son propre centre.
    thickness, radius, half = v.material_thickness, v.bend_radius, v.base_size / 2
    delta = 90 - wrap_bend_angle()
    first = rotation((half, (len(v.dials) + 1) * thickness - radius), delta)
    # Replié, le 2e pli est contre l'extérieur du pli du volet, devant le rabat
    second = rotation((half, -(radius + thickness + u.min_gap)), delta)
    return first * second


def fold_wrap(sheet: BuildSheet) -> None:
    """Plie le bord droit du panneau arrière vers l'avant, puis sur la face avant."""
    back_z = sheet.flats().sort_by(Face.area)[-1].center().Z
    edge = sheet.rims().filter_by(Axis.Y).sort_by_distance((v.base_size / 2, 0, back_z))[0]
    angle = wrap_bend_angle()
    gaps = bottom_gaps(edge, v.base_wrap_height)
    flange(edge, wrap_wall_length(), -angle, gaps=gaps)
    # Le 2e pli est sur le bout de la tranche, de la même hauteur et du même angle
    x, y = wrap_wall_end()
    end = sheet.rims().filter_by(Axis.Y).sort_by_distance((x, 0, -y))[0]
    flange(end, v.base_wrap_length, -angle)
    # Les deux coins du bout du rabat sont arrondis
    x, y = wrap_tip()
    tip = sheet.rims().filter_by(Axis.Y).sort_by_distance((x, 0, -y))[0]
    fillet(tip.vertices(), v.fillet)


def shape_wrap(sheet: BuildSheet) -> None:
    """Ajoute au rabat le disque des cadrans, centré sur le rivet, et perce ses trous."""
    half, thickness = v.base_size / 2, v.material_thickness
    # Le plan moyen du rabat, replié contre la face avant du volet, puis déplié
    mid = Plane.XZ.offset(u.cover_offset + u.min_gap + thickness / 2)
    mid = u.to_sheet(Plane(wrap_fold() * mid.location))
    side_margin, bottom_margin = v.base_wrap_slot_margin
    # Fentes verticales à `side_margin` des deux côtés du rabat, tranche et bout, et à
    # `bottom_margin` de son bas
    sides = half - side_margin, half - v.base_wrap_length + side_margin
    middle = -half + bottom_margin + v.base_wrap_slot_v_length / 2
    drops = [-v.base_wrap_slot_drop - i * v.base_wrap_slot_step for i in range(2)]
    with BuildSketch(mode=Mode.PRIVATE) as disc:
        Circle(u.disc_radius)
    with BuildSketch(mode=Mode.PRIVATE) as holes:
        Circle(v.rivet_head_hole / 2)
        with Locations(*[(0, y) for y in drops]):
            SlotOverall(v.base_wrap_slot_h_length, v.base_wrap_slot_width)
        with Locations(*[(x, middle) for x in sides]):
            SlotOverall(v.base_wrap_slot_v_length, v.base_wrap_slot_width, rotation=90)
    u.sketch_on(sheet, mid, disc.sketch)
    u.sketch_on(sheet, mid, holes.sketch, Mode.SUBTRACT)


def shape_cover(sheet: BuildSheet) -> None:
    """Ajoute au volet le disque centré sur le rivet, denté et percé du trou du rivet."""
    radius = v.base_cover_disc_diam / 2
    # Le plan moyen du volet, replié à `bend_radius * 2` de la face avant du panneau avant
    # (y = 0), puis déplié
    mid = Plane.XZ.offset(u.cover_offset - v.material_thickness / 2)
    mid = u.to_sheet(Plane(cover_fold() * mid.location))
    # Le bord gauche du volet descend à 45° vers la droite, depuis le point le plus bas du
    # disque : on retire ce qui dépasse la droite x + z = -rayon
    reach = v.base_size
    below = (0, -radius), (reach, -radius - reach), (0, -radius - reach)
    with BuildSketch(mode=Mode.PRIVATE) as disc:
        Circle(radius)
    # Les dents ne touchent que le disque, hors du volet
    with BuildSketch(mode=Mode.PRIVATE) as holes:
        Polygon(*cover_teeth_outline(), align=None)
        Polygon(*below, align=None)
        Circle(v.rivet_diam / 2)
    u.sketch_on(sheet, mid, disc.sketch)
    u.sketch_on(sheet, mid, holes.sketch, Mode.SUBTRACT)
    # Congé de l'angle entre la pente et le bas du volet ; l'arc du disque reste vif
    corner = Vector(v.base_size / 2 - radius, -v.base_size / 2, 0)
    corner = cast("Vector", mid.from_local_coords(corner))
    fillet(sheet.vertices().sort_by_distance(corner)[:1], v.fillet)


def fold_sides(sheet: BuildSheet) -> None:
    """Plie les côtés du socle : support, volet de la face avant et rabat de la tranche."""
    fold_support(sheet)
    fold_cover(sheet)
    shape_cover(sheet)
    fold_wrap(sheet)
    shape_wrap(sheet)


def cover_teeth_span() -> tuple[float, float]:
    """Retourne les angles, en °, entre lesquels l'arc libre du disque est denté."""
    # L'arc libre du disque, sans congé à ses bouts, va du haut du volet (0°) jusqu'au
    # point le plus bas du disque, où part la pente (270°)
    return 0, 270


def cover_teeth_points() -> list[tuple[float, float]]:
    """Retourne les points (angle en °, profondeur) du zigzag des dents le long de l'arc."""
    step, depth = v.base_cover_teeth_step, v.base_cover_teeth_depth
    start, end = cover_teeth_span()
    # Dents au pas exact, sommets sur les multiples du pas, creux à mi-pas : ainsi le
    # motif ne dépend pas du diamètre. Seules les dents entières sont gardées, ce qui
    # laisse un petit espace lisse à chaque bout de l'arc.
    first, last = ceil(start / step), floor(end / step)
    return [(j * step / 2, depth * (j % 2)) for j in range(2 * first, 2 * last + 1)]


def cover_teeth_outline() -> list[tuple[float, float]]:
    """Retourne le contour de la matière à retirer de l'arc du disque, pour les dents."""
    radius = v.base_cover_disc_diam / 2
    points = cover_teeth_points()

    def polar(r: float, angle: float) -> tuple[float, float]:
        return r * cos(radians(angle)), r * sin(radians(angle))

    # Un seul contour : le zigzag des dents, puis le retour par l'extérieur du cercle,
    # pour retirer aussi l'arc
    teeth = [polar(radius - depth, angle) for angle, depth in points]
    outside = [polar(radius + 1, angle) for angle, _ in reversed(points)]
    return teeth + outside


def view_tip() -> Sketch:
    """Construit l'esquisse de la pointe de matière laissée par la fenêtre, à retirer."""
    # La fenêtre sort du bord gauche du socle en laissant une pointe de matière effilée.
    # On retire cette pointe jusqu'au bord de la languette de gauche, mais seulement
    # hors du cercle extérieur de la fenêtre : on ne touche pas au panneau côté cadran.
    half, outer = v.base_size / 2, view_radii()[0]
    top = -sqrt(outer**2 - half**2) + 1  # un peu au-dessus de la pointe
    bottom = left_strip_edge_y()
    with BuildSketch() as sketch:
        with Locations((-half / 2 - 0.5, (top + bottom) / 2)):
            Rectangle(half + 1, top - bottom)
        Circle(outer, mode=Mode.SUBTRACT)
        # Prolongement du bord jusqu'au point le plus bas du congé de la fenêtre
        left, right = -half - 1, window_bottom()[0]
        with Locations(((left + right) / 2, bottom + 0.5)):
            Rectangle(right - left, 1)
    return sketch.sketch_local


def view_window() -> Sketch:
    """Construit la fenêtre en arc de cercle, décalée vers l'extérieur du cadran."""
    outer, inner = view_radii()
    with BuildSketch() as sketch:
        with BuildSketch(Rotation(90, 0, -180)):
            Circle(outer, base_view_angle, None)
        Circle(inner, mode=Mode.SUBTRACT)
    return sketch.sketch_local


def front_corners(vertices: ShapeList[Vertex]) -> list[Vertex]:
    """Retourne les sommets du panneau avant à arrondir, sauf au bas de la fenêtre."""
    min_pos, max_pos = -v.base_size / 2 + 1, v.base_size
    corners = vertices.filter_by_position(Axis.Y, min_pos, max_pos)
    # Pas de congé au bas de la fenêtre, ni à droite du disque intérieur (début de la fente)
    # ni en haut du pli du volet (milieu du bord droit), où le pli commence à angle vif
    skipped = [
        p
        for angle in (u.base_slot_angle, 0)
        for p in u.polar_vertices(corners, angle, u.slot_radii)
    ]
    skipped += u.point_vertices(corners, [(v.base_size / 2 - u.cover_inset, 0)])
    return [p for p in corners if p not in skipped]


class Strip(NamedTuple):
    """Languette du socle : abscisse du centre, ordonnée du bord, échancrure et largeur."""

    x: float
    edge_y: float
    notch_height: float
    width: float


def strips() -> list[Strip]:
    """Construit les languettes du socle."""
    # À droite juste sous l'axe du cadran, à gauche sur le bord plat sous la pointe de la
    # fenêtre.
    drop = u.base_right_strip_drop
    return [
        Strip(u.base_right_strip_pos, -drop, drop, v.base_right_strip_width),
        Strip(left_strip_pos(), left_strip_edge_y(), 0, v.base_left_strip_width),
    ]


def strip_fit(edge: Edge, x: float, width: float) -> tuple[float, float]:
    """Construit le retrait des deux bouts de la pliure, pour la largeur et la position."""
    # La pliure ne garde que la largeur voulue, centrée en x sur le bord libre
    start, end = edge.position_at(0).X, edge.position_at(1).X
    low, high = (
        max(0, x - width / 2 - min(start, end)),
        max(0, max(start, end) - x - width / 2),
    )
    return (low, high) if start < end else (high, low)


def shape_strip_head(sheet: BuildSheet, x: float, wall_z: float, width: float) -> None:
    """Taille le bout de la languette en tête étroite, qui traverse le panneau arrière."""
    thickness = v.material_thickness
    head = width - 2 * v.base_strip_stop - 2 * v.base_strip_clearance
    # La base vient en butée sur la face avant du panneau arrière, la tête la traverse
    back_front = (len(v.dials) + 1) * thickness
    mid = Plane(
        (x, wall_z, -(back_front + thickness / 2)),
        x_dir=(1, 0, 0),
        z_dir=(0, 1, 0),
    )
    inner, outer = head / 2, width / 2 + 1
    # Dans le plan de la languette : x depuis son centre, y depuis la face du panneau
    with BuildSketch(mode=Mode.PRIVATE) as shoulders:
        for sign in (-1, 1):
            with Locations((sign * (inner + outer) / 2, thickness / 2)):
                Rectangle(outer - inner, 2 * thickness)
    u.sketch_on(sheet, mid, shoulders.sketch, Mode.SUBTRACT)


def base() -> Part:
    """Construit la pièce correspondant au socle."""
    thickness, radius = v.material_thickness, v.bend_radius
    # Longueur plane ajoutée entre les deux pliages, pour écarter les deux panneaux
    spacing = len(v.dials) * v.material_thickness - 2 * radius

    with BuildPart() as builder:
        with BuildSheet(Plane.XZ, thickness=thickness, bend_radius=radius) as sheet:
            with BuildSketch():
                Rectangle(v.base_size, v.base_size)
            bottom = sheet.rims().group_by(Axis.Y)[0]
            if spacing:  # deux pliages à 90° avec une paroi plane entre eux
                flange(bottom, angle=-90, length=spacing)
                bottom = sheet.rims().filter_by(Axis.X).sort_by(Axis.Z)[0]
                flange(bottom, angle=-90, length=v.base_size)

            with BuildSketch(mode=Mode.SUBTRACT):
                insert(front_cutter())

            fillet(front_corners(sheet.vertices()), v.fillet)

            with BuildSketch(mode=Mode.SUBTRACT):
                Circle(v.rivet_diam / 2)
            with Locations(Plane(sheet.flats().sort_by(Axis.Z)[0])):
                Circle(v.rivet_diam / 2, mode=Mode.SUBTRACT)

            # Fenêtre du panneau avant, pour voir le bout des languettes, avec ses congés
            with BuildSketch(mode=Mode.SUBTRACT):
                insert(view_window())
            end_angle = base_view_angle - 180
            fillet(u.polar_vertices(sheet.vertices(), end_angle, view_radii()), v.fillet)

            # Chanfrein horizontal de la pointe de la fenêtre au bord gauche, avec congés
            with BuildSketch(mode=Mode.SUBTRACT):
                insert(view_tip())
            tip_y = left_strip_edge_y()
            tip_corners = sheet.vertices().filter_by_position(
                Axis.Y,
                tip_y - v.tolerance,
                tip_y + v.tolerance,
            )
            fillet(
                tip_corners.filter_by_position(Axis.X, -v.base_size, -v.base_size / 2 + 1),
                v.fillet,
            )

            for x, edge_y, notch_height, width in strips():
                # Le panneau avant est échancré pour abaisser la bande sous son bord
                if notch_height:
                    notch_pos = x, edge_y + notch_height / 2
                    # Même largeur que l'entaille des cadrans, pour aligner les congés
                    half = u.notch_half(width)
                    with BuildSketch(mode=Mode.SUBTRACT), Locations(notch_pos):
                        Rectangle(2 * half, notch_height)
                    # Congés des coins du panneau qui bordent l'entrée de l'échancrure
                    mouth = [(x + s * half, edge_y + notch_height) for s in (-1, 1)]
                    fillet(u.point_vertices(sheet.vertices(), mouth), v.light_fillet)

                # Bande pliée vers l'arrière depuis le bord libre.
                # Sa base vient en butée contre le panneau arrière, sa tête traverse la
                # fenêtre de la tôle arrière, qui retient la base de la languette.
                edge = sheet.rims().filter_by(Axis.X).sort_by_distance((x, edge_y, 0))[0]
                # Elle se prolonge d'une épaisseur, pour traverser la fenêtre du panneau
                # arrière, sans que son bout soit dans le plan de la face arrière
                length = radius + spacing + thickness - u.min_gap
                flange(edge, length, -90, gaps=strip_fit(edge, x, width))

                back_z = sheet.flats().sort_by(Face.area)[-1].center().Z
                wall_z = edge_y + radius + thickness / 2
                shape_strip_head(sheet, x, wall_z, width)
                with Locations((x, wall_z, back_z)):
                    window = (
                        width - 2 * v.base_strip_stop,
                        thickness + 2 * v.base_strip_clearance,
                    )
                    Rectangle(*window, mode=Mode.SUBTRACT)

            fold_sides(sheet)
        thicken()

    part = builder.part
    part.label = v.base[0]
    part.color = Color(v.base[1])
    return part
