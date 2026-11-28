"""Exporte en SVG les patrons à plat de toutes les pièces, rangés sur une feuille."""

import argparse
import logging
from pathlib import Path

from build123d import *
from build123d.topology.shape_core import Shape

from . import values as v
from .base import base_sheet
from .dial import dial_sheet
from .label import label_outline, label_text
from .nest import Piece, Placement, nest

logger = logging.getLogger(__name__)

CARDBOARD_FILE = "carton.svg"
PAPER_FILE = "papier.svg"

PARALLEL = 0.999  # cosinus minimal entre deux directions considérées parallèles
TOLERANCE = 1e-3  # distance en dessous de laquelle deux points sont confondus, en mm


def fold_joints(flat: Shape, folds: list[Edge]) -> list[Edge]:
    """Retourne les bords des pliages par lesquels ils se raccordent aux faces voisines."""
    joints = []
    for fold in folds:
        # Le pliage est la face dépliée qui contient sa ligne médiane
        bend = min(flat.faces(), key=lambda f: f.distance_to(fold.center()))
        direction = fold.tangent_at(0.5)
        joints += [
            e for e in bend.edges() if abs(e.tangent_at(0.5).dot(direction)) > PARALLEL
        ]
    return joints


def cut_lines(flat: Shape, joints: list[Edge]) -> list[Wire]:
    """
    Retourne les traits de découpe d'une tôle dépliée.

    Ce sont tous les bords des faces dépliées, sauf ceux par lesquels elles se raccordent
    à un pliage. En particulier, les bords d'une languette dépliée, qui touchent la tôle
    voisine sans en être reliés, sont à découper, même s'ils ne sont plus un contour.
    """
    edges = [edge for face in flat.faces() for edge in face.edges()]
    pieces = edges[0].fuse(*edges[1:]).edges()  # coupés là où ils se chevauchent
    kept = [
        e for e in pieces if not any(j.distance_to(e.center()) < TOLERANCE for j in joints)
    ]
    return list(Wire.combine(kept))


def flat_piece(label: str, sheet: BuildSheet) -> Piece:
    """Déplie la tôle, et retourne son patron : surface, traits de découpe et pliages."""
    logger.info("Dépliage de %s", label)
    flat, faces = unfold(sheet.sheet_local, sheet_parameters=sheet.sheet_parameters)
    folds = [f.bend_line for f in faces.values() if f.is_bend and f.bend_line]
    cuts = cut_lines(flat, fold_joints(flat, folds))
    # Les plats et les pliages, fusionnés en une seule surface, servent au rangement
    parts = flat.faces()
    outline = parts[0].fuse(*parts[1:]).clean().face()
    box = outline.bounding_box()
    shift = Location((-box.min.X, -box.min.Y, 0))
    return Piece(
        label,
        outline.moved(shift),
        [cut.moved(shift) for cut in cuts],
        [fold.moved(shift) for fold in folds],
    )


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
    add_layer(svg, "Gravure", v.export_engrave_line)
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
        svg.add_shape(piece.cuts, "Decoupe")
        svg.add_shape(piece.folds, "Pliage")
        svg.add_shape(piece.engravings, "Gravure")
    svg.write(path)


def label_placement() -> Placement:
    """Retourne le label en papier fin et son texte, dans l'angle de la feuille."""
    outline = label_outline()
    corner = outline.bounding_box().min
    shift = Location((-corner.X, -corner.Y, 0))
    piece = Piece(
        v.proposal[0],
        outline.moved(shift),
        [outline.outer_wire().moved(shift)],
        [],
        [wire.moved(shift) for wire in label_text()],
    )
    return Placement(piece, (v.export_margin, v.export_margin))


def setup_logging() -> None:
    """Affiche les messages de ce module, mais pas ceux, très bavards, de build123d."""
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%H:%M:%S"))
    package = logging.getLogger(__package__)
    package.addHandler(handler)
    package.setLevel(logging.INFO)


def export_cardboard(path: Path) -> None:
    """Range les patrons du socle et des cadrans sur la feuille de carton, et les écrit."""
    placements = nest(flat_pieces())
    logger.info("Écriture de %s", path)
    export_svg(placements, str(path))
    used = max(p.placed().outline.bounding_box().max.X for p in placements)
    area = sum(p.piece.outline.area for p in placements)
    logger.info("%d pièces, longueur utilisée %.0f mm", len(placements), used)
    logger.info("Taux d'utilisation : %.0f %%", 100 * area / (used * v.export_sheet[1]))


def export_paper(path: Path) -> None:
    """Écrit le label en papier fin."""
    logger.info("Écriture de %s", path)
    export_svg([label_placement()], str(path))


def main(argv: list[str] | None = None) -> None:
    """Écrit les SVG du carton et du papier, dans le dossier donné en paramètre."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "folder",
        nargs="?",
        default="export",
        type=Path,
        help="dossier de sortie",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--cardboard", action="store_true", help="n'exporter que le carton")
    group.add_argument("--paper", action="store_true", help="n'exporter que le papier")
    args = parser.parse_args(argv)

    setup_logging()
    args.folder.mkdir(parents=True, exist_ok=True)
    if not args.paper:
        export_cardboard(args.folder / CARDBOARD_FILE)
    if not args.cardboard:
        export_paper(args.folder / PAPER_FILE)


if __name__ == "__main__":
    main()
