instructions_addendum = """
####

Use the above instructions to modify the supplied files: {file_list}
Keep and implement the existing function or class stubs, they will be called from unit tests.
Only use standard python libraries, don't suggest installing any packages.
"""


test_failures = """
####

See the testing errors above.
The tests are correct.
Fix the code in {file_list} to resolve the errors.
"""
