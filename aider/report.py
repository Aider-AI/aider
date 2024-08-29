import os
import sys
import traceback
import urllib.parse
import webbrowser

from aider import __version__


def report_github_issue(issue_text, title=None):
    """
    Compose a URL to open a new GitHub issue with the given text prefilled,
    and attempt to launch it in the default web browser.

    :param issue_text: The text of the issue to file
    :param title: The title of the issue (optional)
    :return: None
    """
    version_info = f"Aider version: {__version__}\n\n"
    issue_text = version_info + issue_text
    base_url = "https://github.com/paul-gauthier/aider/issues/new"
    params = {"body": issue_text}
    if title is None:
        title = "Bug report"
    params["title"] = title
    issue_url = f"{base_url}?{urllib.parse.urlencode(params)}"

    print(f"\n# {title}\n")
    print(issue_text.strip())
    print()
    print("Please consider reporting this bug to help improve aider!")
    prompt = "Report this as a GitHub Issue using your browser? (Y/n) "
    confirmation = input(prompt).strip().lower()

    yes = not confirmation or confirmation.startswith("y")
    if not yes:
        return

    print("Attempting to open the issue URL in your default web browser...")
    try:
        if webbrowser.open(issue_url):
            print("Browser window should be opened.")
            return
    except Exception:
        pass

    print()
    print("Unable to open browser window automatically.")
    print("Please use this URL to file a GitHub issue:")
    print()
    print(issue_url)


def exception_handler(exc_type, exc_value, exc_traceback):
    # We don't want any more exceptions
    sys.excepthook = None

    # Format the traceback
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)

    # Replace full paths with basenames in the traceback
    tb_lines_with_basenames = []
    for line in tb_lines:
        if "File " in line:
            parts = line.split('"')
            if len(parts) > 1:
                full_path = parts[1]
                basename = os.path.basename(full_path)
                line = line.replace(full_path, basename)
        tb_lines_with_basenames.append(line)

    tb_text = "".join(tb_lines_with_basenames)

    # Find the first non-frozen frame
    while exc_traceback:
        filename = exc_traceback.tb_frame.f_code.co_filename
        if not filename.startswith("<frozen "):
            break
        exc_traceback = exc_traceback.tb_next

    # Get the filename and line number
    line_number = exc_traceback.tb_lineno
    basename = os.path.basename(filename)

    # Get the exception type name
    exception_type = exc_type.__name__

    # Prepare the issue text
    issue_text = f"An uncaught exception occurred:\n\n```\n{tb_text}\n```"

    # Prepare the title
    title = f"Uncaught {exception_type} in {basename} line {line_number}"

    # Report the issue
    report_github_issue(issue_text, title=title)

    # Call the default exception handler
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def report_uncaught_exceptions():
    """
    Set up the global exception handler to report uncaught exceptions.
    """
    sys.excepthook = exception_handler


def main():
    report_uncaught_exceptions()
    raise ValueError("boo")

    title = None
    if len(sys.argv) > 2:
        # Use the first command-line argument as the title and the second as the issue text
        title = sys.argv[1]
        issue_text = sys.argv[2]
    elif len(sys.argv) > 1:
        # Use the first command-line argument as the issue text
        issue_text = sys.argv[1]
    else:
        # Read from stdin if no argument is provided
        print("Enter the issue title (optional, press Enter to skip):")
        title = input().strip()
        if not title:
            title = None
        print("Enter the issue text (Ctrl+D to finish):")
        issue_text = sys.stdin.read().strip()

    report_github_issue(issue_text, title)


if __name__ == "__main__":
    main()
