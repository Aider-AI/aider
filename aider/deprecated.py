def add_deprecated_model_args(parser, group):
    """Add deprecated model shortcut arguments to the argparse parser."""
    opus_model = "claude-3-opus-20240229"
    group.add_argument(
        "--opus",
        action="store_true",
        help=f"Use {opus_model} model for the main chat (deprecated, use --model)",
        default=False,
    )
    sonnet_model = "anthropic/claude-3-7-sonnet-20250219"
    group.add_argument(
        "--sonnet",
        action="store_true",
        help=f"Use {sonnet_model} model for the main chat (deprecated, use --model)",
        default=False,
    )
    haiku_model = "claude-3-5-haiku-20241022"
    group.add_argument(
        "--haiku",
        action="store_true",
        help=f"Use {haiku_model} model for the main chat (deprecated, use --model)",
        default=False,
    )
    gpt_4_model = "gpt-4-0613"
    group.add_argument(
        "--4",
        "-4",
        action="store_true",
        help=f"Use {gpt_4_model} model for the main chat (deprecated, use --model)",
        default=False,
    )
    gpt_4o_model = "gpt-4o"
    group.add_argument(
        "--4o",
        action="store_true",
        help=f"Use {gpt_4o_model} model for the main chat (deprecated, use --model)",
        default=False,
    )
    gpt_4o_mini_model = "gpt-4o-mini"
    group.add_argument(
        "--mini",
        action="store_true",
        help=f"Use {gpt_4o_mini_model} model for the main chat (deprecated, use --model)",
        default=False,
    )
    gpt_4_turbo_model = "gpt-4-1106-preview"
    group.add_argument(
        "--4-turbo",
        action="store_true",
        help=f"Use {gpt_4_turbo_model} model for the main chat (deprecated, use --model)",
        default=False,
    )
    gpt_3_model_name = "gpt-3.5-turbo"
    group.add_argument(
        "--35turbo",
        "--35-turbo",
        "--3",
        "-3",
        action="store_true",
        help=f"Use {gpt_3_model_name} model for the main chat (deprecated, use --model)",
        default=False,
    )
    deepseek_model = "deepseek/deepseek-chat"
    group.add_argument(
        "--deepseek",
        action="store_true",
        help=f"Use {deepseek_model} model for the main chat (deprecated, use --model)",
        default=False,
    )
    o1_mini_model = "o1-mini"
    group.add_argument(
        "--o1-mini",
        action="store_true",
        help=f"Use {o1_mini_model} model for the main chat (deprecated, use --model)",
        default=False,
    )
    o1_preview_model = "o1-preview"
    group.add_argument(
        "--o1-preview",
        action="store_true",
        help=f"Use {o1_preview_model} model for the main chat (deprecated, use --model)",
        default=False,
    )


def handle_deprecated_model_args(args, io):
    """Handle deprecated model shortcut arguments and provide appropriate warnings."""
    # Define model mapping
    model_map = {
        "opus": "claude-3-opus-20240229",
        "sonnet": "anthropic/claude-3-7-sonnet-20250219",
        "haiku": "claude-3-5-haiku-20241022",
        "4": "gpt-4-0613",
        "4o": "gpt-4o",
        "mini": "gpt-4o-mini",
        "4_turbo": "gpt-4-1106-preview",
        "35turbo": "gpt-3.5-turbo",
        "deepseek": "deepseek/deepseek-chat",
        "o1_mini": "o1-mini",
        "o1_preview": "o1-preview",
    }

    # Check if any deprecated args are used
    for arg_name, model_name in model_map.items():
        arg_name_clean = arg_name.replace("-", "_")
        if hasattr(args, arg_name_clean) and getattr(args, arg_name_clean):
            # Find preferred name to display in warning
            from aider.models import MODEL_ALIASES

            display_name = model_name
            # Check if there's a shorter alias for this model
            for alias, full_name in MODEL_ALIASES.items():
                if full_name == model_name:
                    display_name = alias
                    break

            # Show the warning
            io.tool_warning(
                f"The --{arg_name.replace('_', '-')} flag is deprecated and will be removed in a"
                f" future version. Please use --model {display_name} instead."
            )

            # Set the model
            if not args.model:
                args.model = model_name
            break
