import tempfile
import unittest
from itertools import chain, repeat
from pathlib import Path
from unittest.mock import MagicMock, patch

from aider.coders import Coder
from aider.coders.betweenblock_coder import BetweenBlockCoder
from aider.io import InputOutput
from aider.models import Model

# from aider.utils import format_messages

main_model_name = "gpt-4"
merge_model_name = "gpt-3.5-turbo"


class TestBetweenBlockCoder(unittest.TestCase):
    def setUp(self):
        self.GPT4 = Model(main_model_name, merge_model=merge_model_name)

    def tearDown(self):
        pass

    @patch("litellm.completion")
    def test_between_edit(self, mock_completion: MagicMock):
        _, file1 = tempfile.mkstemp()

        with open(file1, "w", encoding="utf-8") as f:
            f.write("line one\nline two\nline three\n")

        files = [file1]

        coder = Coder.create(self.GPT4, "between", io=InputOutput(), fnames=files, stream=False)

        def mock_main_completion(*args, model=None, messages=None, temperature=None, **kwargs):
            # print("MAIN PROMPT:")
            # print(format_messages(messages))

            assert model == main_model_name
            assert (
                "2. Provide the code suggestions in a Markdown code block with this format:"
                in messages[0]["content"]
            )

            mock_completion.side_effect = mock_merge_completion

            return MagicMock(
                choices=[
                    MagicMock(
                        message=MagicMock(
                            role="assistant",
                            content=f"""Do this:

{Path(file1).name}
```
@BETWEEN@ "line two" AND "line three"
inserted line
```
""",
                            tool_calls=list(),
                        )
                    )
                ],
                usage=None,
            )

        def mock_merge_completion(*args, model=None, messages=None, temperature=None, **kwargs):
            # print("MERGE PROMPT:")
            # print(format_messages(messages))

            assert model == merge_model_name
            assert (
                "Merge all changes from the <update> snippet into the <code> below."
                in messages[-1]["content"]
            )
            assert temperature == 0.0

            assert 'Merge this code between "line two" and "line three":' in messages[-1]["content"]
            assert "<code>\nline one\nline two\nline three\n</code>" in messages[-1]["content"]
            assert "<update>\ninserted line\n</update>" in messages[-1]["content"]

            return MagicMock(
                choices=[
                    MagicMock(
                        message=MagicMock(
                            role="assistant",
                            content=(
                                "<updated-code>\nline one\nline two\ninserted line\nline"
                                " three\n</updated-code>"
                            ),
                            tool_calls=list(),
                        )
                    )
                ],
                usage=None,
            )

        mock_completion.side_effect = mock_main_completion

        # Call the run method with a message
        coder.run(with_message="hi")

        content = Path(file1).read_text(encoding="utf-8")

        self.assertEqual(mock_completion.call_count, 2)

        self.assertEqual(content, "line one\nline two\ninserted line\nline three\n")

    @patch("litellm.completion")
    def test_long_file_edit(self, mock_completion: MagicMock):
        _, file1 = tempfile.mkstemp()

        original_lines = list(map(str, range(0, 100)))

        with open(file1, "w", encoding="utf-8") as f:
            f.write("\n".join(original_lines))

        changed_lines = list(original_lines)

        changed_lines[62] = "sixty two"
        changed_lines[63] = "sixty three"
        changed_lines.insert(22, "21.5")

        files = [file1]

        coder = Coder.create(self.GPT4, "between", io=InputOutput(), fnames=files, stream=False)

        def mock_main_completion(*args, model=None, messages=None, temperature=None, **kwargs):
            mock_completion.side_effect = mock_merge_completion

            assert model == main_model_name

            return MagicMock(
                choices=[
                    MagicMock(
                        message=MagicMock(
                            role="assistant",
                            content=f"""Do this:

{Path(file1).name}
```
@BETWEEN@ "21" AND "22"
21.5

@BETWEEN@ "61" AND "64"
sixty two
sixty three
```
""",
                            tool_calls=list(),
                        )
                    )
                ],
                usage=None,
            )

        def mock_merge_completion(*args, model=None, messages=None, temperature=None, **kwargs):
            # print("MERGE PROMPT:")
            # print(format_messages(messages))

            assert model == merge_model_name

            assert (
                "Merge all changes from the <update> snippet into the <code> below."
                in messages[-1]["content"]
            )

            if 'Merge this code between "21" and "22":' in messages[-1]["content"]:
                assert """<code>
... 18 more lines ...

18
19
20
21
22
23
24
25

... 74 more lines ...
</code>""" in messages[-1]["content"]
                assert "<update>\n21.5\n</update>" in messages[-1]["content"]

                return MagicMock(
                    choices=[
                        MagicMock(
                            message=MagicMock(
                                role="assistant",
                                content="""<updated-code>
... 18 more lines ...

18
19
20
21
21.5
22
23
24
25

... 74 more lines ...
</updated-code>""",
                                tool_calls=list(),
                            )
                        )
                    ],
                    usage=None,
                )
            elif 'Merge this code between "61" and "64":' in messages[-1]["content"]:
                # 59 lines because "21.5" line already inserted
                assert """<code>
... 59 more lines ...

58
59
60
61
62
63
64
65
66
67

... 32 more lines ...
</code>""" in messages[-1]["content"]
                assert "<update>\nsixty two\nsixty three\n</update>" in messages[-1]["content"]

                return MagicMock(
                    choices=[
                        MagicMock(
                            message=MagicMock(
                                role="assistant",
                                content="""<updated-code>
... 59 more lines ...

58
59
60
61
sixty two
sixty three
64
65
66
67

... 32 more lines ...
</updated-code>""",
                                tool_calls=list(),
                            )
                        )
                    ],
                    usage=None,
                )
            else:
                assert 0

        mock_completion.side_effect = mock_main_completion

        # Call the run method with a message
        coder.run(with_message="hi")

        self.assertEqual(mock_completion.call_count, 3)

        content = Path(file1).read_text(encoding="utf-8")

        self.assertEqual(content, "\n".join(changed_lines))

    @patch("litellm.completion")
    def test_whole_file(self, mock_completion: MagicMock):
        _, file1 = tempfile.mkstemp()

        with open(file1, "w", encoding="utf-8") as f:
            f.write("line one\nline two\nline three\n")

        files = [file1]

        coder = Coder.create(self.GPT4, "between", io=InputOutput(), fnames=files, stream=False)

        mock_completion.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        role="assistant",
                        content=f"""Do this:

{Path(file1).name}
```
@WHOLE FILE@
line one!
line two!
line three!
```
""",
                        tool_calls=list(),
                    )
                )
            ],
            usage=None,
        )

        # Call the run method with a message
        coder.run(with_message="hi")

        content = Path(file1).read_text(encoding="utf-8")

        mock_completion.assert_called_once()

        self.assertEqual(content, "line one!\nline two!\nline three!\n")

    @patch("litellm.completion")
    def test_multiple_edits(self, mock_completion: MagicMock):
        tempdir = Path(tempfile.mkdtemp())

        file1 = tempdir / "file1.txt"
        file2 = tempdir / "file2.txt"
        newfile = tempdir / "file3.txt"

        with open(file1, "w", encoding="utf-8") as f:
            f.write("line one\nline two\nline three\nline four\nline five\n")
        with open(file2, "w", encoding="utf-8") as f:
            f.write("line six\nline seven\nline eight\n")

        files = [file1, file2]

        io = InputOutput()
        coder = Coder.create(self.GPT4, "between", io=io, fnames=files, stream=False)

        def mock_main_completion(*args, model=None, messages=None, temperature=None, **kwargs):
            # print("MAIN PROMPT:")
            # print(format_messages(messages))

            assert model == main_model_name

            mock_completion.side_effect = mock_merge_completion

            return MagicMock(
                choices=[
                    MagicMock(
                        message=MagicMock(
                            role="assistant",
                            content=f"""Do this:

{file1}
```
@BETWEEN@ "line one" AND "line two"
inserted line 1

@BETWEEN@ "line three" AND "line five"
LINE FOUR
```

{newfile}
```
@WHOLE FILE@
line ten
line eleven
line twelve
```

{file2}
```
@BETWEEN@ "line seven" AND "line eight"
line nine
```
""",
                            tool_calls=list(),
                        )
                    )
                ],
                usage=None,
            )

        def mock_merge_completion(*args, model=None, messages=None, temperature=None, **kwargs):
            # print("MERGE PROMPT:")
            # print(format_messages(messages))

            assert model == merge_model_name

            if 'Merge this code between "line one" and "line two":' in messages[-1]["content"]:
                return MagicMock(
                    choices=[
                        MagicMock(
                            message=MagicMock(
                                role="assistant",
                                content=(
                                    "<updated-code>\nline one\ninserted line\nline two\nline"
                                    " three\nline four\nline five\n</updated-code>"
                                ),
                                tool_calls=list(),
                            )
                        )
                    ],
                    usage=None,
                )
            elif 'Merge this code between "line three" and "line five":' in messages[-1]["content"]:
                return MagicMock(
                    choices=[
                        MagicMock(
                            message=MagicMock(
                                role="assistant",
                                content=(
                                    "<updated-code>\nline one\ninserted line 1\nline two\nline"
                                    " three\nLINE FOUR\nline five\n</updated-code>"
                                ),
                                tool_calls=list(),
                            )
                        )
                    ],
                    usage=None,
                )
            elif (
                'Merge this code between "line seven" and "line eight":' in messages[-1]["content"]
            ):
                return MagicMock(
                    choices=[
                        MagicMock(
                            message=MagicMock(
                                role="assistant",
                                content=(
                                    "<updated-code>\nline six\nline seven\nline eight\nline"
                                    " nine\n</updated-code>"
                                ),
                                tool_calls=list(),
                            )
                        )
                    ],
                    usage=None,
                )
            else:
                assert 0

        mock_completion.side_effect = mock_main_completion
        io.confirm_ask = MagicMock(return_value=True)

        coder.run(with_message="hi")

        self.assertEqual(mock_completion.call_count, 4)

        self.assertEqual(
            Path(file1).read_text(encoding="utf-8"),
            "line one\ninserted line 1\nline two\nline three\nLINE FOUR\nline five\n",
        )
        self.assertEqual(
            Path(file2).read_text(encoding="utf-8"), "line six\nline seven\nline eight\nline nine\n"
        )
        self.assertEqual(
            Path(newfile).read_text(encoding="utf-8"), "line ten\nline eleven\nline twelve\n"
        )

    @patch("litellm.completion")
    def test_non_unique_lines(self, mock_completion: MagicMock):
        _, file1 = tempfile.mkstemp()

        original_lines = list(chain(*zip(map(str, range(0, 100)), repeat("  REPEATING LINE"))))

        with open(file1, "w", encoding="utf-8") as f:
            f.write("\n".join(original_lines))

        changed_lines = list(original_lines)
        changed_lines.insert(73 * 2, "  inserted line 2")
        changed_lines.insert(27 * 2 + 1, "  inserted line 1")

        files = [file1]

        coder = Coder.create(self.GPT4, "between", io=InputOutput(), fnames=files, stream=False)

        def mock_main_completion(*args, model=None, messages=None, temperature=None, **kwargs):
            mock_completion.side_effect = mock_merge_completion

            assert model == main_model_name

            return MagicMock(
                choices=[
                    MagicMock(
                        message=MagicMock(
                            role="assistant",
                            content=f"""Do this:

{Path(file1).name}
```
@BETWEEN@ "27" AND "REPEATING LINE"
inserted line 1

@BETWEEN@ "REPEATING LINE" AND "73"
inserted line 2
```
""",
                            tool_calls=list(),
                        )
                    )
                ],
                usage=None,
            )

        def mock_merge_completion(*args, model=None, messages=None, temperature=None, **kwargs):
            # print("MERGE PROMPT:")
            # print(format_messages(messages))

            assert model == merge_model_name

            assert (
                "Merge all changes from the <update> snippet into the <code> below."
                in messages[-1]["content"]
            )

            if 'Merge this code between "27" and "REPEATING LINE":' in messages[-1]["content"]:
                assert """<code>
... 51 more lines ...

  REPEATING LINE
26
  REPEATING LINE
27
  REPEATING LINE
28
  REPEATING LINE
29

... 141 more lines ...
</code>""" in messages[-1]["content"]
                assert "<update>\ninserted line 1\n</update>" in messages[-1]["content"]

                return MagicMock(
                    choices=[
                        MagicMock(
                            message=MagicMock(
                                role="assistant",
                                content="""<updated-code>
... 51 more lines ...

  REPEATING LINE
26
  REPEATING LINE
27
  inserted line 1
  REPEATING LINE
28
  REPEATING LINE
29

... 141 more lines ...
</updated-code>""",
                                tool_calls=list(),
                            )
                        )
                    ],
                    usage=None,
                )
            elif 'Merge this code between "REPEATING LINE" and "73":' in messages[-1]["content"]:
                # 59 lines because "21.5" line already inserted
                assert """<code>
... 143 more lines ...

71
  REPEATING LINE
72
  REPEATING LINE
73
  REPEATING LINE
74
  REPEATING LINE

... 50 more lines ...
</code>""" in messages[-1]["content"]
                assert "<update>\ninserted line 2\n</update>" in messages[-1]["content"]

                return MagicMock(
                    choices=[
                        MagicMock(
                            message=MagicMock(
                                role="assistant",
                                content="""<updated-code>
... 143 more lines ...

71
  REPEATING LINE
72
  REPEATING LINE
  inserted line 2
73
  REPEATING LINE
74
  REPEATING LINE

... 50 more lines ...
</updated-code>""",
                                tool_calls=list(),
                            )
                        )
                    ],
                    usage=None,
                )
            else:
                assert 0

        mock_completion.side_effect = mock_main_completion

        # Call the run method with a message
        coder.run(with_message="hi")

        self.assertEqual(mock_completion.call_count, 3)

        content = Path(file1).read_text(encoding="utf-8")

        self.assertEqual(content, "\n".join(changed_lines))

    @patch("litellm.completion")
    def test_not_merged_between(self, mock_completion: MagicMock):
        _, file1 = tempfile.mkstemp()

        original_lines = list(map(str, range(0, 100)))

        with open(file1, "w", encoding="utf-8") as f:
            f.write("\n".join(original_lines))

        changed_lines = list(original_lines)

        changed_lines.insert(57, "56.5")
        changed_lines.insert(18, "17.5")

        with open(file1, "w", encoding="utf-8") as f:
            f.write("\n".join(original_lines))

        files = [file1]

        coder = Coder.create(self.GPT4, "between", io=InputOutput(), fnames=files, stream=False)

        def mock_main_completion(*args, model=None, messages=None, temperature=None, **kwargs):
            # print("MAIN PROMPT:")
            # print(format_messages(messages))

            assert model == main_model_name
            assert (
                "2. Provide the code suggestions in a Markdown code block with this format:"
                in messages[0]["content"]
            )

            mock_completion.side_effect = mock_first_merge_completion

            return MagicMock(
                choices=[
                    MagicMock(
                        message=MagicMock(
                            role="assistant",
                            content=f"""Do this:

{Path(file1).name}
```
@BETWEEN@ "17" AND "19"
17.5

@BETWEEN@ "51" AND "52"
56.5
```
""",
                            tool_calls=list(),
                        )
                    )
                ],
                usage=None,
            )

        def mock_first_merge_completion(
            *args, model=None, messages=None, temperature=None, **kwargs
        ):
            # print("MERGE PROMPT:")
            # print(format_messages(messages))

            assert model == merge_model_name

            if 'Merge this code between "17" and "19":' in messages[1]["content"]:
                assert """<code>
... 14 more lines ...

14
15
16
17
18
19
20
21
22

... 77 more lines ...
</code>""" in messages[-1]["content"]
                assert "<update>\n17.5\n</update>" in messages[-1]["content"]
                assert len(messages) == 2

                return MagicMock(
                    choices=[
                        MagicMock(
                            message=MagicMock(
                                role="assistant",
                                content="""<updated-code>
... 14 more lines ...

14
15
16
17
17.5
18
19
20
21
22

... 77 more lines ...
</updated-code>""",
                                tool_calls=list(),
                            )
                        )
                    ],
                    usage=None,
                )
            elif 'Merge this code between "51" and "52":' in messages[1]["content"]:
                assert """<code>
... 49 more lines ...

48
49
50
51
52
53
54
55

... 44 more lines ...
</code>""" in messages[1]["content"]
                assert "<update>\n56.5\n</update>" in messages[1]["content"]

                if len(messages) > 2:
                    assert "56.5" in messages[-2]["content"]
                    assert (
                        'Merge the <update> snippet between lines "51" and "52", not at end!'
                        in messages[-1]["content"]
                    )
                    assert len(messages) <= 4
                    if len(messages) == 4:
                        mock_completion.side_effect = mock_main_completion_fixed

                return MagicMock(
                    choices=[
                        MagicMock(
                            message=MagicMock(
                                role="assistant",
                                content="""<updated-code>
... 49 more lines ...

48
49
50
51
52
53
54
55
56.5

... 44 more lines ...
</updated-code>""",
                                tool_calls=list(),
                            )
                        )
                    ],
                    usage=None,
                )
            else:
                assert 0

        def mock_main_completion_fixed(
            *args, model=None, messages=None, temperature=None, **kwargs
        ):
            # print("FIX PROMPT:")
            # print(format_messages(messages))

            assert model == main_model_name
            assert (
                "2. Provide the code suggestions in a Markdown code block with this format:"
                in messages[0]["content"]
            )
            assert "This code cannot be inserted between lines" in messages[-1]["content"]

            mock_completion.side_effect = mock_fixed_merge_completion

            return MagicMock(
                choices=[
                    MagicMock(
                        message=MagicMock(
                            role="assistant",
                            content=f"""Do this:

{Path(file1).name}
```
@BETWEEN@ "56" AND "57"
56.5
```
""",
                            tool_calls=list(),
                        )
                    )
                ],
                usage=None,
            )

        def mock_fixed_merge_completion(
            *args, model=None, messages=None, temperature=None, **kwargs
        ):
            # print("MERGE PROMPT:")
            # print(format_messages(messages))

            assert model == merge_model_name

            assert 'Merge this code between "56" and "57":' in messages[-1]["content"]
            assert """<code>
... 54 more lines ...

53
54
55
56
57
58
59
60

... 39 more lines ...
</code>""" in messages[-1]["content"]
            assert "<update>\n56.5\n</update>" in messages[1]["content"]
            assert len(messages) == 2

            return MagicMock(
                choices=[
                    MagicMock(
                        message=MagicMock(
                            role="assistant",
                            content="""<updated-code>
... 54 more lines ...

53
54
55
56
56.5
57
58
59
60

... 39 more lines ...
</updated-code>""",
                            tool_calls=list(),
                        )
                    )
                ],
                usage=None,
            )

        mock_completion.side_effect = mock_main_completion

        # Call the run method with a message
        coder.run(with_message="hi")

        content = Path(file1).read_text(encoding="utf-8")

        self.assertEqual(mock_completion.call_count, 6)

        self.assertEqual(content, "\n".join(changed_lines))

    @patch("litellm.completion")
    def test_skipped_placeholder_at_begin(self, mock_completion: MagicMock):
        _, file1 = tempfile.mkstemp()

        original_lines = list(map(str, range(0, 100)))

        with open(file1, "w", encoding="utf-8") as f:
            f.write("\n".join(original_lines))

        changed_lines = list(original_lines)

        changed_lines[73] = "seventy three"

        files = [file1]

        coder = Coder.create(self.GPT4, "between", io=InputOutput(), fnames=files, stream=False)
        coder.max_reflections = 1

        mock_completion.side_effect = [
            MagicMock(
                choices=[
                    MagicMock(
                        message=MagicMock(
                            role="assistant",
                            content=f"""Do this:

{Path(file1).name}
```
@BETWEEN@ "72" AND "73"
seventy three
```
""",
                            tool_calls=list(),
                        )
                    )
                ],
                usage=None,
            ),
            MagicMock(
                choices=[
                    MagicMock(
                        message=MagicMock(
                            role="assistant",
                            content="""<updated-code>
69
70
71
72
seventy three
74
75
76

... 23 more lines ...
</updated-code>""",
                            tool_calls=list(),
                        )
                    )
                ],
                usage=None,
            ),
        ]

        # Call the run method with a message
        coder.run(with_message="hi")

        self.assertEqual(mock_completion.call_count, 2)

        content = Path(file1).read_text(encoding="utf-8")

        self.assertEqual(content, "\n".join(changed_lines))

    @patch("litellm.completion")
    def test_skipped_placeholder_at_end(self, mock_completion: MagicMock):
        _, file1 = tempfile.mkstemp()

        original_lines = list(map(str, range(0, 100)))

        with open(file1, "w", encoding="utf-8") as f:
            f.write("\n".join(original_lines))

        changed_lines = list(original_lines)

        changed_lines[73] = "seventy three"

        files = [file1]

        coder = Coder.create(self.GPT4, "between", io=InputOutput(), fnames=files, stream=False)
        coder.max_reflections = 1

        mock_completion.side_effect = [
            MagicMock(
                choices=[
                    MagicMock(
                        message=MagicMock(
                            role="assistant",
                            content=f"""Do this:

{Path(file1).name}
```
@BETWEEN@ "72" AND "73"
seventy three
```
""",
                            tool_calls=list(),
                        )
                    )
                ],
                usage=None,
            ),
            MagicMock(
                choices=[
                    MagicMock(
                        message=MagicMock(
                            role="assistant",
                            content="""<updated-code>
... 69 more lines ...

69
70
71
72
seventy three
74
75
76
</updated-code>""",
                            tool_calls=list(),
                        )
                    )
                ],
                usage=None,
            ),
        ]

        # Call the run method with a message
        coder.run(with_message="hi")

        self.assertEqual(mock_completion.call_count, 2)

        content = Path(file1).read_text(encoding="utf-8")

        self.assertEqual(content, "\n".join(changed_lines))

    def test_find_existing_line(self):
        coder = BetweenBlockCoder(main_model=self.GPT4, io=InputOutput(), fnames=[])
        content_lines = [
            "full line\n",
            "   indented line\n",
            "with-trailing-space \n",
            "repeating line\n",
            "tab\tin the  middle\n",
            "table    formatting\n",
            "  repeating line  \n",
            "comment at the end   # comment\n",
            '"line" with ""double" "-"quotes"\n',
            "no eol at end",
        ]

        self.assertEqual(coder.find_existing_line(content_lines, "full line"), [0])
        self.assertEqual(coder.find_existing_line(content_lines, "indented line"), [1])
        self.assertEqual(coder.find_existing_line(content_lines, "with-trailing-space"), [2])
        self.assertEqual(coder.find_existing_line(content_lines, "repeating line"), [3, 6])
        self.assertEqual(coder.find_existing_line(content_lines, "tab in the middle"), [4])
        self.assertEqual(coder.find_existing_line(content_lines, "table formatting"), [5])
        self.assertEqual(coder.find_existing_line(content_lines, "comment at the end"), [7])
        self.assertEqual(
            coder.find_existing_line(content_lines, '"line" with "double "-"quotes"'), [8]
        )
        self.assertEqual(coder.find_existing_line(content_lines, "no eol at end"), [9])


if __name__ == "__main__":
    unittest.main()
