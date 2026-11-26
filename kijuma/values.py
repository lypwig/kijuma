"""List of values used in the project."""

epsilon = 0.01

# Base
base_size = 210, 210

# Strip folded from the front sheet, holded by a window in the back sheet
strip_width = 50  # width of the window
strip_pos = 65  # horizontal position of the strip center from the dial center
strip_clearance = 0.1  # play between the tab and the window

# Dial
disc_diam = 74
dial_diam = min(base_size) - 5
stop_size = (5, 2)
stop_loc = dial_diam / 2 - 5, 0
tab_height = 5
slot_width = 10
slot_start = 45
slot_length = 180

# Fasteners
rivet_diam = 5
rivet_head = 8, 2

# Material
material_thickness = 1

# Global
fillet = 2.5
bend_radius = 1
