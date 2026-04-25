watch_code_prompt = """
I've written your instructions in comments in the files and marked them with "ai"
You can see the "AI" comments shown below (marked with █).
Find them in the files I've shared with you, and follow their instructions.

You MUST use your edit format to actually modify the files to implement the requested changes.
Do not just explain the changes or print them to the chat.

After completing those instructions, also be sure to remove all the "AI" comments from the files too.
"""

watch_ask_prompt = """/ask
Find the "AI" comments below (marked with █) in the files I've shared with you.
They contain my questions that I need you to answer and other instructions for you.
"""
