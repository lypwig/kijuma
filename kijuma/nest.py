"""Range des patrons à plat sur une feuille, en minimisant la longueur utilisée."""

import logging
from dataclasses import dataclass, field
from itertools import pairwise
from math import ceil

import numpy as np
from build123d import *

from . import values as v

logger = logging.getLogger(__name__)

Grid = np.ndarray  # tableau de booléens : vrai là où la grille est occupée
THRESHOLD = 0.5  # seuil entre un pixel vide et un pixel occupé, après convolution


@dataclass
class Piece:
    """Le patron à plat d'une pièce : son contour de découpe et ses lignes de pliage."""

    label: str
    outline: Face  # surface du patron, pour le rangement
    cuts: list[Wire]  # traits de découpe : le contour, et les bords des languettes
    folds: list[Edge]
    engravings: list[Wire] = field(default_factory=list)  # textes à graver ou imprimer

    def moved(self, location: Location) -> "Piece":
        """Retourne le patron déplacé."""
        cuts = [cut.moved(location) for cut in self.cuts]
        folds = [fold.moved(location) for fold in self.folds]
        engravings = [engraving.moved(location) for engraving in self.engravings]
        return Piece(self.label, self.outline.moved(location), cuts, folds, engravings)

    def rotated(self, angle: float) -> "Piece":
        """Retourne le patron pivoté de `angle` degrés, recalé dans l'angle (0, 0)."""
        turned = self.moved(Rotation(0, 0, angle))
        box = turned.outline.bounding_box()
        return turned.moved(Location((-box.min.X, -box.min.Y, 0)))


@dataclass
class Placement:
    """Un patron, déjà pivoté et recalé dans l'angle (0, 0), rangé sur la feuille."""

    piece: Piece
    position: tuple[float, float]

    def placed(self) -> Piece:
        """Retourne le patron à sa place sur la feuille."""
        return self.piece.moved(Location((*self.position, 0)))


@dataclass
class Spot:
    """Une place libre pour un patron, dans une orientation donnée (en pixels)."""

    right: int  # bord droit : ce que l'on cherche à minimiser
    column: int
    row: int
    angle: float
    piece: Piece
    grid: Grid

    @property
    def key(self) -> tuple[int, int, int]:
        """Retourne la clé de comparaison : la plus à gauche, puis la plus basse."""
        return self.right, self.column, self.row


def outline_segments(face: Face, resolution: float) -> list[tuple[float, ...]]:
    """Retourne les segments (x0, y0, x1, y1) qui approchent tous les bords de la face."""
    segments = []
    for wire in (face.outer_wire(), *face.inner_wires()):
        for edge in wire.edges():
            count = 1 if edge.geom_type == GeomType.LINE else ceil(edge.length / resolution)
            points = [edge.position_at(i / count) for i in range(count + 1)]
            segments += [(a.X, a.Y, b.X, b.Y) for a, b in pairwise(points)]
    return segments


def rasterize(face: Face, resolution: float) -> Grid:
    """Remplit une grille dont les pixels, de côté `resolution`, sont dans la face."""
    size = face.bounding_box().size
    width, height = ceil(size.X / resolution), ceil(size.Y / resolution)
    # Parité : chaque bord croisé par la ligne de pixels inverse l'état à partir de là
    toggles = np.zeros((height, width + 1), dtype=np.int8)
    for x0, y0, x1, y1 in outline_segments(face, resolution):
        if y0 == y1:
            continue
        low, high = sorted((y0, y1))
        rows = np.arange(ceil(low / resolution - 0.5), ceil(high / resolution - 0.5))
        rows = rows[(rows >= 0) & (rows < height)]
        x = x0 + ((rows + 0.5) * resolution - y0) * (x1 - x0) / (y1 - y0)
        columns = np.clip(np.ceil(x / resolution - 0.5).astype(int), 0, width)
        toggles[rows, columns] ^= 1
    return (np.cumsum(toggles, axis=1) % 2)[:, :width].astype(bool)


def convolve(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    """Retourne la convolution complète de deux tableaux, par transformée de Fourier."""
    shape = [a + b - 1 for a, b in zip(first.shape, second.shape, strict=True)]
    return np.fft.irfft2(np.fft.rfft2(first, shape) * np.fft.rfft2(second, shape), shape)


def dilate(grid: Grid, radius: int) -> Grid:
    """Retourne la grille, entourée de `radius` pixels, épaissie d'un disque de ce rayon."""
    span = np.arange(-radius, radius + 1)
    disc = (span[:, None] ** 2 + span[None, :] ** 2 <= radius**2).astype(float)
    padded = np.pad(grid.astype(float), radius)
    full = convolve(padded, disc)
    return (
        full[radius : radius + padded.shape[0], radius : radius + padded.shape[1]]
        > THRESHOLD
    )


def overlaps(taken: Grid, piece: Grid) -> np.ndarray:
    """Retourne, pour chaque position du coin de `piece`, le nombre de pixels superposés."""
    # La corrélation est la convolution avec la grille de la pièce retournée
    full = convolve(taken.astype(float), piece[::-1, ::-1].astype(float))
    rows, columns = (a - b for a, b in zip(taken.shape, piece.shape, strict=True))
    return full[piece.shape[0] - 1 :][: rows + 1, piece.shape[1] - 1 :][:, : columns + 1]


def stamp(taken: Grid, mask: Grid, row: int, column: int) -> None:
    """Marque `mask` comme occupé dans `taken`, son coin à (`row`, `column`)."""
    top, left = max(row, 0), max(column, 0)
    bottom = min(row + mask.shape[0], taken.shape[0])
    right = min(column + mask.shape[1], taken.shape[1])
    taken[top:bottom, left:right] |= mask[
        top - row : bottom - row,
        left - column : right - column,
    ]


def best_spot(taken: Grid, piece: Piece, angle: float, margin: int) -> Spot | None:
    """Retourne la place libre la plus à gauche pour le patron pivoté de `angle`."""
    turned = piece.rotated(angle)
    grid = rasterize(turned.outline, v.export_resolution)
    height, width = taken.shape
    rows, columns = grid.shape
    if rows > height - 2 * margin or columns > width - 2 * margin:
        return None
    free = overlaps(taken, grid) < THRESHOLD
    free[:margin, :] = False
    free[:, :margin] = False
    free[height - margin - rows + 1 :, :] = False
    free[:, width - margin - columns + 1 :] = False
    if not free.any():
        return None
    free_rows, free_columns = np.nonzero(free)
    # La feuille est remplie de gauche à droite : on minimise la longueur utilisée
    best = np.lexsort((free_rows, free_columns))[0]
    column, row = int(free_columns[best]), int(free_rows[best])
    return Spot(column + columns, column, row, angle, turned, grid)


def nest(
    pieces: list[Piece],
    sheet: tuple[float, float] = v.export_cardboard_sheet_size,
    gap: float = v.export_gap,
    margin: float = v.export_margin,
    step: float = v.export_rotation_step,
) -> list[Placement]:
    """
    Range les patrons sur la feuille, en minimisant la longueur utilisée.

    Les patrons sont rangés du plus grand au plus petit, chacun dans l'orientation et à la
    place libre qui raccourcissent le moins la feuille. L'espace est une grille de pixels :
    les patrons sont épaissis de `gap` pour garder cet écart avec leurs voisins. Ils ne sont
    que pivotés, jamais retournés, et ceux qui portent du texte ne sont pas pivotés.
    """
    resolution = v.export_resolution
    taken = np.zeros((ceil(sheet[1] / resolution), ceil(sheet[0] / resolution)), dtype=bool)
    reach, border = ceil(gap / resolution) + 1, ceil(margin / resolution)
    placements = []
    logger.info("Rangement de %d pièces, rotations de %g°", len(pieces), step)
    for piece in sorted(pieces, key=lambda p: -p.outline.area):
        # Une pièce avec du texte garde son orientation, pour qu'il reste lisible
        angles = [0.0] if piece.engravings else np.arange(0, 360, step)
        spots = (best_spot(taken, piece, float(a), border) for a in angles)
        spot = min((s for s in spots if s), key=lambda s: s.key, default=None)
        if spot is None:
            message = f"{piece.label} ne tient pas sur la feuille {sheet}"
            raise ValueError(message)
        logger.info("Rangement de %s : %.0f°", piece.label, spot.angle)
        stamp(taken, dilate(spot.grid, reach), spot.row - reach, spot.column - reach)
        position = spot.column * resolution, spot.row * resolution
        placements.append(Placement(spot.piece, position))
    return placements
