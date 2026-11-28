# Kijuma

**Kit de jugement majoritaire**

Un outil en carton permettant d'effectuer des scrutins au jugement majoritaire, pour 5 à 40 participant.es avec 1 à 7 propositions.

Ce dépôt contient un module Python basé sur build123d permetant de dessiner les pièces à découper.

## Développement

Lancez le viewer (qui devrait apparaitre sur `http://127.0.0.1:3939/viewer`) :

    nix-shell --run viewer

Dans un autre terminal, lancez le watcher :

    nix-shell --run watcher

Dans un autre terminal, lancez un shell nix :

    nix-shell

De là vous pouvez :

Lancez le linter et l'analyse de typage :

    uv run ruff check && uv run ty check

Lancer les tests (non-intersection des pièces, tôle dépliée sans superposition) :

    uv run pytest

Exporter en SVG pour la découpe :

    uv run python -m kijuma.export export/kijuma.svg

Voir la section "Export SVG" dans `kijuma/values.py` pour paramétrer l'export (dimensions de la feuille, écart entre pièces, couleurs des lignes, etc).

## Paternité

Auteur: Nathanaël Jourdane

Licence: [MIT](https://mit-license.org/)
