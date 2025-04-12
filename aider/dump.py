import json
import traceback


def cvt(s):
    if isinstance(s, str):
        return s
    try:
        return json.dumps(s, indent=4)
    except TypeError:
        return str(s)


def dump(*vals):
    # http://docs.python.org/library/traceback.html
    stack = traceback.extract_stack()
    vars = stack[-2][3]

    # strip away the call to dump()
    vars = "(".join(vars.split("(")[1:])
    vars = ")".join(vars.split(")")[:-1])

    vals = [cvt(v) for v in vals]
    has_newline = sum(1 for v in vals if "\n" in v)
    if has_newline:
        print("%s:" % vars)
        print(", ".join(vals))
    else:
        print("%s:" % vars, ", ".join(vals))
