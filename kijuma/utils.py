"""Valeurs dérivées et fonctions utilitaires."""

from collections.abc import Iterable as Itr
from math import cos, hypot, radians, sin
from typing import cast

from build123d import *
from build123d.topology.shape_core import Shape

from . import values as v

FLAT_REACH = 0.75 * v.cardboard_thickness  # écart maximal à la face de référence
FLAT_NORMAL = 0.99  # composante minimale de la normale d'une face parallèle à un plan

disc_radius = v.dial_disc_diam / 2  # rayon du disque central
dial_radius = v.dial_diam / 2  # rayon extérieur du cadran
slot_radii = (
    disc_radius,
    disc_radius - v.dial_slot_width,
)  # rayons de la fente, ext. et int.
base_slot_angle = (
    180 + len(v.dials) * v.dial_slot_step
)  # angle du bout de la fente du socle

# Position horiz. de la languette de droite : centrée entre le disque central et le cadran
base_right_strip_pos = (v.dial_disc_diam + v.dial_diam) / 4
base_right_strip_drop = (v.cardboard_thickness + v.bend_radius) / 2  # abaissement languette

# Distance de la face avant du volet à celle du panneau avant, une fois le volet replié
cover_offset = 2 * v.bend_radius + v.cardboard_thickness

# Jeu symbolique entre deux faces de tôle qui ne doivent pas se toucher, comme le rabat et
# le volet : un contact exact, ou un bord dans le plan d'une autre face, fait échouer
# l'épaississement de la tôle
min_gap = 0.001

# Enfoncement du pli du volet dans le socle, pour que le rabat passe à l'extérieur du pli
# tout en gardant le même rayon de pliage que les autres plis
cover_inset = v.cardboard_thickness + min_gap


def notch_half(strip_width: float) -> float:
    """Retourne la demi-largeur de l'entaille qui reçoit une languette de cette largeur."""
    return strip_width / 2 + v.dial_notch_size


def point_vertices(vertices: Itr[Vertex], points: Itr[tuple[float, float]]) -> list[Vertex]:
    """Retourne les sommets situés aux points (x, y) donnés."""
    points = list(points)
    return [
        p
        for p in vertices
        if any(hypot(p.X - px, p.Y - py) < v.tolerance for px, py in points)
    ]


def polar_vertices(vertices: Itr[Vertex], angle: float, radii: Itr[float]) -> list[Vertex]:
    """Retourne les sommets situés à l'angle (en degrés) et aux rayons donnés."""
    return point_vertices(
        vertices,
        [(r * cos(radians(angle)), r * sin(radians(angle))) for r in radii],
    )


def to_sheet(plane: Plane) -> Plane:
    """Convertit un plan, donné dans le repère global, dans le repère de la tôle."""
    # La tôle est construite sur Plane.XZ : ses axes sont X, Z et -Y
    return Plane(Plane.XZ.location.inverse() * plane.location)


def sketch_on(sheet: BuildSheet, mid: Plane, sketch: Shape, mode: Mode = Mode.ADD) -> None:
    """
    Ajoute ou retire une esquisse à la face de la tôle la plus proche du plan moyen `mid`.

    Le plan `mid` est dans le repère de la tôle, l'esquisse est dessinée dans les
    axes de `mid`. Esquisser sur une face de la tôle ajoute de la matière à son contour,
    ou en retire, comme si la tôle était à plat.
    """
    faces = [f for f in sheet.flats() if abs(f.normal_at().dot(mid.z_dir)) > FLAT_NORMAL]
    # Seules les faces à une demi-épaisseur du plan moyen sont candidates (la face de
    # référence est à ce plan ± une demi-épaisseur, les autres à plus d'une épaisseur) ;
    # la plus proche du centre de l'esquisse est choisie
    center = cast("Vector", mid.from_local_coords(cast("Compound", sketch).center()))
    near = [
        f for f in faces if abs(f.normal_at().dot(mid.origin - f.center())) < FLAT_REACH
    ]
    face = min(near, key=lambda f: f.distance_to(center))
    normal = face.normal_at()
    origin = mid.origin - normal * normal.dot(mid.origin - face.center())
    # Le plan d'esquisse suit la normale de la face : si elle est opposée à celle de `mid`,
    # l'axe y est inversé, et l'esquisse est retournée pour le compenser
    flipped = normal.dot(mid.z_dir) < 0
    drawn = Sketch(sketch.mirror(Plane.XZ)) if flipped else sketch
    # Un constructeur créé dans une fonction ne publie pas dans la tôle : l'esquisse est
    # placée sur la face, puis ajoutée ou retirée directement
    placed = Plane(origin, x_dir=mid.x_dir, z_dir=normal) * drawn
    sheet._add_to_context(*placed.faces(), mode=mode)  # noqa: SLF001
