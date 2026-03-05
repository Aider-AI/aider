import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from aider.warpgrep import WarpGrepClient, WarpGrepResult


class TestParseToolCalls:
    def setup_method(self):
        self.client = WarpGrepClient(
            api_key="test-key",
            root="/tmp",
            get_tracked_files_fn=lambda: [],
            io=MagicMock(),
        )

    def test_parse_single_tool_call(self):
        text = """<think>Looking for auth</think>

<tool_call>
<function=ripgrep>
<parameter=pattern>authenticate</parameter>
<parameter=path>src/</parameter>
</function>
</tool_call>"""
        calls = self.client._parse_tool_calls(text)
        assert len(calls) == 1
        assert calls[0]["function"] == "ripgrep"
        assert calls[0]["params"]["pattern"] == "authenticate"
        assert calls[0]["params"]["path"] == "src/"

    def test_parse_multiple_tool_calls(self):
        text = """<tool_call>
<function=ripgrep>
<parameter=pattern>login</parameter>
<parameter=path>.</parameter>
</function>
</tool_call>

<tool_call>
<function=read>
<parameter=path>src/auth.py</parameter>
</function>
</tool_call>"""
        calls = self.client._parse_tool_calls(text)
        assert len(calls) == 2
        assert calls[0]["function"] == "ripgrep"
        assert calls[1]["function"] == "read"

    def test_parse_finish_call(self):
        text = """<tool_call>
<function=finish>
<parameter=files>src/auth.py:1-15,45-80
src/middleware.py:*</parameter>
</function>
</tool_call>"""
        calls = self.client._parse_tool_calls(text)
        assert len(calls) == 1
        assert calls[0]["function"] == "finish"
        assert "src/auth.py:1-15,45-80" in calls[0]["params"]["files"]

    def test_parse_no_tool_calls(self):
        text = "Just some thinking without any tool calls."
        calls = self.client._parse_tool_calls(text)
        assert len(calls) == 0

    def test_parse_ripgrep_with_glob(self):
        text = """<tool_call>
<function=ripgrep>
<parameter=pattern>TODO</parameter>
<parameter=path>src/</parameter>
<parameter=glob>*.py</parameter>
</function>
</tool_call>"""
        calls = self.client._parse_tool_calls(text)
        assert len(calls) == 1
        assert calls[0]["params"]["glob"] == "*.py"


class TestRepoStructure:
    def setup_method(self):
        self.client = WarpGrepClient(
            api_key="test-key",
            root="/tmp",
            get_tracked_files_fn=lambda: [],
            io=MagicMock(),
        )

    def test_build_repo_structure(self):
        files = ["src/main.py", "src/utils.py", "README.md"]
        result = self.client._build_repo_structure(files)
        assert "README.md" in result
        assert "src/main.py" in result
        assert "src/utils.py" in result

    def test_build_repo_structure_sorted(self):
        files = ["z.py", "a.py", "m.py"]
        result = self.client._build_repo_structure(files)
        lines = result.strip().split("\n")
        assert lines == ["a.py", "m.py", "z.py"]

    def test_build_repo_structure_empty(self):
        result = self.client._build_repo_structure([])
        assert result == ""


class TestFinishParsing:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        # Create test files
        os.makedirs(os.path.join(self.tmpdir, "src"), exist_ok=True)
        with open(os.path.join(self.tmpdir, "src", "auth.py"), "w") as f:
            for i in range(100):
                f.write(f"# line {i + 1}\n")
        with open(os.path.join(self.tmpdir, "src", "middleware.py"), "w") as f:
            for i in range(50):
                f.write(f"# middleware line {i + 1}\n")

        self.client = WarpGrepClient(
            api_key="test-key",
            root=self.tmpdir,
            get_tracked_files_fn=lambda: ["src/auth.py", "src/middleware.py"],
            io=MagicMock(),
        )

    def test_process_finish_with_ranges(self):
        results = self.client._process_finish("src/auth.py:1-15")
        assert len(results) == 1
        assert results[0].rel_path == "src/auth.py"
        assert results[0].start_line == 1
        assert results[0].end_line == 15

    def test_process_finish_wildcard(self):
        results = self.client._process_finish("src/middleware.py:*")
        assert len(results) == 1
        assert results[0].rel_path == "src/middleware.py"
        assert results[0].start_line == 1
        assert results[0].end_line == 50

    def test_process_finish_multiple_ranges(self):
        results = self.client._process_finish("src/auth.py:1-15,45-80")
        assert len(results) == 2
        assert results[0].start_line == 1
        assert results[0].end_line == 15
        assert results[1].start_line == 45
        assert results[1].end_line == 80

    def test_process_finish_multiple_files(self):
        specs = "src/auth.py:1-15\nsrc/middleware.py:*"
        results = self.client._process_finish(specs)
        assert len(results) == 2
        paths = {r.rel_path for r in results}
        assert paths == {"src/auth.py", "src/middleware.py"}

    def test_process_finish_empty(self):
        results = self.client._process_finish("")
        assert results == []

    def test_process_finish_nonexistent_file(self):
        results = self.client._process_finish("nonexistent.py:1-10")
        assert results == []


class TestReadAndGrep:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        with open(os.path.join(self.tmpdir, "test.py"), "w") as f:
            f.write("def hello():\n    print('hello')\n\ndef world():\n    print('world')\n")

        self.client = WarpGrepClient(
            api_key="test-key",
            root=self.tmpdir,
            get_tracked_files_fn=lambda: ["test.py"],
            io=MagicMock(),
        )

    def test_exec_read(self):
        result = self.client._exec_read({"path": "test.py"})
        assert "<tool_response>" in result
        assert "1|def hello():" in result
        assert "2|    print('hello')" in result

    def test_exec_read_nonexistent(self):
        result = self.client._exec_read({"path": "missing.py"})
        assert "Error reading" in result

    def test_python_grep(self):
        result = self.client._python_grep("hello", self.tmpdir)
        assert "hello" in result

    def test_exec_list_directory(self):
        result = self.client._exec_list_directory({"path": "."})
        assert "<tool_response>" in result
        assert "test.py" in result


class TestMockHTTP:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, "src"), exist_ok=True)
        with open(os.path.join(self.tmpdir, "src", "app.py"), "w") as f:
            for i in range(20):
                f.write(f"# line {i + 1}\n")

        self.client = WarpGrepClient(
            api_key="test-key",
            root=self.tmpdir,
            get_tracked_files_fn=lambda: ["src/app.py"],
            io=MagicMock(),
        )

    @patch("aider.warpgrep.requests.post")
    def test_search_finish_immediately(self, mock_post):
        finish_response = {
            "choices": [
                {
                    "message": {
                        "content": (
                            "<tool_call>\n"
                            "<function=finish>\n"
                            "<parameter=files>src/app.py:1-10</parameter>\n"
                            "</function>\n"
                            "</tool_call>"
                        )
                    }
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = finish_response
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        results = self.client.search("test query")
        assert len(results) == 1
        assert results[0].rel_path == "src/app.py"
        assert results[0].start_line == 1
        assert results[0].end_line == 10

    @patch("aider.warpgrep.requests.post")
    def test_search_multi_turn(self, mock_post):
        ripgrep_response = {
            "choices": [
                {
                    "message": {
                        "content": (
                            "<tool_call>\n"
                            "<function=ripgrep>\n"
                            "<parameter=pattern>line</parameter>\n"
                            "<parameter=path>src/</parameter>\n"
                            "</function>\n"
                            "</tool_call>"
                        )
                    }
                }
            ]
        }
        finish_response = {
            "choices": [
                {
                    "message": {
                        "content": (
                            "<tool_call>\n"
                            "<function=finish>\n"
                            "<parameter=files>src/app.py:1-5</parameter>\n"
                            "</function>\n"
                            "</tool_call>"
                        )
                    }
                }
            ]
        }

        mock_resp1 = MagicMock()
        mock_resp1.json.return_value = ripgrep_response
        mock_resp1.raise_for_status = MagicMock()

        mock_resp2 = MagicMock()
        mock_resp2.json.return_value = finish_response
        mock_resp2.raise_for_status = MagicMock()

        mock_post.side_effect = [mock_resp1, mock_resp2]

        results = self.client.search("find lines")
        assert len(results) == 1
        assert results[0].rel_path == "src/app.py"
        assert mock_post.call_count == 2

    @patch("aider.warpgrep.requests.post")
    def test_search_no_results(self, mock_post):
        finish_response = {
            "choices": [
                {
                    "message": {
                        "content": (
                            "<tool_call>\n"
                            "<function=finish>\n"
                            "<parameter=files></parameter>\n"
                            "</function>\n"
                            "</tool_call>"
                        )
                    }
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = finish_response
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        results = self.client.search("nonexistent")
        assert results == []
