# flake8: noqa: E501

from .cedarscript_prompts_base import CedarPromptsBase


class CedarPromptsGrammar(CedarPromptsBase):

    def edit_format_name(self):
        return f"{super().edit_format_name()}-g"

    final_remarks = CedarPromptsBase.final_remarks_brain

    cedarscript_training = """<training><p>Learning CEDARScript</p>
Please read the tree-sitter grammar rules (enclosed by <grammar.js> tags) to learn the syntax and how to use CEDARScript:
<grammar.js>
const SELECT_FILENAMESPATHS_TARGET = seq('FILE', choice('NAMES', 'PATHS'))
const SELECT_OTHER_TARGETS = choice(
  seq('FILE', 'CONTENTS'),
  seq('CLASS', choice('NAMES', 'CONTENTS')),
  seq('FUNCTION', choice('NAMES', 'SIGNATURES', 'CONTENTS')),
  seq('VARIABLE', choice('NAMES', 'CONTENTS')),
  'IDENTIFIERS'
);
/**
- WHOLE: the whole chosen item;
- BODY: Only the function body (its *signature* is *NOT* considered);
*/
const BODY_OR_WHOLE = field('bow', choice('BODY', 'WHOLE'))

/**
<about>CEDARScript, SQL-like language used to express code manipulations (via DDL and DML Write commands) and to help an LLM examine and understand the codebase (via DML Read-Only command)</about>
*/
module.exports = grammar({
  name: 'CEDARScript',

  extras: $ => [
    /\\s|\\r?\\n/,
    $.comment
  ],

  rules: {
    source_file: $ => repeat(seq(
      $._command,
      optional($.command_separator)
    )),

    _command: $ => choice(
      // DDL
      $.create_command,
      $.rm_file_command,
      $.mv_file_command,
      // DML (write)
      $.update_command,
      // DML (Read-Only)
      $.select_command,
      prec(-1, alias($.invalid_move_command, $.error))
    ),
    invalid_move_command: $ => seq(
      'MOVE',
      choice('FILE', 'FUNCTION', 'CLASS', 'VARIABLE'),
    ),
    /**
    Syntax: CREATE FILE "<path/to/new-file>" WITH CONTENT '''<content>''';
    Only for new files. Fails if file already exists.
    */
    create_command: $ => seq(
      'CREATE', $.singlefile_clause,
      'WITH', $.content_clause
    ),

    /**
    Syntax: RM FILE "<path/to/file>";
    Use cases: Delete file from the codebase
    */
    rm_file_command: $ => seq(
      'RM', $.singlefile_clause
    ),

    /**
    Syntax: MV FILE "<source-file>" TO "<target-file>";
    Use cases: Renaming a file, moving a file to another path (target file is overwritten if existing).
    <example><goal>Rename "old.js", then move "config.json" to "production" folder</goal>
    ```CEDARScript
    -- Rename "old.js"
    MV FILE "src/old.js" TO "src/new.js";
    -- Overwrite development config with production config
    MV FILE "production/config.ini" TO "development/config.ini";
    ```
    </example>
    */
    mv_file_command: $ => seq(
      'MV', $.singlefile_clause, $.to_value_clause
    ),

    /**
    Syntax (simplified): UPDATE <singlefile or identifier_from_file> <update type>;
    <use-cases>
    - Creating or replacing classes, functions or other code in existing files/classes/functions
    - Replacing specific lines of existing code
    - Performing complex code transformations using refactoring patterns
    - etc...
    </use-cases>
    */
    update_command: $ => seq(
      'UPDATE',
      choice(
        field('singleFile_clause',
          seq(
            $.singlefile_clause,
            choice(
              $.update_delete_mos_clause,
              $.update_move_mos_clause,
              seq(
                choice(
                  $.insert_clause,
                  $.replace_mos_clause
                ),
                seq('WITH', choice($.content_clause, $.content_from_segment))
              )
            )
          )
        ),
        field('identifierInFile_clause',
          seq(
            $.identifier_from_file,
            choice(
              $.update_delete_region_clause,
              $.update_move_region_clause,
              seq(
                choice(
                  $.insert_clause,
                  $.replace_region_clause
                ),
                seq('WITH', choice($.content_clause, $.content_from_segment))
              )
            )
          )
        ),
        $.update_project_clause
      )
    ),

    insert_clause: $ => seq('INSERT', $.relpos_bai),

    // replace_mos_clause, replace_region_clause:
    /**
    Define what to be replaced in the chosen function, class or file.
    */
    replace_mos_clause: $ => seq('REPLACE', $.marker_or_segment),
    replace_region_clause: $ => seq('REPLACE', $.region_field),
    // ---

    /**
    refactor_language_field: Only language 'rope' is supported. Works only with Python codebases.
    */
    refactor_language_field: $ => seq('REFACTOR LANGUAGE', field('refactor_language', $.string)),
    pattern_field: $ => seq('PATTERN', field('pattern', $.string)),
    goal_field: $ => seq('GOAL', field('goal', $.string)),

    // update_delete_region_clause, update_delete_mos_clause:
    /**
    *NOT* top-level command. Used inside the `UPDATE` command to specify deletion of code parts.
    */
    update_delete_region_clause: $ => seq('DELETE', $.region_field),
    update_delete_mos_clause: $ => seq('DELETE', $.marker_or_segment),
    // ---

    /**
    update_project_clause: Advanced pattern-based refactorings.
    Indirectly use the `Restructure` class in the 'Rope' refactoring library to perform complex code transformations using patterns.
    These patterns can match and replace code structures in your project.
    */
    update_project_clause: $ => seq('PROJECT', $.refactor_language_field,
      'WITH', $.pattern_field,
      'WITH', $.goal_field,
    ),
    update_move_clause_destination: $ => field('move_destination', seq(
      optional(seq('TO', $.singlefile_clause)),
      $.insert_clause,
      optional($.relative_indentation)
    )),

    // update_move_mos_clause, update_move_region_clause
    /**
    `MOVE` is only used as part of the UPDATE command for moving code within a file.
    Unlike CREATE, RM, or UPDATE, it is *NOT* a top-level command.
    */
    update_move_mos_clause: $ => seq('MOVE', field('move_mos_source', $.marker_or_segment), $.update_move_clause_destination),
    update_move_region_clause: $ => seq('MOVE', field('move_region_source', $.region_field), $.update_move_clause_destination),
    // ---

    /**
    Syntax: (FUNCTION|CLASS) FROM FILE "<path/to/file>" WHERE <where...> [OFFSET <offset>]
    Use cases: Specify a function or class of a given file.
    <params>
    - `where...`: Identifies a function or class as the item of interest in the file.
    - `offset`: Specifies how many items to skip. See details in `offset_clause`.
    </params>
    */
    identifier_from_file: $ => seq(
      choice('FUNCTION', 'CLASS'), 'FROM', $.singlefile_clause,
      $.where_clause,
      optional($.offset_clause)
    ),

    /**
    Read-only command. Used to glean information about the code base being examined.
    <use-cases>
    - Understanding code structure;
    - Finding relevant files/classes/functions/variables that may deal with a certain topic
       -- (ex.: if a user may want to find all places that deal with payments, search for 'payment')
    - Displaying code elements to user
    - Generating documentation;
    - Automating code navigation.
    </use-cases>
    */
    select_command: $ => seq(
      'SELECT',
      choice(
        seq(field('file_names_paths_target', $.select_filenamespaths_target), 'FROM', $.multifile_clause),
        seq(field('single_or_multifile_target', $.select_other_target), 'FROM', choice($.singlefile_clause, $.multifile_clause))
      ),
      optional($.where_clause),
      optional($.limit_clause)
    ),

    select_filenamespaths_target: $ => SELECT_FILENAMESPATHS_TARGET,
    select_other_target: $ => SELECT_OTHER_TARGETS,

    where_clause: $ => seq(
      'WHERE',
      field('condition', $.condition)
    ),

    conditions_left: $ => choice(
      'NAME',
      'PATH'
    ),
    operator: $ => choice('=', 'LIKE'),
    condition: $ => seq($.conditions_left, $.operator, field('value_or_pattern', $.string)),

    to_value_clause: $ => seq('TO', field('value', $.single_quoted_string)),
    /**
    Syntax: FILE "<path/to/file>"
    Use cases: Specify a file
    */
    singlefile_clause: $ => seq('FILE', field('path', $.string)),
    multifile_clause: $ => seq(
      choice('PROJECT', seq('DIRECTORY', field('directory', $.single_quoted_string))),
      optional($.maxdepth_clause)
    ),

    maxdepth_clause: $ => seq('MAX DEPTH', field('depth', $.number)),

    // <specifying-locations-in-code>
    /**
    lineMarker: Points to specific line via its trimmed contents.
    Use `OFFSET <n>` to pinpoint which (if there are 2 or more with same content)
    */
    lineMarker: $ => seq('LINE', field('lineMarker', $.string), optional($.offset_clause)),
    /**
    identifierMarker: Points to an identifier (variable, function or class).
    Use `OFFSET <n>` to pinpoint which (if there are 2 or more with same name)
    */
    identifierMarker: $ => seq(field('identifier', choice('VARIABLE', 'FUNCTION', 'CLASS')), field('identifierMarker', $.string), optional($.offset_clause)),
    marker: $ => choice($.lineMarker, $.identifierMarker),
    /**
    relpos_beforeafter: Points to region immediately before or after a `marker`
    */
    relpos_beforeafter: $ => field('relpos_beforeafter', seq(choice('BEFORE', 'AFTER'), $.marker)),
    /**
    relpos_inside: Points to inside `identifierMarker` (its top or bottom region).
    Use cases: When inserting content at the top or bottom of a function, class or file.
    */
    relpos_inside: $ => seq('INSIDE', field('inside', $.identifierMarker), optional(field('topOrBottom', choice('TOP', 'BOTTOM')))),
    relpos_bai: $ => field('relpos_bai', choice($.relpos_beforeafter, $.relpos_inside)),
    /**
    relpos_at: points to a specific `lineMarker`
    */
    relpos_at: $ => seq('AT', field('at', $.lineMarker)),
    /**
    relpos_segment_start: Points to start of segment
    */
    relpos_segment_start: $ => seq('STARTING', field('starting', choice($.relpos_at, $.relpos_beforeafter))),
    /**
    relpos_segment_end: Points to end of segment
    */
    relpos_segment_end: $ => seq('ENDING', field('ending', choice($.relpos_at, $.relpos_beforeafter))),
    /**
    segment: Points to segment identified by a start and an end pointer
    */
    segment: $ => field('segment', seq('SEGMENT', $.relpos_segment_start, $.relpos_segment_end)),
    marker_or_segment: $ => field('mos', choice($.marker, $.segment)),
    /** region_field:
    - BODY_OR_WHOLE: pre-defined regions
    - marker_or_segment: more flexible region selection
    */
    region_field: $ => field('region', choice(BODY_OR_WHOLE, $.marker_or_segment)),

    /**
    Field `offset`: Integer to identify how many occurrences to skip. *MANDATORY* iff there are 2 or more occurrences.
    <examples>
    <li>`OFFSET 0` is the default. It means to skip 0 items (so, points to the *1st* occurrence).</li>
    <li>`OFFSET 1` skips 1 item, so points to the *2nd* occurrence</li>
    <li>`OFFSET 2` skips 2 items, so points to the *3rd* occurrence</li>
    <li>`OFFSET n` skips n items, thus specifies the (n+1)-th occurrence</li>
    </examples>
    */
    offset_clause: $ => seq('OFFSET', field('offset', $.number)),

    // </specifying-locations-in-code>

    limit_clause: $ => seq('LIMIT', field('count', $.number)),

    /**
    relative_indentation: Helps maintain proper code structure when inserting or replacing code.
    Sets the indentation level relative to the context specified in the command:
    <li>`INSIDE (FUNCTION|CLASS)`: Reference is the body of the function or class</li>
    <li>`(BEFORE|AFTER) (LINE|FUNCTION|CLASS)`: Reference is line, function, or class, regardless of whether BEFORE or AFTER is used</li>
    When `rel_indent` is 0, code is put at the same level as the reference.
    */
    relative_indentation: $ => seq('RELATIVE INDENTATION', field('rel_indent', $.number)),

    content_from_segment: $ => seq(
      optional($.singlefile_clause),
      $.marker_or_segment,
      optional($.relative_indentation)
    ),

    /**
<details topic="Relative Indent Strings">
<summary>A relative indent prefix is used within strings in CONTENT blocks to simplify matching indentation with the existing code being changed</summary>
<p>Syntax:</p>
<ol>
<li>`@N:` is the relative indent prefix</li>
<li>`N` is an integer representing the relative indent *level* (can be negative)</li>
<li>`content` is the actual code or text for that line</li>
</ol>
<examples>
<li>'@7:single-quote-string'</li>
<li>"@-3:double-quote-string"</li>
<li>r"@0:raw-string"</li>
<li>'''
@0:multi
@-1:line
'''</li>
<li>\"\"\"
@0:multi
@-1:line
\"\"\"</li>
</examples>

<p>Key points:</p>
<ol>
<li>Each line must start with `@N:` where `N` represents the indentation level</li>
<li>Indentation level should change logically with code structure:
   - Increment N when entering a new block (class body, function body, if statement, loop, etc.)
   - Decrement N when exiting a block
 </li>
<li>The actual content follows immediately after the prefix (@N:)</li>
</ol>

<example>
[...] WITH CONTENT '''
@0:class myClass:
@1:def myFunction(param):
@2:if param > 0:
@3:print("Positive")
@2:else:
@3:print("Non-positive")
@2:return param * 2
@0:class nextClass:
'''
</example>

Remember: The relative indentation prefix (@N:) is used to indicate the logical structure
of the code. The CEDARScript interpreter will handle the actual formatting and indentation
in the target code file.
    */
    content_clause: $ => seq('CONTENT', field('content', $.string)),

    escape_sequence: $ => token(seq(
      '\\\\',
      choice(
        /[abfnrtv\\\\"']/,
        /\\d{1,3}/,
        /x[0-9a-fA-F]{2}/,
        /u[0-9a-fA-F]{4}/,
        /U[0-9a-fA-F]{8}/,
        /N\\{[^}]+\\}/
      )
    )),

    string: $ => choice(
      $.raw_string,
      $.single_quoted_string,
      $.multi_line_string
    ),
    raw_string: $ => choice(
      seq(
        'r"',
        repeat(/./),
        '"'
      ),
      seq(
        "r'",
        repeat(/./),
        "'"
      ),
      seq(
        'r\"\"\"',
        repeat(/./),
        '\"\"\"'
      ),
      seq(
        "r'''",
        repeat(/./),
        "'''"
      )
    ),
    single_quoted_string: $ => choice(
      seq(
        "'",
        repeat(choice(
          /[^'\\\\\\n]/,
          $.escape_sequence
        )),
        "'"
      ),
      seq(
        '"',
        repeat(choice(
          /[^"\\\\\\n]/,
          $.escape_sequence
        )),
        '"'
      )
    ),
    /**
    multi_line_string: Also useful to avoid escaping quotes
    */
    multi_line_string: $ => choice(
      seq(
        '\"\"\"',
        repeat(choice(
          /[^"\\\\]/,
          '"',
          '""',
          $.escape_sequence
        )),
        '\"\"\"'
      ),
      seq(
        "'''",
        repeat(choice(
          /[^'\\\\]/,
          "'",
          "''",
          $.escape_sequence
        )),
        "'''"
      )
    ),

    number: $ => /\\d+/,

    comment: $ => token(seq('--', /.*/)),

    command_separator: $ => ';'

  }
});
</grammar.js>
"""

    # Appears twice (as SYSTEM and as USER):
    system_reminder = """When presented with a code change task:
<action>
<step>Identify the files to be updated</step>
<step>Determine the best, concise sequence of targeted CEDARScript commands to express the code change in shortest possible way.
Super careful to avoid syntax errors.</step>
<step>If your script fails, carefully the error details inside tag <error-details> and tell me how you can overcome the problem, then try harder to get it right.
</step>
</action>
<important>
<ul>
<li>Pay attention to which filenames the user wants you to edit, especially if they are asking you to create a new file</li>
<li>Use the exact file path for the file that needs to be changed (remember you can only change files that the user added to the chat!)</li>
<li>Even when being concise, don't use `/dev/stdin` unless user provided a literal source code block directly in message</li>
<li>Each CEDARScript command is applied in the same order as they appear. If a command fails to be applied, all commands before it were correctly applied (don't retry those!). Once a command is applied on a file, the next command will see the update version of that file, with all changes that were applied by earlier commands.</li>
<li>It's crucial to strive to provide *as concise and small as possible*, targeted CEDARScript commands that each change a given aspect of the program, so that humans can easily understand what's changing</li>
<li>Try *HARD* to minimize the number of unchanged lines in a CEDARScript command and to have a very *concise* script</li>
<li>To move code within a file or function, you *MUST* use the `UPDATE ... MOVE ...` construct to minimize script size (DON'T use `WITH CONTENT`)</li>
<li>Prefer using multiline_string (enclosed in ''') even for single line content (provides better indentation)</li>
<li>Understand that the actual indentation characters (spaces or tabs) will be applied by the CEDARScript engine,
adjusting your relative indentation to match the target code's style and position</li>
</ul>

{lazy_prompt}
ONLY EVER RETURN CODE IN *CEDARScript block*!
CEDARScript commands MUST BE *AS CONCISE AS POSSIBLE*!
ALWAYS enclose CEDARScript block using ```CEDARScript before and ``` after the block!
{shell_cmd_reminder}
"""

    example_messages = CedarPromptsBase.example_messages + [
        dict(
            role="user",
            content="""
'''python
class MyClass(NamedTuple):
    instance_var_1: str = '4r3'
    def myFirstFunction(
        self, name: str,
        age: int
    ):
        if age > 70
            a = doSomething(name, age)
        return a + 5 + len(self.instance_var_1) * 7
    def middle(self):
        pass
    def anotherFunction(self, name: str, age: int):
        b = checkVal(45, "strict", self.myFirstFunction(name, age), 8, "tops")
        bb = checkVal(7, "lax", self.myFirstFunction(name, age), 2, "bottom")
        c = "x" + '"' + "'" + "z"
        print("calc d...")
        d = checkVal(45, "strict", self.myFirstFunction(name, age), 8, "tops")
        print("calc dd...")
        print("takes longer...")
        dd = checkVal(4455, "aasdf", '33se"asd',
          "strict", 8, 
          "tops", "xx",
          '9"f', "as'df", self.myFirstFunction(name, age))
        return b * 3
'''
Refactor method myFirstFunction to be a stand alone, top level function.
            """
        ),
        dict(
            role="assistant",
            content="""Here's my plan to make this refactoring:
1. Move the `myFirstFunction` method from the `MyClass` class, placing it at the top level, just before the line where its class starts;
2. Update the copied function to remove references to `self` and declare any required instance members as function parameters;
3. Update call sites of the method `myFirstFunction` to call the new top-level function with the same name, passing any instance members as arguments;

Here's the CEDARScript script:

{fence[0]}CEDARScript
-- 1. Move the `myFirstFunction` method from the `MyClass` class, placing it at the top level, just before the line where its class starts.
UPDATE FUNCTION
  FROM FILE "/dev/stdin"
  WHERE NAME = "myFirstFunction"
MOVE WHOLE
INSERT BEFORE LINE "class MyClass():" -- using the line where the method's class starts as 'reference mark' increases chances of the command being correctly applied.
  RELATIVE INDENTATION 0; -- the block of code being moved wil start at the same indentation as the 'reference mark'

-- 2. Update the copied function to remove references to `self`, now declaring `instance_var_1` as parameter
UPDATE FUNCTION
FROM FILE "/dev/stdin"
WHERE NAME = "myFirstFunction"
REPLACE SEGMENT
    STARTING AFTER LINE "def myFirstFunction("
    ENDING AT LINE "self, name: str,"
WITH CONTENT '''
@1:instance_var_1: str, name: str,
''';
UPDATE FUNCTION
FROM FILE "/dev/stdin"
WHERE NAME = "myFirstFunction"
REPLACE SEGMENT
  STARTING AFTER LINE "a = doSomething(name, age)"
  ENDING AT LINE "return a + 5 + len(self.instance_var_1) * 7"
-- `@-1:` used because the return statement is 1 indent level to the *left* of the STARTING reference mark
WITH CONTENT '''
@-1:return a + 5 + len(instance_var_1) * 7
''';

-- 3. Update ALL call sites of the method `myFirstFunction` to call the new top-level function with the same name, passing `instance_var_1` as argument
UPDATE FUNCTION
  FROM FILE "/dev/stdin"
  WHERE NAME = "anotherFunction"
  REPLACE SEGMENT
    STARTING AFTER LINE "def anotherFunction(self, name: str, age: int):"
    ENDING BEFORE LINE '''c = "x" + '"' + "'" + "z"''' -- multi-line string used to avoid escaping `'` and `"`
  WITH CONTENT '''
@1:b = checkVal(45, "strict", myFirstFunction(instance_var_1, name, age), 8, "tops")
@1:bb = checkVal(7, "lax", myFirstFunction(instance_var_1, name, age), 2, "bottom")
''';
UPDATE FUNCTION
  FROM FILE "/dev/stdin"
  WHERE NAME = "anotherFunction"
  REPLACE LINE 'd = checkVal(45, "strict", self.myFirstFunction(name, age), 8, "tops")'
  WITH CONTENT '''
@0:d = checkVal(45, "strict", myFirstFunction(instance_var_1, name, age), 8, "tops")
''';
UPDATE FUNCTION
  FROM FILE "/dev/stdin"
  WHERE NAME = "anotherFunction"
  REPLACE SEGMENT
    STARTING AT LINE \"\"\"'9"f', "as'df", self.myFirstFunction(name, age))\"\"\" -- multi-line string used to avoid escaping `'` and `"`
    ENDING BEFORE LINE 'return b * 3'
  WITH CONTENT '''
@0:'9"f', "as'df", myFirstFunction(instance_var_1, name, age))
''';
{fence[1]}

Notes:
1. As the code to be changed was provided in your message, we're using file name "/dev/stdin".
2. The line "class MyClass():" was used as the insertion reference to reduce any chances of failing to apply the changes.
""",
        ),
        dict(
            role="user",
            content="""
'''python
class MyClass(NamedTuple):
    instance_var_1: str = '4r3'
    def myFirstFunction(self, name: str, age: int):
        \"\"\"Lorem ipsum dolor sit amet
        Args:
            name: name
            age: age
        \"\"\"
        if age > 70
          a = doSomething(name, age)
          return a + 5 + len(self.instance_var_1) * 7
      def middle(self):
          pass
      def anotherFunction(self, name: str, age: int):
          # Check and store in 'b' and 'bb'
          b = checkVal(45, "strict", self.myFirstFunction(name, age), 8, "tops")
          bb = checkVal(7, "lax", self.myFirstFunction(name, age), 2, "bottom")
          return b + bb
  '''
  Refactor method myFirstFunction to be a stand alone, top level function.
              """
        ),
        dict(
            role="assistant",
            content="""Here's my plan to make this refactoring:
1. Move the `myFirstFunction` method from the `MyClass` class, placing it at the top level, just before the line where its class starts;
2. Update the copied function to remove references to `self` and declare any required instance members as function parameters;
3. Update call sites of the method `myFirstFunction` to call the new top-level function with the same name, passing any instance members as arguments;

Here's the CEDARScript script:

{fence[0]}CEDARScript
-- 1. Move the `myFirstFunction` method from the `MyClass` class, placing it at the top level, just before the line where its class starts.
UPDATE FUNCTION
  FROM FILE "/dev/stdin"
  WHERE NAME = "myFirstFunction"
MOVE WHOLE
INSERT BEFORE LINE "class MyClass():" -- using the line where the method's class starts as 'reference mark' increases chances of the command being correctly applied.
  RELATIVE INDENTATION 0; -- the block of code being moved wil start at the same indentation as the 'reference mark'

-- 2. Update the copied function to remove references to `self`, now declaring `instance_var_1` as parameter
UPDATE FUNCTION
FROM FILE "/dev/stdin"
WHERE NAME = "myFirstFunction"
REPLACE SEGMENT
    STARTING AT LINE "def myFirstFunction(self, name: str, age: int):"
    ENDING BEFORE LINE '\"\"\"Lorem ipsum dolor sit amet' -- Chose the first line below the starting line to get the shortest segment possible
WITH CONTENT '''
@0:def myFirstFunction(instance_var_1: str, name: str, age: int):
''';
UPDATE FUNCTION
FROM FILE "/dev/stdin"
WHERE NAME = "myFirstFunction"
REPLACE SEGMENT
  STARTING AFTER LINE "a = doSomething(name, age)"
  ENDING AT LINE "return a + 5 + len(self.instance_var_1) * 7"
WITH CONTENT '''
@-1:return a + 5 + len(instance_var_1) * 7
''';

-- 3. Update ALL call sites of the method `myFirstFunction` to call the new top-level function with the same name, passing `instance_var_1` as argument
UPDATE FUNCTION
FROM FILE "/dev/stdin"
WHERE NAME = "anotherFunction"
  REPLACE SEGMENT
    STARTING AFTER LINE "# Check and store in 'b' and 'bb'"
    ENDING BEFORE LINE "return b + bb"
  WITH CONTENT '''
@0:b = checkVal(45, "strict", myFirstFunction(instance_var_1, name, age), 8, "tops")
@0:bb = checkVal(7, "lax", myFirstFunction(instance_var_1, name, age), 2, "bottom")
''';
{fence[1]}

Notes:
1. As the code to be changed was provided in your message, we're using file name "/dev/stdin".
2. The line "class MyClass():" was used as the insertion reference to reduce any chances of failing to apply the changes.
""",
        ),
    ]
