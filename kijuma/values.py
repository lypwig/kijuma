"""Liste des valeurs utilisées dans le projet."""

# === Interaction ===

animated_dial = 1  # numéro du cadran à animer, de 1 à len(dials)
base_support_angle = 180  # angle du pli du support par rapport au panneau arrière
base_cover_angle = 180  # angle du pli du volet par rapport au panneau avant (180° = replié)
base_wrap_angle = 180  # angle total des 2 plis du rabat (180° : replié, 0° : à plat)

# === Global ===

material_thickness = 1  # épaisseur du carton, en mm
fillet = 2.5  # rayon des arrondis des angles
light_fillet = 0.75  # rayon des petits arrondis (rivet, entailles, languettes)
bend_radius = 0.5  # rayon de courbure intérieur des pliages
tolerance = 0.1  # distance maximale pour retrouver un sommet par sa position, en mm

# === Assemblage ===

assembly_label = "Kijuma"
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

# --- Panneaux et fenêtre ---
base_size = 210  # largeur et hauteur du socle
base_view_width = 10  # largeur de la fenêtre en arc de cercle

# --- Languettes ---
base_left_strip_width = 15  # largeur de la base de la languette de gauche
base_right_strip_width = 20  # largeur de la base de la languette de droite
base_strip_stop = 2.5  # largeur des butées des languettes, de part et d'autre de la tête
base_strip_clearance = 0  # jeu entre la tête des languettes et des fenêtres

# --- Support (patte arrière) ---
base_support_height = 50  # largeur de la patte du support, entre ses bords haut et bas
base_support_length = 150  # longueur horizontale de la patte, depuis le panneau arrière
base_support_tilt = 20  # inclinaison du socle, vers l'arrière, une fois posé sur le support

# --- Couverture (volet replié sur la face avant, côté droit) ---
base_cover_height = base_size / 2  # hauteur du volet
base_cover_length = base_size / 2  # longueur du volet, depuis le bord droit du panneau
base_cover_disc_diam = 91  # diamètre du disque du volet, centré sur le rivet
base_cover_teeth_step = 3  # pas angulaire des dents, en ° (≈ 2 mm)
base_cover_teeth_depth = 0.75  # profondeur des dents de l'arc du disque

# --- Rabat (contourne la tranche droite, recouvre le volet) ---
base_wrap_height = base_size / 2  # hauteur du rabat
base_wrap_length = 180  # longueur du rabat replié sur la face avant, après la tranche
base_wrap_slot_width = 2  # largeur des fentes du rabat, aux bouts arrondis
base_wrap_slot_drop = 20  # distance de la 1re fente horizontale sous le rivet
base_wrap_slot_step = 20  # écart entre les 2 fentes horizontales
base_wrap_slot_h_length = 100  # longueur des fentes horizontales, centrées sur le rivet
base_wrap_slot_margin = 25, 20  # distance des fentes verticales aux côtés et au bas
base_wrap_slot_v_length = 30  # longueur des fentes verticales

# === Cadran ===

# --- Disque et fente ---
dial_disc_diam = base_size * 0.5  # diamètre du disque central
dial_diam = base_size - 5  # diamètre extérieur du cadran
dial_slot_width = 3  # largeur de la fente en arc de cercle du disque central
dial_slot_step = 18  # décalage de l'angle de la fente d'un cadran au suivant, en °

# --- Languettes de la couronne ---
dial_tab_step = 8  # décalage de l'angle des languettes d'un cadran au suivant
dial_tab_height = 5  # largeur des languettes des cadrans
dial_notch_size = 0.25  # jeu entre l'entaille cadran et la languette

# --- Butée ---
dial_stop_size = (5, 2)  # longueur et largeur de la petite butée oblongue des cadrans
dial_stop_loc = 5  # position de la butée depuis l'extérieur du cadran

# --- Languette intérieure ---
dial_flap_depth = 0.6  # hauteur de la languette pliée vers l'avant, depuis le cadran
dial_flap_fold = 5  # longueur du bout de la languette rabattu vers le centre
dial_flap_gap = 0.3  # retrait de la pliure à chaque bout, pour éviter tout chevauchement
dial_flap_teeth_step = 2.368  # pas des dents du bout de la languette intérieure, en mm
dial_flap_teeth_depth = 0.75  # profondeur des dents du bout de la languette intérieure

# === Fixations ===

# --- Rivet ---
rivet_diam = 5  # diamètre de la tige du rivet, et des trous qui la reçoivent
# Longueur du rivet : volet, panneaux, cadrans, jeu et dépassement
rivet_length = (3 + len(dials)) * material_thickness + 2 * bend_radius + 1
rivet_head = 8, 1  # diamètre et épaisseur de la tête du rivet
rivet_head_hole = rivet_head[0] + 1  # diamètre du trou du rabat, pour la tête du rivet

# === Export SVG ===

# --- Feuille de carton ---
export_sheet = (1000, 700)  # longueur et largeur de la feuille de carton, en mm
export_margin = 5  # marge entre les pièces et le bord de la feuille
export_gap = 4  # écart minimal entre deux pièces

# --- Rangement ---
export_rotation_step = 15  # pas des rotations essayées pour ranger chaque pièce, en degrés
export_resolution = 1  # taille des pixels de la grille de rangement, en mm
