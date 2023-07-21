"""
This module includes all the common imports and variable used in other modules.
"""

from rich.console import Console
from rich.theme import Theme
import os

console = Console(theme=Theme({
    "normal1" : "bold blue1",
    "normal2" : "bold dark_violet",
    "warning1": "bold plum4",
    "warning2": "bold red",
    "exists"  : "bold chartreuse3"
}))


# SFX_LOC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SFX", "Yay.mp3").replace("\\", "/")
SFX_LOC = "SFX\\Yay.mp3"
