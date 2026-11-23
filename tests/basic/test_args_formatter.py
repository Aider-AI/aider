import argparse

import configargparse
import pytest

from aider.args_formatter import DotEnvFormatter, YamlHelpFormatter


@pytest.mark.parametrize("formatter", [DotEnvFormatter, YamlHelpFormatter])
@pytest.mark.parametrize("default", [0, 2, 0.5, -1])
def test_numeric_defaults(formatter, default):
    parser = configargparse.ArgumentParser(formatter_class=formatter)
    parser.add_argument("--limit", type=type(default), default=default, env_var="AIDER_LIMIT")
    output = argparse.ArgumentParser.format_help(parser)
    expected = f"#AIDER_LIMIT={default}" if formatter is DotEnvFormatter else f"#limit: {default}"
    assert expected in output


@pytest.mark.parametrize("formatter", [DotEnvFormatter, YamlHelpFormatter])
@pytest.mark.parametrize("default", [True, False])
def test_boolean_defaults(formatter, default):
    parser = configargparse.ArgumentParser(formatter_class=formatter)
    parser.add_argument(
        "--enabled", action=argparse.BooleanOptionalAction, default=default, env_var="AIDER_ENABLED"
    )
    output = argparse.ArgumentParser.format_help(parser)
    value = str(default).lower()
    expected = f"#AIDER_ENABLED={value}" if formatter is DotEnvFormatter else f"#enabled: {value}"
    assert expected in output
