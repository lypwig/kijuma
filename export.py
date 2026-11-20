#! uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "lxml>=5.0",
#   "cssselect2>=0.7",
#   "tinycss2>=1.2",
#   "svgo-py>=4.1",
# ]
# ///

import argparse
import re
import sys
from pathlib import Path
import subprocess
import tempfile
import re

import cssselect2
import tinycss2
from lxml import etree
from svgo import optimize

def inline_css(input_path, output_path):
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(str(input_path), parser)
    root = tree.getroot()

    # Espaces de noms
    ns = {
        "svg": "http://www.w3.org/2000/svg",
    }

    # Récupération des feuilles CSS
    stylesheets = root.xpath(
        ".//svg:style",
        namespaces=ns
    )

    if not stylesheets:
        print("Aucune feuille CSS trouvée.")
        tree.write(
            str(output_path),
            encoding="utf-8",
            xml_declaration=True,
            pretty_print=False
        )
        return

    # Compilation des règles CSS
    matcher = cssselect2.Matcher()

    for style_element in stylesheets:
        css_text = style_element.text or ""

        try:
            stylesheet = cssselect2.compile_selector_list
            from tinycss2 import parse_stylesheet, parse_declaration_list

            rules = parse_stylesheet(
                css_text,
                skip_comments=True,
                skip_whitespace=True
            )

            for rule in rules:
                if rule.type != "qualified-rule":
                    continue

                selector = tinycss2.serialize(rule.prelude).strip()
                declarations = parse_declaration_list(
                    rule.content,
                    skip_comments=True,
                    skip_whitespace=True
                )

                properties = {}

                for declaration in declarations:
                    if declaration.type != "declaration":
                        continue

                    value = tinycss2.serialize(
                        declaration.value
                    ).strip()

                    if declaration.important:
                        value += " !important"

                    properties[declaration.name] = value

                for compiled_selector in cssselect2.compile_selector_list(
                    selector
                ):
                    matcher.add_selector(
                        compiled_selector,
                        properties.copy()
                    )

        except Exception as exc:
            raise RuntimeError(
                f"Erreur lors de l'analyse CSS : {exc}"
            ) from exc

    # Application des règles CSS
    wrapper = cssselect2.ElementWrapper.from_xml_root(root)

    count = 0

    for element_wrapper in wrapper.iter_subtree():
        element = element_wrapper.etree_element

        if not isinstance(element.tag, str):
            continue

        matches = matcher.match(element_wrapper)

        if not matches:
            continue

        # Récupération des styles existants inline
        existing_style = {}

        for declaration in (element.get("style") or "").split(";"):
            if ":" not in declaration:
                continue

            name, value = declaration.split(":", 1)
            existing_style[name.strip()] = value.strip()

        # Calcul de la cascade CSS
        computed = {}

        for specificity, order, pseudo, declarations in matches:
            for name, value in declarations.items():
                important = value.endswith(" !important")
                clean_value = re.sub(
                    r"\s*!important$",
                    "",
                    value
                )

                priority = (
                    important,
                    specificity,
                    order
                )

                if (
                    name not in computed
                    or priority >= computed[name][0]
                ):
                    computed[name] = (
                        priority,
                        clean_value
                    )

        # Les styles inline existants restent prioritaires
        for name, value in computed.items():
            if name not in existing_style:
                existing_style[name] = value[1]

        # Écriture des styles inline
        if existing_style:
            element.set(
                "style",
                ";".join(
                    f"{name}:{value}"
                    for name, value in existing_style.items()
                )
            )

        # Suppression de la classe
        element.attrib.pop("class", None)
        count += 1

    # Suppression des feuilles CSS
    for style_element in stylesheets:
        parent = style_element.getparent()
        if parent is not None:
            parent.remove(style_element)

    # Écriture du SVG final
    tree.write(
        str(output_path),
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=False
    )

    # Sérialisation du SVG après conversion CSS
    svg_data = etree.tostring(
        tree,
        encoding="unicode",
        xml_declaration=False
    )

    # Configuration SVGO
    svgo_config = {
        "multipass": True,
        "js2svg": {
            "indent": 1,
            "pretty": True,
        },
        "plugins": [
            "preset-default",
            # {
            #     "name": "removeElementsByAttr",
            #     "params": {
            #         "id": [],
            #         "class": [],
            #     }
            # },
            "cleanupListOfValues",
            "convertOneStopGradients",
            "removeRasterImages",
            "removeScripts",
            "removeStyleElement",
            "removeTitle",
            "removeXlink",
            "reusePaths",
        ]
    }

    print("Optimisation SVGO en cours...")

    result = optimize(svg_data, svgo_config)

    # Écriture du résultat
    Path(output_path).write_text(
        result["data"],
        encoding="utf-8"
    )

    print(f"Éléments traités : {count}")
    print(f"Fichier optimisé : {output_path}")


def export_pages(input_path, output_dir):
    input_path = Path(input_path)
    output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    tree = etree.parse(str(input_path))

    # Namespace Inkscape
    ns = {
        "inkscape": "http://www.inkscape.org/namespaces/inkscape",
    }

    pages = tree.xpath(
        "//*[local-name()='page' and namespace-uri()='http://www.inkscape.org/namespaces/inkscape']"
    )

    if not pages:
        raise RuntimeError("Aucune page Inkscape trouvée.")

    print(f"{len(pages)} page(s) détectée(s).")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        for i, page in enumerate(pages):
            page_num = i + 1

            page_name = page.get(
                "{http://www.inkscape.org/namespaces/inkscape}label"
            )

            if not page_name:
                page_name = f"page{page_num}"

            # Nettoyage du nom de fichier
            page_name = re.sub(
                r'[^\w.-]+',
                '_',
                page_name
            )

            if not page_name.startswith("cnc_"):
                break

            temp_svg = tmp_dir / f"page_{page_num}.svg"

            output_svg = output_dir / (
                f"{input_path.stem}_{page_name}.svg"
            )

            print(
                f"Export page {page_num} : {page_name}"
            )

            # Export Plain SVG avec Inkscape
            subprocess.run(
                [
                    "inkscape",
                    str(input_path),
                    f"--export-page={page_num}",
                    # "--export-area-page",
                    # "--export-id=decoupe",
                    # "--export-id-only",
                    "--export-plain-svg",
                    f"--export-filename={temp_svg}",
                ],
                check=True
            )

            # Conversion CSS + optimisation SVGO
            inline_css(temp_svg, output_svg)

            print(f"  -> {output_svg}")

    print(f"\nExport terminé : {len(pages)} page(s).")


def main():
    parser = argparse.ArgumentParser(
        description="Export des pages Inkscape en Plain SVG avec optimisation."
    )

    parser.add_argument(
        "input",
        help="Fichier SVG source"
    )

    parser.add_argument(
        "-o",
        "--output",
        default="export",
        help="Dossier de destination (défaut : export)"
    )

    args = parser.parse_args()

    input_path = Path(args.input)

    if not input_path.is_file():
        parser.error(f"Fichier introuvable : {input_path}")

    export_pages(input_path, args.output)


if __name__ == "__main__":
    main()
