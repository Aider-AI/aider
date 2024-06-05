---
parent: Example chat transcripts
---

# Honor the NO_COLOR environment variable

The user pastes the specification of the NO_COLOR environment variable protocol
from [no-color.org](https://no-color.org) into the aider chat.

Aider figures out which files need to be edited, and asks permission to make changes.
It then disables all the color and pretty-printing functions if NO_COLOR is
set, so the tool conforms to the specification.

The user then asks for a test case, which aider adds as well.

<div class="chat-transcript" markdown="1">

> $ aider  
> Using git repo: .git  
> Use /help to see in-chat commands.  

#### Command-line software which adds ANSI color to its output by default should check for a NO_COLOR environment variable that, when present and not an empty string (regardless of its value), prevents the addition of ANSI color.  

To implement this feature, we need to modify the `aider/io.py` file. Please make it *read-write* so I can provide the necessary changes.

> aider/io.py  
> Add these files to the chat? y  

Great! Now, I will make the necessary changes to check for the `NO_COLOR` environment variable and disable ANSI color when it is present and not an empty string.

```python
aider/io.py
<<<<<<< ORIGINAL
import os
=======
import os
import os.path
>>>>>>> UPDATED
```

```python
aider/io.py
<<<<<<< ORIGINAL
    def __init__(
        self,
        pretty=True,
        yes=False,
        input_history_file=None,
        chat_history_file=None,
        input=None,
        output=None,
        user_input_color="blue",
        tool_output_color=None,
        tool_error_color="red",
    ):
        self.user_input_color = user_input_color
        self.tool_output_color = tool_output_color
        self.tool_error_color = tool_error_color
        self.input = input
        self.output = output
        self.pretty = pretty
        self.yes = yes
        self.input_history_file = input_history_file
        if chat_history_file is not None:
            self.chat_history_file = Path(chat_history_file)
        else:
            self.chat_history_file = None

        if pretty:
            self.console = Console()
        else:
            self.console = Console(force_terminal=True, no_color=True)
=======
    def __init__(
        self,
        pretty=True,
        yes=False,
        input_history_file=None,
        chat_history_file=None,
        input=None,
        output=None,
        user_input_color="blue",
        tool_output_color=None,
        tool_error_color="red",
    ):
        no_color = os.environ.get("NO_COLOR")
        if no_color is not None and no_color != "":
            pretty = False

        self.user_input_color = user_input_color if pretty else None
        self.tool_output_color = tool_output_color if pretty else None
        self.tool_error_color = tool_error_color if pretty else None
        self.input = input
        self.output = output
        self.pretty = pretty
        self.yes = yes
        self.input_history_file = input_history_file
        if chat_history_file is not None:
            self.chat_history_file = Path(chat_history_file)
        else:
            self.chat_history_file = None

        self.console = Console(force_terminal=not pretty, no_color=not pretty)
>>>>>>> UPDATED
```

These changes will make the software check for the `NO_COLOR` environment variable and disable ANSI color when it is present and not an empty string.

> Applied edit to aider/io.py  
> Applied edit to aider/io.py  
> Commit 3218242 aider: Added check for NO_COLOR environment variable to disable ANSI color.  

</div>
<div class="chat-transcript" markdown="1">
#### add a test

To add a test for the `NO_COLOR` environment variable, we will create a new test function in the `tests/test_io.py` file. Since this file does not exist, we will create it first.

```python
tests/test_io.py
<<<<<<< ORIGINAL
=======
import os
import unittest
from unittest.mock import patch
from aider.io import InputOutput

class TestInputOutput(unittest.TestCase):
    def test_no_color_environment_variable(self):
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            io = InputOutput()
            self.assertFalse(io.pretty)

if __name__ == "__main__":
    unittest.main()
>>>>>>> UPDATED
```

This test function checks if the `pretty` attribute of the `InputOutput` class is set to `False` when the `NO_COLOR` environment variable is set.

> Allow creation of new file tests/test_io.py? y  
> Add tests/test_io.py to git? y  
> Applied edit to tests/test_io.py  
> Commit 52a9df5 aider: Added a test function to check if the `pretty` attribute of the `InputOutput` class is set to `False` when the `NO_COLOR` environment variable is set.  

</div>
<div class="chat-transcript" markdown="1">
#### /run pytest

> ============================= test session starts ==============================  
> platform darwin -- Python 3.11.3, pytest-7.3.1, pluggy-1.0.0  
> rootdir: /Users/gauthier/Projects/aider  
> collected 25 items  
>   
> tests/test_coder.py ......                                               [ 24%]  
> tests/test_commands.py .                                                 [ 28%]  
> tests/test_io.py .                                                       [ 32%]  
> tests/test_main.py ....                                                  [ 48%]  
> tests/test_repomap.py ...                                                [ 60%]  
> tests/test_utils.py ..........                                           [100%]  
>   
> ============================== 25 passed in 1.41s ==============================
>  
> Add the output to the chat? y


</div>
