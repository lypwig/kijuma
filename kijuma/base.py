"""
Construit le modèle du socle du profil de mérite, qui reçoit les cadrans.

Les esquisses et pièces auxiliaires sont construites dans leur propre fonction,
puis ajoutées à base() : un constructeur imbriqué n'agit sur son parent que s'il est
créé dans la même fonction que lui.
"""

from math import asin, ceil, cos, degrees, floor, radians, sin, sqrt, tan
from typing import NamedTuple

from build123d import *
from build123d.topology import Shape

from . import utils as u
from . import values as v

base_view_angle = len(v.dials) * v.dial_tab_step
MIN_BEND_ANGLE = 0.01  # angle minimal d'un pli, en °, car un pli de 0° est refusé


def front_cutter() -> Sketch:
    """Construit l'esquisse à retirer du panneau avant : moitié haute, disque et fente."""
    with BuildSketch() as sketch:
        align = (Align.CENTER, Align.MIN)
        Rectangle(v.base_size, v.base_size / 2, align=align)
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


def support_trim() -> Part:
    """Construit la matière à retirer de la patte pour lui donner son contour final."""
    # Posé sur son support, le socle est incliné de `tilt` vers l'arrière : le bas de la
    # patte est alors horizontal. Dans le modèle (qui ne pivote pas), il monte donc vers
    # l'arrière, de `tilt` mesuré dans le plan de la patte, quel que soit son angle de
    # pli. La patte est large de `width` entre le bas et le haut, la longueur du bas est
    # `length` le long de la patte, et le bout est perpendiculaire au bas et au haut. Le
    # côté du panneau, vertical, est donc plus long que `width`.
    width, length = v.base_support_height, v.base_support_length
    fold = support_fold_length()
    thickness, radius = v.material_thickness, v.bend_radius
    tilt = radians(v.base_support_tilt)
    slope = tan(tilt)  # montée par longueur de patte
    bottom = -v.base_size / 2
    # Coins du bout : le haut est à la distance perpendiculaire `width`
    far_bottom = length, bottom + length * slope
    far_top = far_bottom[0] - width * sin(tilt), far_bottom[1] + width * cos(tilt)
    # Le contour et la plaque débordent derrière la fin du pli, pour couper tout le pli
    start = -(radius + thickness) - 1
    profile = [
        (start - 1, bottom + (start - 1) * slope),
        far_bottom,
        far_top,
        (start - 1, bottom + fold + (start - 1) * slope),
    ]
    plate_end = length + 5
    plate_top = bottom + fold + length * slope + 10
    plate_center = (start + plate_end) / 2, (bottom - 10 + plate_top) / 2
    # Épais de part et d'autre de la patte ; le panneau arrière lui-même est préservé
    plane = support_plane().offset(-3 * thickness)
    half, back_y = v.base_size / 2, (len(v.dials) + 2) * thickness
    with BuildPart() as builder:
        with BuildSketch(plane), Locations(plate_center):
            Rectangle(plate_end - start, plate_top - bottom + 10)
        extrude(amount=6 * thickness)
        with BuildSketch(plane) as outline:
            Polygon(*profile, align=None)
            fillet(outline.vertices().sort_by(Axis.X)[-2:], v.fillet)
        extrude(amount=6 * thickness, mode=Mode.SUBTRACT)
        with Locations((0, back_y - 50, 0)):
            Box(2 * half, 100, 4 * half, mode=Mode.SUBTRACT)
    return builder.part


def fold_support(sheet: BuildSheet) -> None:
    """Plie le bord gauche du panneau arrière, vu de face, vers l'arrière."""
    back_z = sheet.flats().sort_by(Face.area)[-1].center().Z
    target = -v.base_size / 2, 0, back_z
    edge = sheet.rims().filter_by(Axis.Y).sort_by_distance(target)[0]
    # La patte déborde vers le haut de ce que le bas du parallélogramme monte
    rise = v.base_support_length * tan(radians(v.base_support_tilt))
    gaps = support_gaps(edge, support_fold_length() + rise)
    flange(
        edge,
        v.base_support_length,
        degrees(support_angle()),
        gaps=gaps,
        length_from=LengthFrom.TANGENT,
    )


def cover_angle() -> float:
    """Retourne l'angle du pli du volet en degrés, jamais nul (0° est refusé)."""
    return max(v.base_cover_angle, MIN_BEND_ANGLE)


def unfold_cover[T: Shape](shape: T) -> T:
    """Fait pivoter une pièce du volet, construite repliée à 180°, à son angle de pli."""
    # Le pli est vertical, à l'angle du bord droit du panneau avant : son centre est à
    # `bend_radius` devant la face avant (y = 0)
    axis = Axis((v.base_size / 2, -v.bend_radius, 0), (0, 0, 1))
    return shape.rotate(axis, 180 - cover_angle())


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
    edge = sheet.rims().filter_by(Axis.Y).sort_by_distance((v.base_size / 2, 0, 0))[0]
    gaps = bottom_gaps(edge, v.base_cover_height)
    flange(edge, v.base_cover_length, cover_angle(), gaps=gaps)


def wrap_angle() -> float:
    """Retourne l'angle du 1er pli du rabat en degrés, jamais nul (0° est refusé)."""
    return max(v.base_wrap_angle, MIN_BEND_ANGLE)


def wrap_radius() -> float:
    """Retourne le rayon intérieur du 1er pli du rabat, qui contourne le pli du volet."""
    # La tranche du rabat passe à l'extérieur du pli du volet, et du jeu
    return v.bend_radius + v.material_thickness + v.base_wrap_gap


def wrap_wall_length() -> float:
    """Retourne la longueur droite de la tranche du rabat, entre ses deux plis."""
    # Replié à 90°, le rabat va de la face avant du panneau arrière jusqu'au volet : il
    # fait l'épaisseur du socle, hors panneau avant (rayons et jeu s'annulent)
    return (len(v.dials) + 1) * v.material_thickness


def wrap_wall_end() -> tuple[float, float]:
    """Retourne la position (x, y) du bout de la tranche, sur son plan moyen."""
    thickness, radius = v.material_thickness, wrap_radius()
    # Le pli tourne autour d'un centre devant la face avant du panneau arrière
    angle = radians(wrap_angle())
    center = v.base_size / 2, (len(v.dials) + 1) * thickness - radius
    reach = radius + thickness / 2
    start = center[0] + reach * sin(angle), center[1] + reach * cos(angle)
    length = wrap_wall_length()
    return start[0] + length * cos(angle), start[1] - length * sin(angle)


def unfold_wrap[T: Shape](shape: T) -> T:
    """Fait pivoter une pièce du rabat, construite repliée à 90°, à l'angle de ses plis."""
    # Les deux plis sont verticaux. Le 2e pivote d'abord, autour de son centre, puis le
    # 1er emporte la tranche et le rabat autour de son propre centre.
    thickness, radius, half = v.material_thickness, v.bend_radius, v.base_size / 2
    first = Axis((half, (len(v.dials) + 1) * thickness - wrap_radius(), 0), (0, 0, 1))
    inner_x = half + wrap_radius()
    flap_y = -(2 * radius + thickness + v.base_wrap_gap)  # face intérieure du rabat
    second = Axis((inner_x - radius, flap_y + radius, 0), (0, 0, 1))
    delta = 90 - wrap_angle()
    return shape.rotate(second, delta).rotate(first, delta)


def fold_wrap(sheet: BuildSheet) -> None:
    """Plie le bord droit du panneau arrière vers l'avant, puis sur la face avant."""
    back_z = sheet.flats().sort_by(Face.area)[-1].center().Z
    edge = sheet.rims().filter_by(Axis.Y).sort_by_distance((v.base_size / 2, 0, back_z))[0]
    angle = wrap_angle()
    gaps = bottom_gaps(edge, v.base_wrap_height)
    flange(edge, wrap_wall_length(), -angle, wrap_radius(), gaps)
    # Le 2e pli est sur le bout de la tranche, de la même hauteur et du même angle
    x, y = wrap_wall_end()
    end = sheet.rims().filter_by(Axis.Y).sort_by_distance((x, 0, -y))[0]
    flange(end, v.base_wrap_length, -angle)


def fold_sides(sheet: BuildSheet) -> None:
    """Plie les côtés du socle : support, volet de la face avant et rabat de la tranche."""
    fold_support(sheet)
    fold_cover(sheet)
    fold_wrap(sheet)


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


def cover_teeth() -> Part:
    """Construit la matière à retirer de l'arc du disque du volet pour y faire des dents."""
    radius = v.base_cover_disc_diam / 2
    points = cover_teeth_points()

    def polar(r: float, angle: float) -> tuple[float, float]:
        return r * cos(radians(angle)), r * sin(radians(angle))

    # Un seul contour : le zigzag des dents, puis le retour par l'extérieur du cercle,
    # pour retirer aussi l'arc
    teeth = [polar(radius - depth, angle) for angle, depth in points]
    outside = [polar(radius + 1, angle) for angle, _ in reversed(points)]
    # Hors de la face avant du panneau, pour ne couper que le volet
    plane = Plane.XZ.offset(2 * v.bend_radius - 0.5)
    with BuildPart() as builder:
        with BuildSketch(plane):
            Polygon(*teeth, *outside, align=None)
        extrude(amount=v.material_thickness + 1)
    return builder.part


def add_cover_disc(body: Compound) -> Compound:
    """Ajoute au volet le disque centré sur le rivet, percé du trou du rivet."""
    thickness = v.material_thickness
    radius = v.base_cover_disc_diam / 2
    # Le volet est replié à `bend_radius * 2` de la face avant du panneau avant (y = 0)
    plane = Plane.XZ.offset(2 * v.bend_radius)
    center = Align.CENTER, Align.CENTER
    with BuildPart() as disc, Locations(plane):
        Cylinder(radius, thickness, align=(*center, Align.MIN))
    with BuildPart() as hole, Locations(plane.offset(-1)):
        Cylinder(v.rivet_diam / 2, thickness + 2, align=(*center, Align.MIN))
    # Le bord gauche du volet descend à 45° vers la droite, depuis le point le plus bas du
    # disque : on retire ce qui dépasse la droite x + z = -rayon, hors du plan de la face
    reach = v.base_size
    below = (0, -radius), (reach, -radius - reach), (0, -radius - reach)
    with BuildPart() as cut:
        with BuildSketch(Plane.XZ.offset(thickness / 2)):
            Polygon(*below, align=None)
        # Jusqu'à la face avant du volet seulement, pour épargner le rabat qui le recouvre
        extrude(amount=u.cover_offset - thickness / 2)
    # Les dents ne touchent que le disque, hors du volet : creusées avant la fusion
    # Tout est construit replié à 180°, puis pivoté avec le volet
    disc_part = unfold_cover(disc.part - cover_teeth())
    cover = Compound(body - unfold_cover(cut.part) + disc_part - unfold_cover(hole.part))
    # Congé de l'angle entre la pente et le bas du volet ; l'arc du disque reste vif
    y = -(2 * v.bend_radius + thickness / 2)
    corner = unfold_cover(Vertex(v.base_size / 2 - radius, y, -v.base_size / 2))
    edge = cover.edges().sort_by_distance(corner)[0]
    return Compound([cover.fillet(v.fillet, [edge])])


def add_wrap_disc(body: Compound) -> Compound:
    """Ajoute au rabat le disque des cadrans, centré sur le rivet, et le trou de sa tête."""
    thickness, gap = v.material_thickness, v.base_wrap_gap
    # Le rabat est replié devant le volet, à `gap` de sa face avant
    plane = Plane.XZ.offset(u.cover_offset + gap)
    center = Align.CENTER, Align.CENTER
    with BuildPart() as disc, Locations(plane):
        Cylinder(u.disc_radius, thickness, align=(*center, Align.MIN))
    # Le trou ne traverse que le rabat, sans toucher le volet
    with BuildPart() as hole, Locations(plane.offset(-gap / 2)):
        Cylinder(v.rivet_head_hole / 2, thickness + gap, align=(*center, Align.MIN))
    # Tout est construit replié à 90°, puis pivoté avec le rabat
    return Compound(body + unfold_wrap(disc.part) - unfold_wrap(hole.part))


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
    skipped += u.point_vertices(corners, [(v.base_size / 2, 0)])
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


def strip_neck(spacing: float, x: float, edge_y: float, width: float) -> Part:
    """Construit la tête de la languette, jusqu'à l'extérieur du panneau arrière."""
    thickness, radius = v.material_thickness, v.bend_radius
    start = radius + thickness
    length = 2 * (radius + thickness) + spacing - start
    width = width - 2 * v.base_strip_stop - 2 * v.base_strip_clearance
    z = edge_y + radius + thickness / 2
    with BuildPart() as builder, Locations((x, start + length / 2, z)):
        Box(width, length, thickness)
    return builder.part


def base() -> Part:
    """Construit la pièce correspondant au socle."""
    thickness, radius = v.material_thickness, v.bend_radius
    # Longueur plane ajoutée entre les deux pliages, pour écarter les deux panneaux
    spacing = len(v.dials) * v.material_thickness - 2 * radius
    necks = []

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
                flange(edge, radius + spacing, -90, gaps=strip_fit(edge, x, width))
                necks.append((x, edge_y, width))

                back_z = sheet.flats().sort_by(Face.area)[-1].center().Z
                wall_z = edge_y + radius + thickness / 2
                with Locations((x, wall_z, back_z)):
                    window = (
                        width - 2 * v.base_strip_stop,
                        thickness + 2 * v.base_strip_clearance,
                    )
                    Rectangle(*window, mode=Mode.SUBTRACT)

            fold_sides(sheet)
        thicken()

    # Têtes de languettes gardées séparées : fusionnées, elles combleraient la fenêtre
    # du panneau arrière quand le jeu est nul, et son contour disparaîtrait.
    body = add_wrap_disc(add_cover_disc(builder.part - support_trim()))
    part = Part([body, *(strip_neck(spacing, *neck) - body for neck in necks)])
    part.label = v.base[0]
    part.color = Color(v.base[1])
    return part
