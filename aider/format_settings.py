# Environment variable names that hold credentials rather than plain config
SECRET_ENV_SUFFIXES = ("_API_KEY", "_KEY", "_TOKEN", "_SECRET", "_PASSWORD")


def is_secret_env_name(name):
    """Return True if an environment variable name looks like it holds a credential."""
    name = (name or "").strip().upper()
    if not name:
        return False
    return name.endswith(SECRET_ENV_SUFFIXES) or "TOKEN" in name or "SECRET" in name


def get_sensitive_values(args):
    """Collect the credentials that may show up in logged text.

    Covers the dedicated --openai-api-key / --anthropic-api-key switches as well
    as the generic --api-key provider=<key> switch and --set-env VAR=<value>
    assignments for credential-looking variables.
    """
    values = []

    for attr in ("openai_api_key", "anthropic_api_key"):
        value = getattr(args, attr, None)
        if value:
            values.append(value)

    for setting in getattr(args, "api_key", None) or []:
        _, _, value = str(setting).partition("=")
        if value.strip():
            values.append(value.strip())

    for setting in getattr(args, "set_env", None) or []:
        name, _, value = str(setting).partition("=")
        if is_secret_env_name(name) and value.strip():
            values.append(value.strip())

    # Replace the longest values first so overlapping secrets are fully redacted
    return sorted(set(values), key=len, reverse=True)


def scrub_sensitive_info(args, text):
    # Replace sensitive information with last 4 characters
    if not text:
        return text

    for value in get_sensitive_values(args):
        text = text.replace(value, f"...{value[-4:]}")

    return text


def format_settings(parser, args):
    show = scrub_sensitive_info(args, parser.format_values())
    # clean up the headings for consistency w/ new lines
    heading_env = "Environment Variables:"
    heading_defaults = "Defaults:"
    if heading_env in show:
        show = show.replace(heading_env, "\n" + heading_env)
        show = show.replace(heading_defaults, "\n" + heading_defaults)
    show += "\n"
    show += "Option settings:\n"
    for arg, val in sorted(vars(args).items()):
        if val:
            val = scrub_sensitive_info(args, str(val))
        show += f"  - {arg}: {val}\n"  # noqa: E221
    return show
