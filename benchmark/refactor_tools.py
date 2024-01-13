#!/usr/bin/env python

import ast
import os
import shutil
import sys
from pathlib import Path

from aider.dump import dump  # noqa: F401


class ParentNodeTransformer(ast.NodeTransformer):
    """
    This transformer sets the 'parent' attribute on each node.
    """

    def generic_visit(self, node):
        for child in ast.iter_child_nodes(node):
            child.parent = node
        return super(ParentNodeTransformer, self).generic_visit(node)


def verify_full_func_at_top_level(tree, func, func_children):
    func_nodes = [
        item for item in ast.walk(tree) if isinstance(item, ast.FunctionDef) and item.name == func
    ]
    assert func_nodes, f"Function {func} not found"

    for func_node in func_nodes:
        if not isinstance(func_node.parent, ast.Module):
            continue

        num_children = sum(1 for _ in ast.walk(func_node))
        pct_diff_children = abs(num_children - func_children) * 100 / func_children
        assert (
            pct_diff_children < 10
        ), f"Old method had {func_children} children, new method has {num_children}"
        return

    assert False, f"{func} is not a top level function"


def verify_old_class_children(tree, old_class, old_class_children):
    node = next(
        (
            item
            for item in ast.walk(tree)
            if isinstance(item, ast.ClassDef) and item.name == old_class
        ),
        None,
    )
    assert node is not None, f"Old class {old_class} not found"

    num_children = sum(1 for _ in ast.walk(node))

    pct_diff_children = abs(num_children - old_class_children) * 100 / old_class_children
    assert (
        pct_diff_children < 10
    ), f"Old class had {old_class_children} children, new class has {num_children}"


def verify_refactor(fname, func, func_children, old_class, old_class_children):
    with open(fname, "r") as file:
        file_contents = file.read()
    tree = ast.parse(file_contents)
    ParentNodeTransformer().visit(tree)  # Set parent attribute for all nodes

    verify_full_func_at_top_level(tree, func, func_children)

    verify_old_class_children(tree, old_class, old_class_children - func_children)


############################


class SelfUsageChecker(ast.NodeVisitor):
    def __init__(self):
        self.non_self_methods = []
        self.parent_class_name = None
        self.num_class_children = 0

    def visit_FunctionDef(self, node):
        # Check if the first argument is 'self' and if it's not used
        if node.args.args and node.args.args[0].arg == "self":
            self_used = any(
                isinstance(expr, ast.Name) and expr.id == "self"
                for stmt in node.body
                for expr in ast.walk(stmt)
            )
            super_used = any(
                isinstance(expr, ast.Name) and expr.id == "super"
                for stmt in node.body
                for expr in ast.walk(stmt)
            )
            if not self_used and not super_used:
                # Calculate the number of child nodes in the function
                num_child_nodes = sum(1 for _ in ast.walk(node))
                res = (
                    self.parent_class_name,
                    node.name,
                    self.num_class_children,
                    num_child_nodes,
                )
                self.non_self_methods.append(res)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.parent_class_name = node.name
        self.num_class_children = sum(1 for _ in ast.walk(node))
        self.generic_visit(node)


def find_python_files(path):
    if os.path.isfile(path) and path.endswith(".py"):
        return [path]
    elif os.path.isdir(path):
        py_files = []
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    py_files.append(full_path)
        return py_files
    else:
        return []


def find_non_self_methods(path):
    python_files = find_python_files(path)
    non_self_methods = []
    for filename in python_files:
        with open(filename, "r") as file:
            try:
                node = ast.parse(file.read(), filename=filename)
            except:
                pass
            checker = SelfUsageChecker()
            checker.visit(node)
            for method in checker.non_self_methods:
                non_self_methods.append([filename] + list(method))

    return non_self_methods


def process(entry):
    fname, class_name, method_name, class_children, method_children = entry
    if method_children > class_children / 2:
        return
    if method_children < 250:
        return

    fname = Path(fname)
    if "test" in fname.stem:
        return

    print(f"{fname} {class_name} {method_name} {class_children} {method_children}")

    dname = Path("tmp.benchmarks/refactor-benchmark-spyder")
    dname.mkdir(exist_ok=True)

    dname = dname / f"{fname.stem}_{class_name}_{method_name}"
    dname.mkdir(exist_ok=True)

    shutil.copy(fname, dname / fname.name)

    docs_dname = dname / ".docs"
    docs_dname.mkdir(exist_ok=True)

    ins_fname = docs_dname / "instructions.md"
    ins_fname.write_text(f"""# Refactor {class_name}.{method_name}

Refactor the `{method_name}` method in the `{class_name}` class to be a stand alone, top level function.
Name the new function `{method_name}`, exactly the same name as the existing method.
Update any existing `self.{method_name}` calls to work with the new `{method_name}` function.
""")  # noqa: E501

    test_fname = dname / f"{fname.stem}_test.py"
    test_fname.write_text(f"""
import unittest
from benchmark.refactor_tools import verify_refactor
from pathlib import Path

class TheTest(unittest.TestCase):
    def test_{method_name}(self):
        fname = Path(__file__).parent / "{fname.name}"
        method = "{method_name}"
        method_children = {method_children}

        class_name = "{class_name}"
        class_children = {class_children}

        verify_refactor(fname, method, method_children, class_name, class_children)

if __name__ == "__main__":
    unittest.main()
""")


def main(paths):
    for path in paths:
        methods = find_non_self_methods(path)
        # methods = sorted(methods, key=lambda x: x[4])

        for method in methods:
            process(method)


if __name__ == "__main__":
    main(sys.argv[1:])
