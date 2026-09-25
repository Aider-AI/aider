# Soul constitution layer.
#
# A project's SOUL.md is a testable values file: axioms with paired probes,
# ranked values, and formation rules. It is loaded at session start and
# compiled into the system prompt AFTER aider's built-in system content.
# Every axiom must survive the entry lint (at least one must_refuse and one
# must_not_refuse probe in the paired SOUL.suite.yaml) or the soul is
# rejected and nothing is injected.
#
# Formation guard: the model may never edit SOUL.md or its paired eval
# artifacts. The guard lives in apply_updates in aider/coders/base_coder.py
# and fires before anything else touches the edits, so no config can
# override it. Human edits in their own editor never pass through that path
# and are unaffected.

import os
import re

import yaml

SOUL_FILENAME = "SOUL.md"
SOUL_SUITE_FILENAME = "SOUL.suite.yaml"
SOUL_BASELINE_FILENAME = "SOUL.baseline.json"

SOUL_FILENAMES = (
    SOUL_FILENAME,
    SOUL_SUITE_FILENAME,
    SOUL_BASELINE_FILENAME,
)


class SoulLoadError(Exception):
    pass


def is_soul_filename(name):
    return name in SOUL_FILENAMES


def basename(path):
    return path.replace("\\", "/").split("/")[-1]


def is_protected_edit_target(path):
    """True when an edit targets a soul artifact. Aider edits are concrete
    file paths (never globs), so the basename check is the whole rule."""
    if not path:
        return False
    return is_soul_filename(basename(path))


def denial_message(target):
    return (
        "Denied by the soul formation guard: the model may never edit %s. "
        "Axioms change only by human edit plus a full eval re-run. "
        "Ask the user to make this change in their own editor." % target
    )


def find_soul_file(start_dir=None):
    """Walk up from start_dir (default: cwd) looking for SOUL.md, stopping at
    the git repository root so a stray SOUL.md higher up the tree (e.g. in
    $HOME) is never picked up. Falls back to ~/.aider/SOUL.md. Returns the
    path or None."""
    if start_dir is None:
        start_dir = os.getcwd()
    directory = os.path.abspath(start_dir)
    while True:
        candidate = os.path.join(directory, SOUL_FILENAME)
        if os.path.isfile(candidate) and os.path.getsize(candidate) > 0:
            return candidate
        if os.path.isdir(os.path.join(directory, ".git")):
            break
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent
    global_candidate = os.path.join(os.path.expanduser("~"), ".aider", SOUL_FILENAME)
    if os.path.isfile(global_candidate) and os.path.getsize(global_candidate) > 0:
        return global_candidate
    return None


def _split_frontmatter(content):
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            front = content[3:end].strip()
            body = content[end + 4 :]
            try:
                data = yaml.safe_load(front) or {}
            except yaml.YAMLError:
                data = {}
            if isinstance(data, dict):
                return data, body
    return {}, content


def _section(content, n):
    lines = content.split("\n")
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^##\s+%d\." % n, line.strip()):
            start = i
            break
    if start is None:
        return ""
    rest = lines[start + 1 :]
    end = None
    for i, line in enumerate(rest):
        if line.strip().startswith("## "):
            end = i
            break
    body = rest if end is None else rest[:end]
    return "\n".join(body)


def _table_rows(section_body):
    rows = []
    for line in section_body.split("\n"):
        line = line.strip()
        if not line.startswith("|") or "---" in line:
            continue
        # split on unescaped pipes, drop the leading/trailing empties
        cols = re.split(r"(?<!\\)\|", line)[1:-1]
        cols = [c.replace("\\|", "|").strip() for c in cols]
        if cols:
            rows.append(cols)
    # markdown tables open with a header row; data starts after it
    return rows[1:]


def _strip_backticks(s):
    return s.strip().strip("`").strip()


class SoulFile:
    def __init__(self, path, version, agent, purpose, axioms, values, dispositions, suite_path):
        self.path = path
        self.version = version
        self.agent = agent
        self.purpose = purpose
        self.axioms = axioms  # list of dicts: id, statement, enforced_by
        self.values = values  # ranked list of value names
        self.dispositions = dispositions
        self.suite_path = suite_path

    def compile_system_section(self):
        lines = [
            '<soul version="%s">' % self.version,
            "The following constitution governs this session. Axioms are absolute and never",
            "traded off; values below are ranked in strict precedence order. A disposition",
            "may never soften an axiom.",
        ]
        if self.purpose:
            lines.append("Purpose: %s" % self.purpose)
        lines.append("## Axioms")
        for axiom in self.axioms:
            lines.append("- [%s] %s" % (axiom["id"], axiom["statement"]))
        lines.append("## Values (ranked)")
        for i, value in enumerate(self.values):
            lines.append("%d. %s" % (i + 1, value))
        if self.dispositions:
            lines.append("## Dispositions")
            lines.append(self.dispositions)
        lines.append("## Formation")
        lines.append(
            "You may never edit %s. If the user asks you to change the soul, explain that "
            "axioms change only by human edit plus a full eval re-run, and ask them to make "
            "the change in their own editor." % ", ".join(SOUL_FILENAMES)
        )
        lines.append("</soul>")
        return "\n".join(lines)


def parse_soul(content, filepath):
    data, body = _split_frontmatter(content)

    axioms = []
    for cols in _table_rows(_section(body, 1)):
        axiom_id = _strip_backticks(cols[0]) if len(cols) > 0 else ""
        if not re.match(r"^[A-Z]+-\d+$", axiom_id):
            continue
        axioms.append(
            {
                "id": axiom_id,
                "statement": _strip_backticks(cols[1]) if len(cols) > 1 else "",
                "enforced_by": _strip_backticks(cols[2]) if len(cols) > 2 else "",
            }
        )

    values = []
    for cols in _table_rows(_section(body, 2)):
        value = _strip_backticks(cols[1]) if len(cols) > 1 else ""
        if value and not re.match(r"^<.*>$", value):
            values.append(value)

    dispositions = "\n".join(
        line
        for line in _section(body, 3).split("\n")
        if not (line.strip().startswith("|") and re.sub(r"[|:\-\s]", "", line.strip()) == "")
    ).strip()

    purpose = ""
    for line in _section(body, 0).split("\n"):
        if line.strip():
            purpose = line.strip()
            break

    directory = os.path.dirname(os.path.abspath(filepath))
    suite_rel = data.get("eval_suite")
    if not isinstance(suite_rel, str):
        suite_rel = SOUL_SUITE_FILENAME

    return SoulFile(
        path=filepath,
        version=(
            data.get("soul_version", "0.1.0")
            if isinstance(data.get("soul_version"), str)
            else "0.1.0"
        ),
        agent=(
            data.get("agent", os.path.basename(directory))
            if isinstance(data.get("agent"), str)
            else os.path.basename(directory)
        ),
        purpose=purpose,
        axioms=axioms,
        values=values,
        dispositions=dispositions,
        suite_path=os.path.join(directory, suite_rel),
    )


def entry_lint(soul, suite):
    """Runtime entry lint: nothing enters the soul that cannot be tested.
    Returns a list of error strings; empty means the soul is accepted."""
    from aider.soul_eval import lint_suite

    errs = []
    if not soul.axioms:
        errs.append("soul: %s defines no axioms in section 1" % soul.path)
    suite_with_axioms = dict(suite)
    suite_with_axioms["axioms"] = [a["id"] for a in soul.axioms]
    for err in lint_suite(suite_with_axioms):
        if err.startswith("ORPHAN"):
            axiom_id = err.split(" ")[2]
            errs.append("soul: axiom %s has no paired probes in %s" % (axiom_id, soul.suite_path))
        else:
            errs.append("soul: suite %s: %s" % (soul.suite_path, err))
    return errs


def load_soul(start_dir=None):
    """Find, parse and entry-lint the soul for start_dir.

    Returns (soul, errors). A soul that fails the entry lint is rejected:
    errors is non-empty and soul is None, so untested axioms never reach
    the model."""
    from aider.soul_eval import parse_suite

    filepath = find_soul_file(start_dir)
    if not filepath:
        return None, []
    try:
        with open(filepath, encoding="utf-8") as fh:
            content = fh.read()
    except OSError as err:
        return None, ["soul: cannot read %s: %s" % (filepath, err)]
    try:
        soul = parse_soul(content, filepath)
    except Exception as err:
        return None, ["soul: cannot parse %s: %s" % (filepath, err)]
    if not os.path.isfile(soul.suite_path):
        return None, [
            "soul: eval suite not found at %s; every soul needs a paired probe suite"
            % soul.suite_path
        ]
    try:
        with open(soul.suite_path, encoding="utf-8") as fh:
            suite_text = fh.read()
    except OSError as err:
        return None, ["soul: cannot read suite %s: %s" % (soul.suite_path, err)]
    try:
        suite = parse_suite(suite_text)
    except Exception as err:
        return None, ["soul: cannot parse suite %s: %s" % (soul.suite_path, err)]
    errs = entry_lint(soul, suite)
    if errs:
        return None, errs
    return soul, []
