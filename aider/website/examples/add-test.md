---
parent: Example chat transcripts
nav_order: 4
---

# Create a "black box" test case

This transcript shows aider creating a black box test case,
**without being given
access to the source code of the function being tested or any of the
other code in the repo.**

Instead, aider is operating entirely off a
[high level map of the repository based on ctags](https://aider.chat/docs/ctags.html),
which provides details on all the symbols and function signatures in the repo.
Using only the meta-data in the map, the LLM is able to figure out how to call the method to be tested, as well as how to instantiate multiple class objects that are required to prepare for the test.

In detail, aider is able to use the repo map to:

  - Find the function signature of the `cmd_add()` function which the user wants a test case for.
  - Determine that it is a method of the `Command` class, so the test case will need to instantiate an instance to conduct the test.
  - Identify that creating a `Command` instance requires passing in `InputOutput` and `Coder` instances.
  - Figure out the arguments required to instantiate the `InputOutput` instance.
  - Decide that the `Coder` class looks complex enough to use a `MagickMock`.

The `cmd_add()` method is defined without type annotations, so aider makes a
reasonable but incorrect guess that it accepts a `list` of files. The
user invokes the `/run` command to run the new unit test, which throws an
error based on this misunderstanding.

The LLM reviews the error message and fixes the call to `cmd_add()` to
correctly pass a `str` with a space-separated list of filenames
instead.  The test then passes on the next `/run`.

<div class="chat-transcript" markdown="1">

> $ aider tests/test_commands.py  
> Creating empty file tests/test_commands.py  
> Added tests/test_commands.py to the chat  
> Files not tracked in .git:  
> - tests/test_commands.py  
>  
> Add them? y  
> Added tests/test_commands.py to the git repo  
> Commit b9cea2c Added new files to the git repo: tests/test_commands.py  
> Using git repo: .git  

#### add a test for cmd_add that passes in 'foo.txt' and 'bar.txt' and ensures they have both been created after the test. run the test in a tmp dir.  

I will add a new test method called `test_cmd_add` in the `tests/test_commands.py` file. This test will create a temporary directory, change the current working directory to the temporary directory, and then call the `cmd_add` method with 'foo.txt' and 'bar.txt' as arguments. After that, it will check if both files have been created in the temporary directory.

Here's the code change:

```python
tests/test_commands.py
<<<<<<< ORIGINAL
=======
import os
import tempfile
from unittest import TestCase
from unittest.mock import MagicMock
from aider.commands import Commands
from aider.io import InputOutput

class TestCommands(TestCase):
    def test_cmd_add(self):
        # Create a temporary directory and change the current working directory
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            # Initialize the Commands and InputOutput objects
            io = InputOutput(pretty=False, yes=True)
            coder = MagicMock()
            commands = Commands(io, coder)

            # Call the cmd_add method with 'foo.txt' and 'bar.txt'
            commands.cmd_add(["foo.txt", "bar.txt"])

            # Check if both files have been created in the temporary directory
            self.assertTrue(os.path.exists("foo.txt"))
            self.assertTrue(os.path.exists("bar.txt"))
>>>>>>> UPDATED
```

This test will ensure that the `cmd_add` method creates the specified files in the current working directory.

> Applied edit to tests/test_commands.py  
> Commit e2d5212 aider: Added a test method `test_cmd_add` that creates a temporary directory, calls the `cmd_add` method with 'foo.txt' and 'bar.txt', and checks if both files have been created in the temporary directory.  

</div>
<div class="chat-transcript" markdown="1">
#### /run pytest tests/test_commands.py

> ```  
> ============================= test session starts ==============================  
> platform darwin -- Python 3.11.3, pytest-7.3.1, pluggy-1.0.0  
> rootdir: /Users/gauthier/Projects/aider  
> collected 1 item  
>   
> tests/test_commands.py F                                                 [100%]  
>   
> =================================== FAILURES ===================================  
> __________________________ TestCommands.test_cmd_add ___________________________  
>   
> self = <tests.test_commands.TestCommands testMethod=test_cmd_add>  
>   
>     def test_cmd_add(self):  
>         # Create a temporary directory and change the current working directory  
>         with tempfile.TemporaryDirectory() as tmpdir:  
>             os.chdir(tmpdir)  
>   
>             # Initialize the Commands and InputOutput objects  
>             io = InputOutput(pretty=False, yes=True)  
>             coder = MagicMock()  
>             commands = Commands(io, coder)  
>   
>             # Call the cmd_add method with 'foo.txt' and 'bar.txt'  
> >           commands.cmd_add(["foo.txt", "bar.txt"])  
>   
> /Users/gauthier/Projects/aider/tests/test_commands.py:20:  
> _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _  
>   
> self = <aider.commands.Commands object at 0x10b412b50>  
> args = ['foo.txt', 'bar.txt']  
>   
>     def cmd_add(self, args):  
>         "Add matching files to the chat session"  
>   
>         added_fnames = []  
>         files = self.coder.get_all_relative_files()  
> >       for word in args.split():  
> E       AttributeError: 'list' object has no attribute 'split'  
>   
> /Users/gauthier/Projects/aider/aider/commands.py:161: AttributeError  
> =========================== short test summary info ============================  
> FAILED tests/test_commands.py::TestCommands::test_cmd_add - AttributeError: '...  
> ============================== 1 failed in 0.34s ===============================  
> ```  
>
> Add the output to the chat? [y/n] (y): y  

It seems that the `cmd_add` method in `aider/commands.py` is expecting a string as input, but in the test, we are passing a list. I will update the test to pass a string instead of a list.

Here's the code change:

```python
tests/test_commands.py
<<<<<<< ORIGINAL
            # Call the cmd_add method with 'foo.txt' and 'bar.txt'
            commands.cmd_add(["foo.txt", "bar.txt"])
=======
            # Call the cmd_add method with 'foo.txt' and 'bar.txt' as a single string
            commands.cmd_add("foo.txt bar.txt")
>>>>>>> UPDATED
```

Now, run the test again with the updated test method:

```
pytest tests/test_commands.py
```

> Applied edit to tests/test_commands.py  
> Commit d1551b4 aider: Updated test to pass a string instead of a list when calling `cmd_add` method.  

</div>
<div class="chat-transcript" markdown="1">
#### /run pytest tests/test_commands.py

> ```  
> ============================= test session starts ==============================  
> platform darwin -- Python 3.11.3, pytest-7.3.1, pluggy-1.0.0  
> rootdir: /Users/gauthier/Projects/aider  
> collected 1 item  
>   
> tests/test_commands.py .                                                 [100%]  
>   
> ============================== 1 passed in 0.38s ===============================  
> ```  

</div>
