def generate_bash_completion(argparser):
    """
    Generate a bash completion script for the aider command-line tool.
    """
    script_name = "aider"

    commands = []
    one_arg_commands = []
    file_commands = {}
    choice_commands = {}

    # Hardcoded list of ISO 639-1 language codes
    iso_639_1_codes = [
        "aa", "ab", "ae", "af", "ak", "am", "an", "ar", "as", "av", "ay", "az",
        "ba", "be", "bg", "bh", "bi", "bm", "bn", "bo", "br", "bs", "ca", "ce",
        "ch", "co", "cr", "cs", "cu", "cv", "cy", "da", "de", "dv", "dz", "ee",
        "el", "en", "eo", "es", "et", "eu", "fa", "ff", "fi", "fj", "fo", "fr",
        "fy", "ga", "gd", "gl", "gn", "gu", "gv", "ha", "he", "hi", "ho", "hr",
        "ht", "hu", "hy", "hz", "ia", "id", "ie", "ig", "ii", "ik", "io", "is",
        "it", "iu", "ja", "jv", "ka", "kg", "ki", "kj", "kk", "kl", "km", "kn",
        "ko", "kr", "ks", "ku", "kv", "kw", "ky", "la", "lb", "lg", "li", "ln",
        "lo", "lt", "lu", "lv", "mg", "mh", "mi", "mk", "ml", "mn", "mr", "ms",
        "mt", "my", "na", "nb", "nd", "ne", "ng", "nl", "nn", "no", "nr", "nv",
        "ny", "oc", "oj", "om", "or", "os", "pa", "pi", "pl", "ps", "pt", "qu",
        "rm", "rn", "ro", "ru", "rw", "sa", "sc", "sd", "se", "sg", "si", "sk",
        "sl", "sm", "sn", "so", "sq", "sr", "ss", "st", "su", "sv", "sw", "ta",
        "te", "tg", "th", "ti", "tk", "tl", "tn", "to", "tr", "ts", "tt", "tw",
        "ty", "ug", "uk", "ur", "uz", "ve", "vi", "vo", "wa", "wo", "xh", "yi",
        "yo", "za", "zh", "zu",
    ]

    for action in argparser._actions:  # pylint: disable=protected-access
        if action.option_strings:
            command = " ".join(action.option_strings)

            # Determine nargs based on the given conditions
            if action.nargs is not None:
                nargs = action.nargs
            elif action.metavar is None:
                if action.type is not None:
                    nargs = 1
                else:
                    nargs = 0
            elif isinstance(action.metavar, str):
                nargs = 1
            elif isinstance(action.metavar, list):
                nargs = len(action.metavar)
            else:
                nargs = 0  # Default case if none of the conditions match

            if nargs == 0:
                commands.append(command)
            elif nargs == 1 or (
                isinstance(action.metavar, str) and not action.metavar.endswith("FILE")
            ):
                one_arg_commands.append(f"{command}")

            if (
                action.metavar
                and isinstance(action.metavar, str)
                and action.metavar.endswith("FILE")
            ):
                file_commands[command] = action.metavar

            if action.choices:
                choice_commands[command] = action.choices

    # Define the list of choices for --edit-mode and --chat-mode
    edit_mode_choices = [
        "help", "ask", "diff", "diff-fenced", "whole", "patch", "udiff",    
        "architect", "editor-diff", "editor-whole", "editor-diff-fenced",   
        "context"
    ]

    # Generate the code for the options with choices
    choice_commands_str = "\n".join(
        [
            '{}) COMPREPLY=( $(compgen -W "{}" -- ${{cur}}) );;'.format(cmd, " ".join(choices))
            for cmd, choices in choice_commands.items()
        ]
    )

    completion_script = f"""
_aider_completion() {{
    local cur prev words cword
    _init_completion || return

    local commands=(
        {" ".join(commands)}
        {" ".join(one_arg_commands)}
    )

    local one_arg_commands=(
        {" ".join(one_arg_commands)}
    )

    local file_commands=(
        {" ".join(file_commands.keys())}
    )

    local choice_commands=(
        {" ".join(choice_commands.keys())}
    )

    if [[ ${{#words[@]}} -ge 4 ]]; then
        prev=${{words[-3]}}
        if [[ " ${{two_arg_commands[*]}} " =~ " ${{prev}} " ]]; then
            # COMPREPLY=( "Enter VALUE2" )
            return 0
        fi
    fi

    if [[ ${{#words[@]}} -ge 3 ]]; then
        prev=${{words[-2]}}

        case "$prev" in
            {choice_commands_str}
            --edit-mode|--chat-mode)
                COMPREPLY=( $(compgen -W "{' '.join(edit_mode_choices)}" -- ${{cur}}) )
                ;;
            --voice-language)
                COMPREPLY=( $(compgen -W "{' '.join(iso_639_1_codes)}" -- ${{cur}}) )
                ;;
        esac

        if [[ " ${{file_commands[*]}} " =~ " ${{prev}} " ]]; then
            _filedir
            return 0
        fi
        if [[ " ${{one_arg_commands[*]}} " =~ " ${{prev}} " ]]; then
            return 0
        fi
        if [[ " ${{two_arg_commands[*]}} " =~ " ${{prev}} " ]]; then
            return 0
        fi

    fi

    COMPREPLY=( $(compgen -W "${{commands[*]}}" -- ${{cur}}) )
    _filedir
    return 0
}}

complete -F _aider_completion {script_name}
complete -F _aider_completion ./{script_name}
"""

    print(completion_script)
