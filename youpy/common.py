"""
This module includes all the common imports and variable used in other modules.
"""

from rich.console import Console
from rich.theme import Theme

console = Console(theme=Theme({
    "normal1" : "bold blue1",
    "normal2" : "bold dark_violet",
    "warning1": "bold plum4",
    "warning2": "bold red",
    "exists"  : "bold chartreuse3"
}))
