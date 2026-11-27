"""Vérifie que les pièces de l'assemblage ne s'interpénètrent pas."""

from itertools import combinations

import pytest
from build123d import *
from build123d.topology import Shape

from kijuma import values as v
from kijuma.assembly import assembly

# Seuil sous lequel on ignore le recouvrement : la tige du rivet et son trou ont le même
# diamètre, leurs cylindres confondus donnent environ 0,03 mm³ de bruit de calcul.
VOLUME_TOLERANCE = 0.05  # mm³

# Un cadran ne peut pas tourner plus que ceux qui sont derrière lui : leurs languettes
# passent dans sa fente et le bloqueraient. Les angles décroissent donc de l'arrière à
# l'avant (en degrés, dans le sens de l'animation). Ils sont tous des multiples du pas des
# dents du volet : entre deux crans, les dents des languettes tombent en face de celles du
# volet et se recouvrent de 0,1 mm, un cadran ne s'y arrête donc pas.
POSITIONS = {
    "initial": (0, 0, 0, 0, 0),
    "arrière seul": (90, 0, 0, 0, 0),
    "arrière à fond": (180, 0, 0, 0, 0),
    "ensemble 30": (30, 30, 30, 30, 30),
    "ensemble 90": (90, 90, 90, 90, 90),
    "ensemble 180": (180, 180, 180, 180, 180),
    "deux paires": (90, 90, 30, 30, 0),
    "escalier 30": (120, 90, 60, 30, 0),
    "escalier 20": (99, 81, 60, 39, 21),
    "escalier fin": (12, 9, 6, 3, 0),
    "escalier haut": (180, 150, 120, 90, 60),
}


@pytest.fixture(scope="module")
def parts() -> list[Shape]:
    """Retourne le socle, le rivet et les cadrans de l'assemblage."""
    children = {c.label: c for c in assembly().children}
    dials = list(children[v.dials_label].children)
    return [children[v.base[0]], children[v.rivet[0]], *dials]


def overlaps(parts: list[Shape], angles: tuple[float, ...]) -> list[str]:
    """Retourne les paires de pièces qui se superposent, avec le volume commun."""
    # Les cadrans pivotent autour de l'axe du rivet, qui passe par l'origine
    moved = [
        *parts[:2],
        *(d.rotate(Axis.Y, a) for d, a in zip(parts[2:], angles, strict=True)),
    ]
    found = []
    for first, second in combinations(moved, 2):
        volume = sum(solid.volume for solid in (first & second).solids())
        if volume > VOLUME_TOLERANCE:
            found.append(f"{first.label} / {second.label} : {volume:.3f} mm³")
    return found


@pytest.mark.parametrize("angles", POSITIONS.values(), ids=POSITIONS.keys())
def test_parts_do_not_intersect(parts: list[Shape], angles: tuple[float, ...]) -> None:
    """Aucune pièce ne traverse une autre, quelle que soit la position des cadrans."""
    assert not overlaps(parts, angles)
