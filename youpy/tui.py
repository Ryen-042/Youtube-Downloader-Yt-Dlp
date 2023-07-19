"""
This module provides TUI functions and prompts.
"""
import questionary
from questionary import Choice, Style


customStyle = Style([
    ('question',    '#aff0d7'),                     # question text
    ('instruction', '#0000ff'),                     # user instructions for select, rawselect, checkbox
    ('disabled',    'fg:#858585 italic'),           # disabled choices for select and checkbox prompts
    ('answer',      "bold fg:#223377"),             # submitted answer text behind the question
    ('pointer',     'fg:#f030ff bold'),             # pointer used in select and checkbox prompts
    ('selected',    'fg:#cc5454'),                  # style for a selected item of a checkbox
    ('separator',   'fg:#cc5454 bold italic'),      # separator in lists
    
    ("normal1",     "bold #0000ff"),
    ("normal2",     "bold #aff0d7"),
    ("warning1",    "bold #875f87"),
    ("warning2",    "bold red"),
    ("exists",      "bold #5fd700")
])


def createChoices(choices: tuple[str, ...], default_choice=-1, values: tuple[object, ...]=(), shortcuts: tuple[str, ...]=()) -> list[Choice]:
    """
    Description:
        Creates a list of `Choice` objects.
    ---
    Parameters:
        `choices -> tuple[str, ...]`: The names of the choices that are printed.
        
        `default_choice -> int`: An index to a choice to mark as the default one.
        
        `values -> tuple[object, ...]`: The values of the choices that are returned when selected. Defaults to the `choices` names.
        
        `shortcuts -> tuple[str, ...]`: A tuple of characters used as shortcuts for the choices. Defaults `range(1, len(choices))`.
    """
    
    return [Choice(title=[("class:normal2", choice_name)], checked=default_choice == i,
                   value=None if not values else values[i], shortcut_key=str(i+1) if not shortcuts else shortcuts[i])
            for i, choice_name in enumerate(choices)]


def selectionQuestion(message: str, choices: tuple[str, ...], default_choice=0, values: tuple[object, ...]=(), shortcuts: tuple[str, ...]=(), shortcuts_instruction_msg: str="") -> object:
    """
    Description:
        Prompt the user to select a choice and return its corresponding value.
    ---
    Parameters:
        `message -> str`: A custom message to display as the prompt question.
            
        `choices -> tuple[str, ...]`: A list containing the names of the choices.
        
        `default_choice -> int`: An index to a choice to mark as the default one.
        
        `values -> tuple[object, ...]`: The values of the choices that are returned when selected. Defaults to the `choices` names.
        
        `shortcuts -> tuple[str, ...]`: A tuple of characters used as shortcuts for the choices. Defaults `range(1, len(choices))`.
        
        `shortcuts_instruction_msg -> str`: A message to display after the prompt question (for control hints).
    
    ---
    Returns:
        `object` => The value associated with the selected choice.
    """
    
    generatedChoices = createChoices(choices, default_choice, values, shortcuts)
    if not shortcuts_instruction_msg:
        shortcuts_instruction_msg = "(Use up/down arrows and number keys to navigate)"
    # else:
        # shortcuts_instruction_msg = f"(Use up/down arrow keys and {shortcuts_instruction_msg} buttons to navigate)"
    
    output = questionary.select(message, choices=generatedChoices, style=customStyle, qmark="➥", pointer="➤",
                                default=generatedChoices[default_choice], use_shortcuts=True,
                                show_selected=False, use_indicator=False, instruction=shortcuts_instruction_msg).ask()
    
    return generatedChoices[default_choice].value if output is None else output


def yesNoQuestion(message: str, default_choice=0, values=(0, 1), choices=("No", "Yes"), shortcuts=("n", "y")) -> object:
    """
    Description:
        Prompt the user to select from two choices and return the value associated with the selected choice.
    ---
    Parameters:
        `message -> str`: A custom message to display as the prompt question.
            
        `choices -> tuple[str, ...]`: A list containing the names of the choices.
        
        `default_choice -> int`: An index to a choice to mark as the default one.
        
        `values -> tuple`: The values of the choices that are returned when selected. Defaults to the `choices` names.
        
        `shortcuts -> tuple[str, ...]`: A tuple of characters used as shortcuts for the choices. Defaults `range(1, len(choices))`.
    
    ---
    Returns:
        `object` => The value associated with the selected choice.
    """
    
    helpShortcuts = ("UP/down" if not default_choice else "up/DOWN") + " arrows and "
    helpShortcuts += f"{str(shortcuts[0]).upper()}/{shortcuts[1]}" if not default_choice else f"{shortcuts[0]}/{str(shortcuts[1]).upper()}"
    
    return selectionQuestion(message, choices, default_choice, values, shortcuts, f"(Use {helpShortcuts} keys to navigate)")
