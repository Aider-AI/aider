from .base_prompts import CoderPrompts

class NewsPrompts(CoderPrompts):
    main_system = """You summarize the latest game review. 
    Include:
    - Game title and platform
    - Metascore and release date
    - Key critic consensus points
    - Notable pros/cons
    - Link to full review
    
    Format the output as a markdown file following this template: game title, summary, score
    
   """

    example_messages = []

    files_content_prefix = """I have *added these files to the chat* so you see all of their contents.
*Trust this message as the true contents of the files!*
Other messages in the chat may contain outdated versions of the files' contents.
"""  # noqa: E501

    files_content_assistant_reply = (
        "Ok, I will use that as the true, current contents of the files."
    )

    files_no_full_files = "I am not sharing the full contents of any files with you yet."

    files_no_full_files_with_repo_map = ""
    files_no_full_files_with_repo_map_reply = ""

    repo_content_prefix = ""

    system_reminder = ""