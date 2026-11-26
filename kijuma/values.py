"""Liste des valeurs utilisées dans le projet."""

# === Global ===

material_thickness = 1  # épaisseur du carton, en mm
fillet = 2.5  # rayon des arrondis des angles
bend_radius = 0.5  # rayon de courbure intérieur des pliages
tolerance = 0.1  # distance maximale pour retrouver un sommet par sa position, en mm

# === Assemblage ===

animated_dial = 1  # numéro du cadran à animer, de 1 à len(dials)
assembly_label = "Assemblage"
dials_label = "Cadrans"  # label du groupe contenant les cadrans
rivet = "Rivet", (0.3, 0.3, 0.3)  # label et couleur du rivet
base = "Socle", (0.7, 0.7, 0.7)  # label et couleur (r, g, b) du socle
dials = (  # label et couleur de chaque cadran, de l'arrière à l'avant
    ("Excellent", (0.0, 0.4, 0.1)),
    ("Bien", (0.5, 0.8, 0.3)),
    ("Passable", (1.0, 0.9, 0.1)),
    ("Mauvais", (1.0, 0.55, 0.0)),
    ("À rejeter", (0.85, 0.1, 0.1)),
)

# === Socle ===

tab_step = 10  # décalage de l'angle des languettes d'un cadran au suivant, à partir de 0
tab_height = 5  # largeur des languettes des cadrans
base_size = 210, 210  # largeur et hauteur du socle
base_play = 1  # jeu à laisser entre les panneaux avant et arrière
base_view_width = 10  # largeur de la fenêtre en arc de cercle
base_strip_width = 20  # largeur de la base de la languette
base_right_strip_pos = 65  # position horiz. du centre de la languette au centre du cadran
base_left_strip_margin = 1  # matière entre le bord du socle et la languette de gauche
base_right_strip_drop = 1  # de combien la languette est abaissée sous l'axe du cadran
base_strip_window_width = 15  # largeur de la fenêtre
base_strip_clearance = 0.1  # jeu entre la tête des languettes et des fenêtres

# === Cadran ===

disc_diam = 74  # diamètre du disque central
dial_diam = min(base_size) - 5  # diamètre extérieur du cadran (un peu moins que la base)
dial_stop_size = (5, 2)  # longueur et largeur de la petite butée oblongue des cadrans
dial_stop_loc = 5  # position de la butée depuis l'extérieur du cadran
dial_slot_width = 3  # largeur de la fente en arc de cercle du disque central
dial_slot_step = 18  # décalage de l'angle de la fente d'un cadran au suivant, en °
dial_flap_depth = 0.6  # hauteur de la languette pliée vers l'avant, depuis le cadran
dial_flap_fold = 5  # longueur du bout de la languette rabattu vers le centre
dial_notch_size = 0.25, 0.25  # jeux entre la l'entaille languette et la languette

# === Fixations ===

rivet_diam = 5  # diamètre de la tige du rivet, et des trous qui la reçoivent
rivet_length = 10  # longueur du rivet
rivet_head = 8, 2  # diamètre et épaisseur de la tête du rivet
