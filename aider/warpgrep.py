import os
import re
import shutil
import subprocess

import requests


class WarpGrepResult:
    def __init__(self, rel_path, start_line, end_line, content):
        self.rel_path = rel_path
        self.start_line = start_line
        self.end_line = end_line
        self.content = content


class WarpGrepClient:
    API_URL = "https://api.morphllm.com/v1/chat/completions"
    MODEL = "morph-warp-grep-v2"
    MAX_TURNS = 4
    MAX_CONTEXT_CHARS = 160000
    MAX_RG_LINES = 200
    MAX_READ_LINES = 800
    MAX_DIR_LINES = 200

    def __init__(self, api_key, root, get_tracked_files_fn, io):
        self.api_key = api_key
        self.root = root
        self.get_tracked_files = get_tracked_files_fn
        self.io = io

    def search(self, query):
        tracked_files = self.get_tracked_files()
        repo_structure = self._build_repo_structure(tracked_files)

        user_content = (
            f"<repo_structure>\n{repo_structure}\n</repo_structure>\n\n"
            f"<search_string>\n{query}\n</search_string>"
        )

        messages = [{"role": "user", "content": user_content}]
        context_chars = len(user_content)

        for turn in range(self.MAX_TURNS):
            response = self._call_api(messages)
            assistant_msg = response["choices"][0]["message"]["content"]
            messages.append({"role": "assistant", "content": assistant_msg})

            tool_calls = self._parse_tool_calls(assistant_msg)

            # Check for finish call
            for tc in tool_calls:
                if tc["function"] == "finish":
                    files_param = tc["params"].get("files", "")
                    return self._process_finish(files_param)

            if not tool_calls:
                # No tool calls and no finish, treat as done
                return []

            # Execute tool calls and build response
            results = []
            for tc in tool_calls:
                result = self._execute_tool_call(tc)
                results.append(result)

            tool_response = "\n\n".join(results)
            context_chars += len(assistant_msg) + len(tool_response)
            remaining = self.MAX_TURNS - turn - 1
            budget_pct = min(100, int(context_chars / self.MAX_CONTEXT_CHARS * 100))

            user_reply = (
                f"{tool_response}\n\n"
                f"You have used {turn + 1} turns and have {remaining} remaining.\n"
                f"<context_budget>{budget_pct}% "
                f"({context_chars}/{self.MAX_CONTEXT_CHARS} chars)</context_budget>"
            )
            messages.append({"role": "user", "content": user_reply})

        return []

    def _build_repo_structure(self, files):
        lines = []
        for f in sorted(files):
            lines.append(f)
        return "\n".join(lines)

    def _call_api(self, messages):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.MODEL,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 2048,
        }
        resp = requests.post(self.API_URL, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        return resp.json()

    def _parse_tool_calls(self, text):
        tool_calls = []
        pattern = r"<tool_call>\s*<function=(\w+)>(.*?)</function>\s*</tool_call>"
        for match in re.finditer(pattern, text, re.DOTALL):
            func_name = match.group(1)
            params_text = match.group(2)
            params = {}
            for param_match in re.finditer(
                r"<parameter=(\w+)>(.*?)</parameter>", params_text, re.DOTALL
            ):
                params[param_match.group(1)] = param_match.group(2).strip()
            tool_calls.append({"function": func_name, "params": params})
        return tool_calls

    def _execute_tool_call(self, tc):
        func = tc["function"]
        params = tc["params"]

        if func == "ripgrep":
            return self._exec_ripgrep(params)
        elif func == "read":
            return self._exec_read(params)
        elif func == "list_directory":
            return self._exec_list_directory(params)
        else:
            return f"<tool_response>\nUnknown tool: {func}\n</tool_response>"

    def _exec_ripgrep(self, params):
        pattern = params.get("pattern", "")
        path = params.get("path", ".")
        file_glob = params.get("glob", None)

        abs_path = os.path.join(self.root, path)

        rg_path = shutil.which("rg")
        if rg_path:
            cmd = [
                rg_path,
                "--line-number",
                "--no-heading",
                "--color",
                "never",
                "-C",
                "1",
            ]
            if file_glob:
                cmd.extend(["--glob", file_glob])
            cmd.extend([pattern, abs_path])

            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=30
                )
                output = result.stdout
            except (subprocess.TimeoutExpired, OSError):
                output = "ripgrep timed out or failed"
        else:
            # Fallback to python grep
            output = self._python_grep(pattern, abs_path)

        lines = output.split("\n")
        if len(lines) > self.MAX_RG_LINES:
            lines = lines[: self.MAX_RG_LINES]
            lines.append(f"... truncated ({len(lines)} lines shown)")
        output = "\n".join(lines)

        return f"<tool_response>\n{output}\n</tool_response>"

    def _python_grep(self, pattern, path):
        results = []
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
        except re.error:
            compiled = re.compile(re.escape(pattern), re.IGNORECASE)

        if os.path.isfile(path):
            files = [path]
        elif os.path.isdir(path):
            files = []
            for dirpath, _dirnames, filenames in os.walk(path):
                for fname in filenames:
                    files.append(os.path.join(dirpath, fname))
        else:
            return f"Path not found: {path}"

        for fpath in files:
            try:
                with open(fpath, "r", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if compiled.search(line):
                            rel = os.path.relpath(fpath, self.root)
                            results.append(f"{rel}:{i}:{line.rstrip()}")
                            if len(results) >= self.MAX_RG_LINES:
                                return "\n".join(results)
            except (OSError, UnicodeDecodeError):
                continue

        return "\n".join(results)

    def _exec_read(self, params):
        file_path = params.get("path", "")
        abs_path = os.path.join(self.root, file_path)

        try:
            with open(abs_path, "r", errors="ignore") as f:
                lines = f.readlines()
        except OSError as e:
            return f"<tool_response>\nError reading {file_path}: {e}\n</tool_response>"

        if len(lines) > self.MAX_READ_LINES:
            lines = lines[: self.MAX_READ_LINES]
            lines.append(f"... truncated at {self.MAX_READ_LINES} lines\n")

        numbered = []
        for i, line in enumerate(lines, 1):
            numbered.append(f"{i}|{line.rstrip()}")

        output = "\n".join(numbered)
        return f"<tool_response>\n{output}\n</tool_response>"

    def _exec_list_directory(self, params):
        path = params.get("path", ".")
        abs_path = os.path.join(self.root, path)

        if not os.path.isdir(abs_path):
            return f"<tool_response>\nNot a directory: {path}\n</tool_response>"

        lines = []
        self._tree(abs_path, "", lines)

        if len(lines) > self.MAX_DIR_LINES:
            lines = lines[: self.MAX_DIR_LINES]
            lines.append(f"... truncated at {self.MAX_DIR_LINES} entries")

        output = "\n".join(lines)
        return f"<tool_response>\n{output}\n</tool_response>"

    def _tree(self, dirpath, prefix, lines, depth=0):
        if depth > 5:
            return
        try:
            entries = sorted(os.listdir(dirpath))
        except OSError:
            return

        for entry in entries:
            if entry.startswith("."):
                continue
            full = os.path.join(dirpath, entry)
            lines.append(f"{prefix}{entry}")
            if os.path.isdir(full) and len(lines) < self.MAX_DIR_LINES:
                self._tree(full, prefix + "  ", lines, depth + 1)

    def _process_finish(self, files_param):
        results = []
        if not files_param.strip():
            return results

        for spec in files_param.split("\n"):
            spec = spec.strip()
            if not spec:
                continue
            result = self._parse_file_spec(spec)
            if result:
                results.extend(result)

        return results

    def _parse_file_spec(self, spec):
        # Format: path/to/file.py:1-15,45-80 or path/to/file.py:*
        if ":" not in spec:
            # Whole file
            return self._read_file_span(spec, None)

        path, ranges_str = spec.rsplit(":", 1)
        path = path.strip()

        if ranges_str.strip() == "*":
            return self._read_file_span(path, None)

        results = []
        for range_str in ranges_str.split(","):
            range_str = range_str.strip()
            if not range_str:
                continue
            if "-" in range_str:
                parts = range_str.split("-", 1)
                try:
                    start = int(parts[0])
                    end = int(parts[1])
                except ValueError:
                    continue
                spans = self._read_file_span(path, (start, end))
                if spans:
                    results.extend(spans)
            else:
                try:
                    line = int(range_str)
                except ValueError:
                    continue
                spans = self._read_file_span(path, (line, line))
                if spans:
                    results.extend(spans)

        return results

    def _read_file_span(self, rel_path, span):
        abs_path = os.path.join(self.root, rel_path)
        try:
            with open(abs_path, "r", errors="ignore") as f:
                lines = f.readlines()
        except OSError:
            return []

        if span is None:
            start = 1
            end = len(lines)
        else:
            start, end = span
            start = max(1, start)
            end = min(len(lines), end)

        content = "".join(lines[start - 1 : end])
        return [WarpGrepResult(rel_path, start, end, content)]
