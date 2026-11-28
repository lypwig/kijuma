# Kijuma

**Kit de jugement majoritaire**

Un outil en carton permettant d'effectuer des scrutins au jugement majoritaire, pour 5 à 40 participant.es avec 1 à 7 propositions.

Ce dépôt contient un module Python basé sur build123d permetant de dessiner les pièces à découper.

## Développement

Lancez le viewer (qui devrait apparaitre sur `http://127.0.0.1:3939/viewer`) :

    nix-shell --run viewer

Dans un autre terminal, lancez le watcher :

    nix-shell --run watcher

Dans un autre terminal, vous pouvez lancer le linter :

    nix-shell --run linter

Pour lancer les tests (non-intersection des pièces, tôle dépliée sans superposition) :

    nix-shell --run tester

## Export pour la découpe

Pour exporter en SVG tous les patrons à plat en minimisant la longueur utilisée :

    uv run python -m kijuma.export export/kijuma.svg

Voir la section "Export SVG" dans `kijuma/values.py` pour paramétrer l'export (dimensions de la feuille, écart entre pièces, couleurs des lignes, etc).

## Paternité

Auteur: Nathanaël Jourdane

Licence: [MIT](https://mit-license.org/)
