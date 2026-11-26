"""Point d'entrée pour construire et animer le modèle."""

from build123d import *
from ocp_viewer import Animation, show

from . import values as v
from .assembly import assembly

show(assembly())

anim = Animation()
label = v.dials[v.animated_dial - 1][0]
anim.add_track(f"/{v.assembly_label}/{label}", "ry", [0, 1, 2], [0, 90, 180])
anim.animate(1)
