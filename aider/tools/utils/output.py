import json
import re


def print_tool_response(coder, mcp_server, tool_response):
    """
    Format the output for display.
    Prints a Header to identify the tool, a body for the relevant information
    for the user and a footer for verbose information

    Args:
        coder: An instance of base_coder
        mcp_server: An mcp server instance
        tool_response: a tool_response dictionary
    """
    tool_header(coder=coder, mcp_server=mcp_server, tool_response=tool_response)
    tool_body(coder=coder, tool_response=tool_response)
    tool_footer(coder=coder, tool_response=tool_response)


def tool_header(coder, mcp_server, tool_response):
    """
    Prints the header for the tool call output

    Args:
        coder: An instance of base_coder
        mcp_server: An mcp server instance
        tool_response: a tool_response dictionary
    """
    color_start, color_end = color_markers(coder)

    coder.io.tool_output(
        f"{color_start}Tool Call:{color_end} {mcp_server.name} • {tool_response.function.name}"
    )


def tool_body(coder, tool_response):
    """
    Prints the output body of a tool call as the raw json returned from the model

    Args:
        coder: An instance of base_coder
        tool_response: a tool_response dictionary
    """
    color_start, color_end = color_markers(coder)

    # Parse and format arguments as headers with values
    if tool_response.function.arguments:
        # For non-replace tools, show raw arguments
        raw_args = tool_response.function.arguments
        coder.io.tool_output(f"{color_start}Arguments:{color_end} {raw_args}")


def tool_body_unwrapped(coder, tool_response):
    """
    Prints the output body of a tool call with the argument
    and content sections separated

    Args:
        coder: An instance of base_coder
        tool_response: a tool_response dictionary
    """

    color_start, color_end = color_markers(coder)

    try:
        args_dict = json.loads(tool_response.function.arguments)
        first_key = True
        for key, value in args_dict.items():
            # Convert explicit \\n sequences to actual newlines using regex
            # Only match \\n that is not preceded by any other backslashes
            if isinstance(value, str):
                value = re.sub(r"(?<!\\)\\n", "\n", value)
            # Add extra newline before first key/header
            if first_key:
                coder.io.tool_output("\n")
                first_key = False
            coder.io.tool_output(f"{color_start}{key}:{color_end}")
            # Split the value by newlines and output each line separately
            if isinstance(value, str):
                for line in value.split("\n"):
                    coder.io.tool_output(f"{line}")
            else:
                coder.io.tool_output(f"{str(value)}")
            coder.io.tool_output("")
    except json.JSONDecodeError:
        # If JSON parsing fails, show raw arguments
        raw_args = tool_response.function.arguments
        coder.io.tool_output(f"{color_start}Arguments:{color_end} {raw_args}")


def tool_footer(coder, tool_response):
    """
    Prints the output footer of a tool call, generally a new line
    But can include id's if ran in verbose mode

    Args:
        coder: An instance of base_coder
        tool_response: a tool_response dictionary
    """
    if coder.verbose:
        coder.io.tool_output(f"Tool ID: {tool_response.id}")
        coder.io.tool_output(f"Tool type: {tool_response.type}")

    coder.io.tool_output("\n")


def color_markers(coder):
    """
    Rich.console color markers

    Args:
        coder: An instance of base_coder
    """
    color_start = "[blue]" if coder.pretty else ""
    color_end = "[/blue]" if coder.pretty else ""

    return color_start, color_end
