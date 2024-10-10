# flake8: noqa: E501

from .cedarscript_prompts_base import CedarPromptsBase


class CedarPromptsRW(CedarPromptsBase):

    def edit_format_name(self):
        return f"{super().edit_format_name()}-rw"

    final_remarks = CedarPromptsBase.final_remarks_brain

    cedarscript_training = """<details><summary>CEDARScript rules</summary>
CEDARScript is used to express code changes and to help an LLM understand the codebase.
<notes>
<p>CEDARScript never uses line numbers to identify a line. Instead, it uses line markers.</p>
A line marker is any of the lines found in the original code, but trimmed.
<p>Examples:</p>
Consider this original code:
<original>
    print("min: " + min_value)
    if avg_value > 0:
        print("avg: " + avg_value)
    print("max: " + max_value)
</original>

To identify the line that prints the average value, use this line marker: "print(\\"avg: \\" + avg_value)"
Note that this line marker doesn't have any spaces to the left, as the corresponding original line is always trimmed.
</notes>

CEDARScript cookbook:

<details topic="How to change the codebase">
<summary>Commands that modify the codebase</summary>
<command name="DELETE">
<use-cases>
Can only be used to delete files
</use-cases>
<details topic="the DELETE command">
<summary>Use `DELETE FILE <path/to/file>` to delete files.</summary>
</details>
</command>

<command name="MOVE">
<use-cases>
Renaming a file, moving a file to another path.
</use-cases>
<details>
<syntax>`MOVE FILE "<original>" TO "<new>"`.</syntax>
</details>
<examples>
<details>
<summary>Rename "old-file.js", then move "config.json" to "production" folder</summary>
<output>
{fence[0]}CEDARScript
-- Rename "old-file.js"
MOVE FILE "src/old-file.js" TO "src/new-file.js";
-- move "config.json" to "production" folder
MOVE FILE "development/config.json" TO "production/config.json";
{fence[1]}
</output>
</details>
</examples>
</command>

<command name="CREATE">
<use-cases>`CREATE` can *ONLY* be used to create a file.</use-cases>
<details topic="The CREATE clause>
<summary>Use `CREATE FILE <file-path>` to create a new file.</summary>
</details>
<examples>
<details>
<summary>To create a new file</summary>
<output>
{fence[0]}CEDARScript
CREATE FILE "path/to/file"
  WITH CONTENT '''
@0:import os
@0:
@0:def myfunction():
@1:// TODO
''';
{fence[1]}
</output>
</details>
</examples>
<notes>
The `CREATE` command *CANNOT* be used to modify existing files *at all*!
</notes>
</command>

<command name="UPDATE">
<use-cases>
- Creating or replacing classes, functions or other code in existing files/classes/functions
- Replacing specific lines of existing code
- Performing complex code transformations using patterns
- etc...
</use-cases>
<details topic="the UPDATE clause">
<summary>Use `UPDATE FILE <path/to/file>` or `UPDATE (CLASS|FUNCTION) FROM FILE <path/to/file> WHERE NAME (LIKE|=) "<name>";` to modify the relevant portion of the codebase.</summary>

<p>Restricting the scope of modifications:</p>
<ul>
<li>`FILE`: the file itself</li>
<li>`CLASS`: a class</li>
<li>`FUNCTION`: method or function</li>
</ul>
</details>

<details topic="The FROM clause">
<summary>Specify `FROM FILE <path/to/file>` to specify which file to be used.</summary>
</details>

<details topic="The REPLACE clause">
<summary>
Use `REPLACE (WHOLE|BODY|SEGMENT)` to identify what portion of the FILE, CLASS or FUNCTION should be replaced.
</summary>

<ul>
<li>`WHOLE`: the whole FILE, CLASS or FUNCTION</li>
<li>`BODY`: the body of the CLASS or FUNCTION</li>
<li>`SEGMENT`: a region of the FILE, CLASS or FUNCTION</li>
</ul>

<details topic="The SEGMENT clause">
<summary>
Use `REPLACE SEGMENT STARTING (AT|BEFORE|AFTER) "<first-line-marker>" [OFFSET <n>] ENDING (AT|BEFORE|AFTER) <last-line-marker> [OFFSET <n>];` to replace existing content with new content.
</summary>

<details>
<summary>Optional `OFFSET` clause</summary>
Both `STARTING` and `ENDING` accept `OFFSET` clause to identify a specific line occurrence (*MANDATORY* iff there are 2 or more lines with the same content).
<syntax>`OFFSET <n>` where *n* is an integer to identify how many occurrences to skip.</syntax> 
<ul>
<li>`OFFSET 0` is the default, so you shouldn't write it explicitly. It means to skip 0 items (so, points to the *1st* occurrence).</li>
<li>`OFFSET 1` skips 1 item, so points to the *2nd* occurrence</li>
<li>`OFFSET 2` skips 2 items, so points to the *3rd* occurrence</li>
<li>`OFFSET n` skips n items, thus specifies the (n+1)-th occurrence</li>
</ul>
</details>

<p>Specify a given segment of starting and ending line markers as shown in these examples:</p>
<ul>
<li>
<original>
    print("min: " + min_value)
    print("max: " + max_value)
</original>
<select title="Insert line between min and max to print the `avg_value`">
<option value="REPLACE SEGMENT">
```CEDARScript
-- Insert line between min and max to print the `avg_value`
REPLACE SEGMENT
  STARTING AT "print(\\"min: \\" + min_value)"
  ENDING AT "print(\\"max: \\" + max_value)"
WITH CONTENT '''
@0:print("min: " + min_value)
@0:print("avg: " + avg_value)
@0:print("max: " + max_value)
''';
```
</output>
</option><option value="INSERT" selected title="Preferred">
```CEDARScript
-- Insert line between min and max to print the `avg_value` (using INSERT)
INSERT AFTER "print(\\"min: \\" + min_value)"
WITH CONTENT '''
@0:print("avg: " + avg_value)
''';
```
</option></select>
<select title="Delete line that prints the `max_value`">
<option>
```CEDARScript
-- Delete line that prints the `max_value`
REPLACE SEGMENT
  STARTING AT "print(\\"min: \\" + min_value)"
  ENDING AT "print(\\"max: \\" + max_value)"
WITH CONTENT '''
@0:print("min: " + min_value)
''';
```
</option>
</li>
<li>
<original>
    def my_function(min_value: int, max_value: int):
        print("min: " + min_value)
        print("max: " + max_value)
        compute(1)
        compute(2)
        compute(3)
</original>
<select title="This example shows how to replace the first few lines of a function">
<option>
```CEDARScript
-- Call `compute(0)` as the first line of the body
REPLACE SEGMENT
  STARTING AT "def my_function(min_value: int, max_value: int):"
  ENDING AT "print(\\"min: \\" + min_value)"
WITH CONTENT '''
@0:def my_function(min_value: int, max_value: int):
@1:compute(0)
@1:print("min: " + min_value)
''';
```
</option>
</select>
</li>
</ul>
</details>

<details topic="The INSERT clause">
<summary>
Use `INSERT (BEFORE|AFTER) "<line-marker>" [OFFSET <n>];` to insert new content before or after a specific line of the FILE, CLASS or FUNCTION.
</summary>

<p>Specify a given line of reference for BEFORE or AFTER as shown in these examples:</p>
<ul>
<li>
<original>
    print("min: " + min_value)
    print("max: " + max_value)
</original>
<select><option>
```CEDARScript
INSERT BEFORE "print(\\"max: \\" + max_value)"
WITH CONTENT '''
@0:print("avg: " + avg_value)
''';
```
</option>
<option>
```CEDARScript
INSERT AFTER "print(\\"min: \\" + min_value)"
WITH CONTENT '''
@0:print("avg: " + avg_value)
''';
```
</option><option>
```CEDARScript
INSERT AFTER "print(\\"min: \\" + min_value)"
WITH CONTENT '''
@0:print("avg: " + avg_value)
@0:if avg_value > 5:
@1:print("avg_value is too high!")
''';
```
</option></select>
</li>
</ul>

</details>

<examples>

<details topic="Advanced pattern-based refactorings">
<summary>
We can indirectly use the `Restructure` class in the 'Rope' refactoring library to perform complex code transformations using patterns.
These patterns can match and replace code structures in your project.
</summary>
<p>General syntax:
{fence[0]}CEDARScript
UPDATE PROJECT
  REFACTOR LANGUAGE "rope"
  WITH PATTERN '''
<rope-line pattern expression>
'''
  WITH GOAL '''
<rope-like goal expression>
''';
{fence[1]}
</p>
</details>

<details>
<summary>Replace the whole contents of a file</summary>
<output>
{fence[0]}CEDARScript
UPDATE FILE "path/to/file.txt"
  REPLACE WHOLE
  WITH CONTENT '''
@0:<Content here...>
''';
{fence[1]}
</output>
</details>

<details>
<summary>Create a new method or function</summary>
<output>
{fence[0]}CEDARScript
UPDATE FILE "path/to/file.txt"
  INSERT BEFORE "def function_5():"
  WITH CONTENT '''
@0:def function_4(param1: int, param2: str):
@1:// content here...
''';
{fence[1]}
</output>
</details>

<details>
<summary>Create a new method in a class</summary>
<output>
{fence[0]}CEDARScript
UPDATE CLASS
  FROM FILE "path/to/file"
  WHERE NAME = "<class name>"
  INSERT BEFORE LINE "def function_5():"
  WITH CONTENT '''
@0:def function_4(param1: int, param2: str):
@1:// content here...
''';
{fence[1]}
</output>
</details>

<details>
<summary>Replace a segment of lines in a function, including its decorators, signature and body (the starting and ending lines are also replaced)</summary>
<output>
{fence[0]}CEDARScript
UPDATE FUNCTION
  FROM FILE "path/to/file"
  WHERE NAME = "function_name" OFFSET 0
  REPLACE SEGMENT
    STARTING AT "some existing line" OFFSET 1
    ENDING BEFORE "a *different* existing line"
  WITH CONTENT '''
@0:<Content here>
''';
{fence[1]}
</output>
<notes>
- `OFFSET` specifies how many items to skip. 0 means don't skip, so the first item is considered. Useful when there are 2 or more items with the same name, like 2 overloaded functions.
- for `STARTING AT`, we have the trimmed contents of an existing line ( "some existing line" ). `OFFSET` 1 means to skip 1 line with that same content.
- for `ENDING BEFORE`, we have the trimmed contents of an existing line ( "a different existing line" ) that comes after the line for `STARTING AT`
</notes>
</details>

<details>
<summary>Delete one or more lines in a function</summary>
<original>
def function_name():
    print("min: " + min_value)
    if avg_value > 0:
        print("avg: " + avg_value)
    print("max: " + max_value)
    do_something_else()
</original>
<output>
{fence[0]}CEDARScript
-- Delete the line that prints `max_value`
UPDATE FUNCTION
  FROM FILE "path/to/file"
  WHERE NAME = "function_name"
  REPLACE SEGMENT
    STARTING AT "print(\\"avg: \\" + avg_value)"
    ENDING AT "print(\\"max: \\" + max_value)"
  WITH CONTENT '''
@0:print("avg: " + avg_value)
''';
{fence[1]}
</output>
<notes>
- `STARTING AT` points to the line immediately *before* the one to delete
- `ENDING AT` points to the line to delete
- `WITH CONTENT` contains only the same line referenced by `STARTING AT`
</notes>
</details>

<details>
<summary>Delete one or more lines in a function (alternative)</summary>
<original>
def function_name():
    print("min: " + min_value)
    if avg_value > 0:
        print("avg: " + avg_value)
    print("max: " + max_value)
    do_something_else()
</original>
<output>
{fence[0]}CEDARScript
-- Delete the line that prints `max_value`
UPDATE FUNCTION
  FROM FILE "path/to/file"
  WHERE NAME = "function_name"
  REPLACE SEGMENT
    STARTING AT "print(\\"max: \\" + max_value)"
    ENDING AT "do_something_else()"
  WITH CONTENT '''
@0:do_something_else()
''';
{fence[1]}
</output>
<notes>
- `STARTING AT` points to the line to delete
- `ENDING AT` points to the line immediately *after* the one to delete
- `WITH CONTENT` contains only the same line referenced by `ENDING AT`
</notes>
</details>


<details>
<output>
{fence[0]}CEDARScript
-- Replace the whole body of a function
UPDATE FUNCTION
  FROM FILE "path/to/file"
  WHERE NAME = "function_name"
  REPLACE BODY
  WITH CONTENT '''
@0:<new function body here>
''';
{fence[1]}
</output>
<notes>
Use `REPLACE BODY` when the function signature doesn't change and there's a lot to change in the body.
*NEVER* include the function signature inside `WITH CONTENT`, as the contents refer to the body only.
</notes>
</details>

<details>
<output>
{fence[0]}CEDARScript
-- Replace the whole function
UPDATE FUNCTION
  FROM FILE "path/to/file"
  WHERE NAME = "function_name"
  REPLACE WHOLE
  WITH CONTENT '''
@0:<new function signature>
@1:<new function body here>
''';
{fence[1]}
</output>
<notes>
Use `REPLACE WHOLE` when the function signature DOES change and there's a lot to change in the body.
*ALWAYS* include the function signature inside `WITH CONTENT`, as the contents refer to the whole function definition.
</notes>
</details>

<details>
<output>
{fence[0]}CEDARScript
-- Move lines within a file
UPDATE FILE "path/to/file"
  MOVE SEGMENT
    STARTING AT "do_something()"
    ENDING AT "do_something_else()"
  INSERT AFTER "if hour == 12:"
    RELATIVE INDENTATION 1;
{fence[1]}
</output>
<notes>
Use `INSERT BEFORE` or `INSERT AFTER` to specify target where the lines to be moved will be pasted. This is used as the reference indentation level.
`RELATIVE INDENTATION` is set to 1 because we need to put the segment 1 level of indentation *deeper* than the line used as reference ("if hour == 12:")
</notes>
</details>

<details>
<output>
{fence[0]}CEDARScript
-- Move lines within a function
UPDATE FUNCTION
  FROM FILE "path/to/file"
  WHERE NAME = "function_name"
  MOVE SEGMENT
    STARTING AT "do_something()"
    ENDING AT "do_something_else()"
  INSERT BEFORE "line marker..."
    RELATIVE INDENTATION 0;
{fence[1]}
</output>
<notes>
Use `INSERT BEFORE` or `INSERT AFTER` to specify target where the lines to be moved will be pasted.
</notes>
</details>

<details>
<output>
{fence[0]}CEDARScript
-- Rename function `OLD_name` to `NEW_name`
UPDATE FUNCTION
  FROM FILE "path/to/file"
  WHERE NAME = "OLD_name"
  RENAME TO "NEW_name";
{fence[1]}
</output>
</details>

</examples>
</command>
</details>

<details topic="How to query the codebase">
<summary>Learning more about the codebase</summary>
<command name="SELECT">
<use-cases>
- Understanding code structure;
- Finding relevant files/classes/functions/variables that may deal with a certain topic
   - (ex.: if a user may want to find all places that deal with payments, search for 'payment')
- Generating documentation;
- Automating code navigation.
</use-cases>
<details topic="The SELECT clause">
<summary>Use `SELECT (FILE NAMES|FILE PATHS|FILES|FUNCTION NAMES|FUNCTION SIGNATURES|FUNCTIONS|IDENTIFIERS|USAGES)` to obtain the desired portions of code</summary>

- `FILE NAMES`: only file names
- `FILE PATHS`: file path and names
- `FILES`: the file name and its whole contents

- `FUNCTION NAMES`: only the function names
- `FUNCTION SIGNATURES`: only the function signatures
- `FUNCTIONS`: the whole function

- `USAGES`: the call sites of a function, or sites where a variable is written to or read from, or class usages, etc

- `IDENTIFIERS`: Names of key elements like classes, functions, variables, etc.
   - Returns a dictionary where keys are file paths and values are lists of defined names within that file.

</details>

<details topic="The FROM clause">
<summary>Specify `FROM (PROJECT|DIRECTORY <path/to/dir>)` to choose where to search for files.</summary>
</details>

<details topic="The WHERE clause">
<details topic="Matching file names or paths">
- Specify `WHERE (NAME|PATH) = "<string>"` to match a specific string.
- Specify `WHERE (NAME|PATH) LIKE "<pattern>"` to match using a SQL-like pattern
</details>
<details topic="Matching for identifiers">
<summary>Can be used with `SELECT IDENTIFIERS`</summary>
- Specify `WHERE IDENTIFIER_TYPE = (CLASS|FUNCTION|VARIABLE|FIELD)` to be more specific
- Specify `WHERE NAME = "<string>"` to match a specific string.
- Specify `WHERE NAME LIKE "<pattern>"` to match using a SQL-like pattern
</details>
<details topic="Matching for usages, call sites">
<summary>Can be used with `SELECT USAGES`</summary>
- Specify `WHERE USAGE_TYPE = (READ|WRITE)` to match a specific variable or field usage type.
- Specify `WHERE IDENTIFIER_TYPE = (CLASS|FUNCTION|VARIABLE|FIELD)` to be more specific
</details>
</details>

<details topic="Limiting and pagination of result items">
<summary>You can use pagination when needed (using LIMIT <int> and OFFSET <int>)</summary>
</details>

<examples>
<details>
<summary>Request files to be included in the chat, from base-directory only</summary>
<output>
{fence[0]}CEDARScript
SELECT FILES
  FROM DIRECTORY "path/to/base-directory" MAX DEPTH 1
  WHERE NAME = "file_name"
  LIMIT 3;
{fence[1]}
</output>

<details>
<summary>Request files to be included in the chat, in base-directory or any of its sub-directories</summary>
<output>
{fence[0]}CEDARScript
SELECT FILES
  FROM DIRECTORY "path/to/base-directory"
  WHERE NAME LIKE "%pattern%";
{fence[1]}
</output>
</details>

<details>
<summary>Request files to be included in the chat (any file in project)</summary>
<output>
{fence[0]}CEDARScript
SELECT FILES
  FROM PROJECT
  WHERE NAME LIKE "file_name"
  LIMIT 70;
{fence[1]}
</output>
</details>

<details>
<summary>Request files to be included in the chat (any file in project)</summary>
<output>
{fence[0]}CEDARScript
SELECT FILES
  FROM PROJECT
  WHERE CONTENT LIKE "%search term%"
  LIMIT 7;
{fence[1]}
</output>
</details>

<details>
<summary>Obtain the whole function (if you need to understand the function without having to get the whole file)</summary>
<output>
{fence[0]}CEDARScript
SELECT FUNCTIONS
  FROM FILE "path/to/file"
  WHERE NAME = "function_name"
  LIMIT 1;
{fence[1]}
</output>
</details>

<details>
<summary>Obtain function signatures only from all functions matching a pattern</summary>
<output>
{fence[0]}CEDARScript
SELECT FUNCTION SIGNATURES
  FROM FILE "path/to/file"
  WHERE NAME LIKE "%pattern-here%"
  LIMIT 2;
{fence[1]}
</output>
</details>

<details>
<summary>Obtain the call sites of a function</summary>
<output>
{fence[0]}CEDARScript
SELECT USAGES
  FROM PROJECT
  WHERE NAME = "function_name"
  LIMIT 100;
{fence[1]}
</output>
</details>

<details>
<summary>Obtain the call sites of a function</summary>
<output>
{fence[0]}CEDARScript
SELECT USAGES
  FROM PROJECT
  WHERE NAME = "variable_name"
    AND TYPE = VARIABLE
    AND USAGE_TYPE = WRITE
{fence[1]}
</output>
</details>

</examples>

</command>

</details>

<details>

<details topic="Crucial detail for content inside `WITH CONTENT` blocks">
<summary>Always use the correct 'relative indentation prefix'</summary>
<examples>
<details>
<summary>`REPLACE SEGMENT`</summary>
<code>
class MyClass:
    def main_function():
        def complex_function():
            if condition:
                first_action("")
                second_action()
                third_action()
            final_action()
</code>
<output>
{fence[0]}CEDARScript
UPDATE FUNCTION
  FROM FILE "example.py"
  WHERE NAME = "complex_function"
  REPLACE SEGMENT
    STARTING AT "first_action(\\"\\")"
    ENDING AT "third_action()"
  WITH CONTENT '''
@0:new_first_action("")
@0:if nested_condition:
@1:nested_action()
@0:new_last_action()
''';
{fence[1]}
</output>
<notes>
- Only line `nested_action()` has relative indentation level 1 (@1:) inside `WITH CONTENT`, as all others have level 0.
- for STARTING AT, we have the trimmed contents of an existing line ( "first_action(\\"\\")" )
- for ENDING AT, we have the trimmed contents of an existing line ( "third_action()" ) that comes after the line for `STARTING AT`
- IMPORTANT! We MUST ALWAYS escape quotes by using `\\"` for each character `"` used in `STARTING AT` or `ENDING AT`, as seen in the example above.
</notes>
</details>

<details>
<summary>`REPLACE SEGMENT`</summary>
<code>
class MyClass:
    def main_function():
        def complex_function():
            if condition:
                first_action("")
                second_action()
                third_action()
            final_action()
</code>
<output>
{fence[0]}CEDARScript
UPDATE FUNCTION
  FROM FILE "example.py"
  WHERE NAME = "complex_function"
  REPLACE SEGMENT
    STARTING AT "if condition:"
    ENDING AT "third_action()"
  WITH CONTENT '''
@0:if condition:
@1:new_first_action("")
@1:if nested_condition:
@2:nested_action()
''';
{fence[1]}
</output>
<notes>
- `STARTING AT` pointed to the `if` line. Since we want to keep the `if`, we start the content with indentation level 0 and rewrite the `if`;
</notes>
</details>

<details>
<summary>`REPLACE SEGMENT` to add a fourth action, using negative indentation</summary>
<code>
class MyClass:
    def main_function():
        def complex_function():
            if condition:
                first_action("")
                second_action()
                third_action()
                # TODO Call fourth_action() here
            final_action()
</code>
<output>
{fence[0]}CEDARScript
UPDATE FUNCTION
  FROM FILE "example.py"
  WHERE NAME = "complex_function"
  REPLACE SEGMENT
    STARTING AT "third_action()"
    ENDING AT "final_action()"
  WITH CONTENT '''
@0:third_action()
@0:fourth_action()
@-1:final_action()
''';
{fence[1]}
</output>
<notes>
- `ENDING AT` pointed to `final_action()`, which we wanted to keep. As that line has a lower indentation level, we used `@-1` to decrement indentation relative to the previous lines;
</notes>
</details>

<details>
<summary>`REPLACE BODY`</summary>
<original>
class MyClass:
    def main_function():
        def complex_function():
            if condition:
                first_action()
                second_action()
                third_action()
            final_action()
</original>
<output>
{fence[0]}CEDARScript
UPDATE FUNCTION
  FROM FILE "example.py"
  WHERE NAME = "complex_function"
  REPLACE BODY
  WITH CONTENT '''
@0:if condition:
@1:new_first_action()
@1:if nested_condition:
@2:nested_action()
@1:new_last_action()
@1:final_action()
''';
{fence[1]}
</output>
<notes>
- Only the line `if condition:` is indented at level 0 inside `WITH CONTENT` (@0:), as all others have relative indentation level 1 or 2.
- When using `REPLACE BODY`, you must always start with indentation level 0 (@0:), since the reference indentation is always the first line of the original function body.
- Observe we don't write the function signature: we only write the function body when using `REPLACE BODY` !
</notes>
</details>

</examples>

</details>

</details>
"""

    # Appears twice (as SYSTEM and as USER):
    system_reminder = """When presented with a code change task, you should use the most appropriate sequence of CEDARScript commands
to *precisely* describe the change, as concisely as possible.
<details>
<summary>CEDARScript Guidelines</summary>
<ul>
<li>Use the exact file path for the file that needs to be changed (remember you can only change files that the user added to the chat!).
Examples:
1. `UPDATE FILE "path/to/file"`
2. `UPDATE FUNCTION FROM FILE "path/to/file"`
</li>
<li>Even when being concise, don't use `STDIN` unless user provided a literal source code block directly in message</li>
<li>Each command must have a semicolon at its end</li>
<li>Each CEDARScript command is applied in the same order as they appear. If a command modifies a file, the next command will see the update version of that file, with all changes that were applied by earlier commands.</li>
<li>It's crucial to strive to provide *as concise and small as possible*, targeted CEDARScript commands that each change a given aspect of the program, so that humans can easily understand what's changing</li>
<li>Try *HARD* to minimize the number of unchanged lines in a CEDARScript command and to have a very *concise* script</li>
<li>To move code within a file or function, you *MUST* use the `MOVE SEGMENT` clause.</li>
<li>To specify "REPLACE SEGMENT":
   - Syntax: (STARTING|ENDING) (AT|BEFORE|AFTER); AT means at that same line, BEFORE targets 1 line before, AFTER targets 1 line after.
   - Use specific, unique line snippets as start and end markers;
   - The "STARTING" line marker is one of the lines found in the original code, but trimmed (that is, don't include spaces nor tabs at the sides of the marker).
Same goes for the "ENDING" line marker. Both should be close to the contents to be changed. Both must ALWAYS escape the quote character.
   - The "ENDING" line marker MUST always correspond to a line in the original code that comes AFTER the `STARTING AT` line. 
   - If applying the changes fails, try choosing other, longer lines for the start or end markers.
</li>
</ul>

<details topic="Crucial detail for content inside `WITH CONTENT` blocks">
<summary>Always use the correct 'relative indentation prefix'</summary>
<p>Relative indentation prefix:</p>
<ul>
<li>Its sole purpose is to represent the indentation level for the line where it appears</li>
<li>It must never be used for vertical line positioning (inserting a line before or after another) nor to indicate a sequence of lines</li>
<li>Each line must start with the *relative indentation prefix*;
<p>Syntax: <code>@N:</code> where `N` is the *indentation* level for that line (-2, -1, 0, 1, 2, etc.)</p>
<p>IMMEDIATELY after the prefix, write the left-trimmed line of content (that is, don't add `\\t` characters!)</p>
<p>Example lines using the prefix:</p>
<code>
@0:def myFunction(x):
@1:println("first line in body")
@1:println("second line in body")
@1:if x > 30:
@2:println("x > 30")
@1:return x
</code>
</li>
<li>When line indentation level is incremented by one, `N` *must* be incremented as well! See examples:
<code>
@0:def myFunction(x): # We start with indentation level 0
@1:println("first line in body") # Line indentation level was incremented by 1 because it's the first line in the function body, so N must be incremented by exactly 1
@1:println("second line in body") # Line indentation level remained the same, so N remained the same we well
@1:if x > 30: # Line indentation level had no change, so N must not change for this line!
@2:println("x > 30") # We're now inside the `if` block, so line indentation was incremented. Thus, N *had* to be incremented
@1:return x # This line doesn't belong to the `if` block. It's in the same level as the `if` instruction itself, which is at the base function body level, which has N=1
@0def anotherFunction(): # This line doesn't belong to the `myFunction` body, so it goes back to the same indentation level as the other function's first line: N=0
@1:pass # This line is the first line inside the function body, so we increment indentation by 1. Thus, N *had* to be incremented by 1 as well. 
</code>
</li>
<li>For `REPLACE BODY`, do not include the function signature. Start with the function body at level 0 (@0:)
<li>Understand that the actual indentation characters (spaces or tabs) will be applied by the CEDARScript engine,
adjusting your relative indentation to match the target code's style and position</li>
</ul>
</details>
</details>

When given a code change task:
1. Identify the file to be updated.
2. <p>Determine the best sequence of targeted CEDARScript commands to express the code change in shortest possible way.
Write the initial version of the script inside a ```draft block.
Then, analyze the script you wrote to find problems, syntax errors, etc. Make sure only valid CEDARScript syntax is used.
Finally, write the revised script as a well-formed CEDARScript block, using the correct syntax.
If your script fails, pay attention to the error details inside tag <error-details> and tell me how you can overcome the problem, then try harder to get it right.
</p>
Pay attention to which filenames the user wants you to edit, especially if they are asking you to create a new file.

{lazy_prompt}
ONLY EVER RETURN CODE IN *CEDARScript block*!
CEDARScript commands MUST BE *AS CONCISE AS POSSIBLE*!
Each CEDARScript command MUST have a ';' character at the end!
ALWAYS enclose CEDARScript block using ```CEDARScript before and ``` after the block!
{shell_cmd_reminder}
"""

    example_messages = CedarPromptsBase.example_messages + [
        dict(
            role="user",
            content="""
'''python
class MyClass():
    def myFirstFunction(self, name: str, age: int):
        doSomething(name, age)
    def anotherFunction(self, name: str, age: int):
        self.myFirstFunction(name, age)        
'''
Refactor method myFirstFunction to be a stand alone, top level function.
            """
        ),
        dict(
            role="assistant",
            content="""To make this refactoring, we need to modify the file where the method `myFirstFunction` is defined:

1. Move the method `myFirstFunction` from its original position to the target position.
3. Update the copied function to remove references to `self`
4. Update call sites of the method `myFirstFunction` to call the new top-level function with the same name.

Here's the CEDARScript script:

{fence[0]}CEDARScript
-- 1. Move the method `myFirstFunction` from its original position to the target position
UPDATE STDIN
  MOVE SEGMENT
    STARTING AT "def myFirstFunction(self, name: str, age: int):"
    ENDING BEFORE "def anotherFunction(self, name: str, age: int):"
  INSERT BEFORE "class MyClass():"
    RELATIVE INDENTATION 0;

-- 2. Update the copied function to remove references to `self`
UPDATE FUNCTION
  FROM STDIN
  WHERE NAME = "myFirstFunction"
  REPLACE SEGMENT
    STARTING AT "def myFirstFunction(self, name: str, age: int):"
    ENDING AT "def myFirstFunction(self, name: str, age: int):"
  WITH CONTENT '''
@0:def myFirstFunction(name: str, age: int):
''';

-- 3. Update call sites of the method `myFirstFunction` to call the new top-level function with the same name
UPDATE FUNCTION
  FROM STDIN
  WHERE NAME = "anotherFunction"
  REPLACE BODY
  WITH CONTENT '''
@0:myFirstFunction(name, age)
''';

""",
        ),
    ]
