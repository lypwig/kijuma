"""Liste des valeurs utilisées dans le projet."""

# === Global ===

material_thickness = 1  # épaisseur du carton, en mm
fillet = 2.5  # rayon des arrondis des angles
bend_radius = 1  # rayon de courbure intérieur des pliages
tolerance = 0.1  # distance maximale pour retrouver un sommet par sa position, en mm
tab_step = 10  # décalage de l'angle des languettes d'un cadran au suivant, à partir de 0
animated_dial = 2  # numéro du cadran à animer, de 1 à len(dials)

# === Assemblage ===

assembly_label = "Assemblage"
rivet = "Rivet", (0.3, 0.3, 0.3)
base = "Socle", (0.7, 0.7, 0.7)  # label et couleur (r, g, b) du socle
dials = (  # label et couleur de chaque cadran, de l'arrière à l'avant
    ("Excellent", (0.0, 0.4, 0.1)),
    ("Bien", (0.5, 0.8, 0.3)),
    ("Passable", (1.0, 0.9, 0.1)),
    ("Mauvais", (1.0, 0.55, 0.0)),
    ("À rejeter", (0.85, 0.1, 0.1)),
)

# === Socle ===

base_size = 210, 210  # largeur et hauteur du socle
base_gap = len(dials) * material_thickness + 1  # espace pour les cadrans + 1 mm de jeu

# Fenêtre en arc de cercle à l'extérieur du panneau avant
base_view_width = 10  # largeur de la fenêtre
base_view_offset = 5  # décalage de la fenêtre vers l'extérieur, par rapport au cadran
base_view_angle = len(dials) * tab_step  # angle couvert depuis le bord gauche
base_view_chamfer = 25  # hauteur du chanfrein horizontal de la pointe, au bord gauche

# Languette pliée depuis le panneau venant traverser une fenêtre du panneau arrière
base_strip_width = 20  # largeur de la base de la languette
base_strip_pos = 65  # position horizontale (du centre de la languette au centre du cadran)
base_strip_drop = 1  # de combien la languette est abaissée sous l'axe du cadran
base_strip_window_width = 15  # largeur de la fenêtre
base_strip_clearance = 0.1  # jeu entre la tête de la languette et la fenêtre

# === Cadran ===

disc_diam = 74  # diamètre du disque central
dial_diam = min(base_size) - 5  # diamètre extérieur du cadran (un peu moins que la base)
dial_stop_size = (5, 2)  # longueur et largeur de la petite butée oblongue des cadrans
dial_stop_loc = dial_diam / 2 - 5, 0  # position de la butée depuis le centre du cadran
dial_tab_height = 5  # hauteur des languettes, en bord de cadran
dial_slot_width = 10  # largeur de la fente en arc de cercle du disque central
dial_slot_length = 180  # angle couvert par la fente en arc de cercle
dial_slot_step = 10  # décalage de l'angle de la fente d'un cadran au suivant, en °
dial_notch_size = base_strip_width + 0.5, base_strip_drop + 0.25  # entailles languette

# === Fixations ===

rivet_diam = 5  # diamètre de la tige du rivet, et des trous qui la reçoivent
rivet_head = 8, 2  # diamètre et épaisseur de la tête du rivet
