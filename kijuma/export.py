"""Exporte en SVG les patrons à plat de toutes les pièces, rangés sur une feuille."""

import logging
import sys

from build123d import *

from . import values as v
from .base import base_sheet
from .dial import dial_sheet
from .nest import Piece, Placement, nest

logger = logging.getLogger(__name__)


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
    moved = [p.placed() for p in placements]
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


def setup_logging() -> None:
    """Affiche les messages de ce module, mais pas ceux, très bavards, de build123d."""
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%H:%M:%S"))
    package = logging.getLogger(__package__)
    package.addHandler(handler)
    package.setLevel(logging.INFO)


def main(path: str = "kijuma.svg") -> None:
    """Range tous les patrons sur la feuille et les écrit dans le fichier SVG."""
    setup_logging()
    placements = nest(flat_pieces())
    logger.info("Écriture de %s", path)
    export_svg(placements, path)
    used = max(p.placed().outline.bounding_box().max.X for p in placements)
    area = sum(p.piece.outline.area for p in placements)
    logger.info("%d pièces, longueur utilisée %.0f mm", len(placements), used)
    logger.info("Taux d'utilisation : %.0f %%", 100 * area / (used * v.export_sheet[1]))


if __name__ == "__main__":
    main(*sys.argv[1:])
