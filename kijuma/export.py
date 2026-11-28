"""Exporte en SVG les patrons à plat de toutes les pièces, rangés sur une feuille."""

import logging
import sys
from dataclasses import dataclass
from itertools import pairwise
from math import ceil

import numpy as np
from build123d import *

from . import values as v
from .base import base_sheet
from .dial import dial_sheet

logger = logging.getLogger(__name__)

Grid = np.ndarray  # tableau de booléens : vrai là où la grille est occupée
HALF = 0.5  # seuil entre un pixel vide et un pixel occupé, après convolution


@dataclass
class Piece:
    """Le patron à plat d'une pièce : son contour de découpe et ses lignes de pliage."""

    label: str
    outline: Face
    folds: list[Edge]

    @property
    def size(self) -> tuple[float, float]:
        """Retourne la largeur et la hauteur de la boîte englobante du patron."""
        box = self.outline.bounding_box()
        return box.size.X, box.size.Y

    def moved(self, location: Location) -> "Piece":
        """Retourne le patron déplacé."""
        folds = [fold.moved(location) for fold in self.folds]
        return Piece(self.label, self.outline.moved(location), folds)

    def rotated(self, angle: float) -> "Piece":
        """Retourne le patron pivoté de `angle` degrés, recalé dans l'angle (0, 0)."""
        turned = self.moved(Rotation(0, 0, angle))
        box = turned.outline.bounding_box()
        return turned.moved(Location((-box.min.X, -box.min.Y, 0)))


@dataclass
class Placement:
    """Un patron rangé sur la feuille."""

    piece: Piece
    angle: float
    position: tuple[float, float]


def flat_piece(label: str, sheet: BuildSheet) -> Piece:
    """Déplie la tôle, et retourne son contour de découpe et ses lignes de pliage."""
    logger.info("Dépliage de %s", label)
    flat, faces = unfold(sheet.sheet_local, sheet_parameters=sheet.sheet_parameters)
    # Les plats et les pliages dépliés sont fusionnés en un seul contour de découpe
    parts = flat.faces()
    outline = parts[0].fuse(*parts[1:]).clean().face()
    folds = [f.bend_line for f in faces.values() if f.is_bend and f.bend_line]
    shift = Location((-outline.bounding_box().min.X, -outline.bounding_box().min.Y, 0))
    return Piece(label, outline.moved(shift), [fold.moved(shift) for fold in folds])


def flat_pieces() -> list[Piece]:
    """Retourne les patrons du socle et des cadrans."""
    logger.info("Construction de %s", v.base[0])
    _, sheet = base_sheet()
    pieces = [flat_piece(v.base[0], sheet)]
    for i, (label, _) in enumerate(v.dials):
        extra = (len(v.dials) - 1 - i) * v.material_thickness
        logger.info("Construction de %s", label)
        _, sheet = dial_sheet(i * v.dial_tab_step, i * v.dial_slot_step, extra)
        pieces.append(flat_piece(label, sheet))
    return pieces


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


def dilate(grid: Grid, radius: int) -> Grid:
    """Retourne la grille épaissie d'un disque de `radius` pixels, par convolution."""
    span = np.arange(-radius, radius + 1)
    disc = (span[:, None] ** 2 + span[None, :] ** 2 <= radius**2).astype(float)
    padded = np.pad(grid.astype(float), radius)
    shape = [a + b - 1 for a, b in zip(padded.shape, disc.shape, strict=True)]
    product = np.fft.rfft2(padded, shape) * np.fft.rfft2(disc, shape)
    full = np.fft.irfft2(product, shape)
    return full[radius : radius + padded.shape[0], radius : radius + padded.shape[1]] > HALF


def overlaps(taken: Grid, piece: Grid) -> np.ndarray:
    """Retourne, pour chaque position du coin de `piece`, le nombre de pixels superposés."""
    shape = [a + b for a, b in zip(taken.shape, piece.shape, strict=True)]
    product = np.fft.rfft2(taken.astype(float), shape) * np.conj(
        np.fft.rfft2(piece.astype(float), shape),
    )
    full = np.fft.irfft2(product, shape)
    rows, columns = (a - b + 1 for a, b in zip(taken.shape, piece.shape, strict=True))
    return full[:rows, :columns]


def stamp(taken: Grid, mask: Grid, row: int, column: int) -> None:
    """Marque `mask` comme occupé dans `taken`, son coin à (`row`, `column`)."""
    top, left = max(row, 0), max(column, 0)
    bottom = min(row + mask.shape[0], taken.shape[0])
    right = min(column + mask.shape[1], taken.shape[1])
    taken[top:bottom, left:right] |= mask[
        top - row : bottom - row,
        left - column : right - column,
    ]


def best_spot(
    taken: Grid,
    piece: Grid,
    margin: int,
) -> tuple[int, int, int] | None:
    """Retourne (bord droit, colonne, ligne) de la place libre la plus à gauche."""
    height, width = taken.shape
    if piece.shape[0] > height - 2 * margin or piece.shape[1] > width - 2 * margin:
        return None
    count = overlaps(taken, piece)
    free = count < HALF
    free[:margin, :] = False
    free[:, :margin] = False
    free[height - margin - piece.shape[0] + 1 :, :] = False
    free[:, width - margin - piece.shape[1] + 1 :] = False
    if not free.any():
        return None
    rows, columns = np.nonzero(free)
    # La feuille est remplie de gauche à droite : on minimise la longueur utilisée
    best = np.lexsort((rows, columns))[0]
    return int(columns[best]) + piece.shape[1], int(columns[best]), int(rows[best])


def nest(
    pieces: list[Piece],
    sheet: tuple[float, float] = v.export_sheet,
    gap: float = v.export_gap,
    margin: float = v.export_margin,
    step: float = v.export_rotation_step,
) -> list[Placement]:
    """
    Range les patrons sur la feuille, en minimisant la longueur utilisée.

    Les patrons sont rangés du plus grand au plus petit, chacun dans l'orientation et à la
    place libre qui raccourcissent le moins la feuille. L'espace est une grille de pixels :
    les patrons sont épaissis de `gap` pour garder cet écart avec leurs voisins.
    """
    resolution = v.export_resolution
    taken = np.zeros((ceil(sheet[1] / resolution), ceil(sheet[0] / resolution)), dtype=bool)
    reach, border = ceil(gap / resolution) + 1, ceil(margin / resolution)
    placements = []
    logger.info("Rangement de %d pièces, rotations de %g°", len(pieces), step)
    for piece in sorted(pieces, key=lambda p: -p.outline.area):
        best: tuple[int, int, int, float, Piece, Grid] | None = None
        for angle in np.arange(0, 360, step):
            turned = piece.rotated(float(angle))
            grid = rasterize(turned.outline, resolution)
            spot = best_spot(taken, grid, border)
            if spot and (best is None or spot < best[:3]):
                best = *spot, float(angle), turned, grid
        if best is not None:
            logger.info("Rangement de %s : %.0f°", piece.label, best[3])
        if best is None:
            message = f"{piece.label} ne tient pas sur la feuille {sheet}"
            raise ValueError(message)
        _, column, row, angle, turned, grid = best
        stamp(taken, dilate(grid, reach), row - reach, column - reach)
        placements.append(Placement(turned, angle, (column * resolution, row * resolution)))
    return placements


def add_layer(svg: ExportSVG, name: str, line: tuple[float, str, str]) -> None:
    """Ajoute au SVG le calque `name`, dont le trait est (épaisseur, couleur, type)."""
    weight, color, kind = line
    svg.add_layer(name, line_color=color, line_weight=weight, line_type=LineType[kind])


def export_svg(placements: list[Placement], path: str) -> None:
    """Écrit le SVG : la découpe, les pliages, et un cadre autour des découpes."""
    svg = ExportSVG(unit=Unit.MM, margin=v.export_margin)
    add_layer(svg, "Cadre", v.export_frame_line)
    add_layer(svg, "Decoupe", v.export_cut_line)
    add_layer(svg, "Pliage", v.export_fold_line)
    moved = [p.piece.moved(Location((*p.position, 0))) for p in placements]
    # Le cadre entoure la boîte englobante des découpes, avec la marge
    box = Compound([piece.outline for piece in moved]).bounding_box()
    margin = v.export_margin
    frame = Rectangle(box.size.X + 2 * margin, box.size.Y + 2 * margin, align=Align.MIN)
    svg.add_shape(
        frame.wire().moved(Location((box.min.X - margin, box.min.Y - margin, 0))),
        "Cadre",
    )
    for piece in moved:
        svg.add_shape(piece.outline.wires(), "Decoupe")
        svg.add_shape(piece.folds, "Pliage")
    svg.write(path)


def main(path: str = "kijuma.svg") -> None:
    """Range tous les patrons sur la feuille et les écrit dans le fichier SVG."""
    # Seuls les messages de ce module sont affichés, pas ceux, très bavards, de build123d
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    placements = nest(flat_pieces())
    logger.info("Écriture de %s", path)
    export_svg(placements, path)
    used = max(p.position[0] + p.piece.size[0] for p in placements)
    area = sum(p.piece.outline.area for p in placements)
    logger.info("%d pièces, longueur utilisée %.0f mm", len(placements), used)
    logger.info("Taux d'utilisation : %.0f %%", 100 * area / (used * v.export_sheet[1]))


if __name__ == "__main__":
    main(*sys.argv[1:])
