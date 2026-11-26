"""List of values used in the project."""

epsilon = 0.01

# Assembly
tab_angles = 0, 10, 20, 30, 40  # one dial for each angle, from front to back

# Base
base_size = 210, 210
sheet_gap = 6  # inner distance between the two sheets: room for the dials plus 1 mm

# Arc-shaped window of the front sheet, showing the ends of the dial tabs at rest
view_width = 10  # width of the window
view_angle = max(tab_angles) + 10  # angle covered from the left edge, past the last tab

# Strip folded from the front sheet, hat-shaped: the head stops against the back sheet,
# the neck goes through a window in the back sheet
strip_width = 20  # width of the head
strip_pos = 65  # horizontal position of the strip center from the dial center
strip_drop = 1  # how far the strip is lowered below the dial axis
strip_protrusion = 0  # how far the neck sticks out of the back sheet
window_width = 15  # width of the window (the neck is narrower by twice the clearance)
strip_clearance = 0.1  # play between the neck and the window, on each side

# Dial
disc_diam = 74
dial_diam = min(base_size) - 5
stop_size = (5, 2)
stop_loc = dial_diam / 2 - 5, 0
tab_height = 5
slot_width = 10
slot_start = 45
slot_length = 180
notch_size = strip_width + 0.5, strip_drop + 0.25  # notches clearing the strip of the base

# Fasteners
rivet_diam = 5
rivet_head = 8, 2

# Material
material_thickness = 1

# Global
fillet = 2.5
bend_radius = 1
