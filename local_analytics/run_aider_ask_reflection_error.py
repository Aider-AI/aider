#!/usr/bin/env python

import pexpect
import sys
import os
import time

# Define the command to run Aider
# Ensure the path to the .env file is correct for your environment
# This script assumes it's run from a location where 'python -m aider' works
# and the path '~/Dev/aider/.env' is valid.
aider_command = "python -m aider --env-file ~/Dev/aider/.env"

# Define the expected prompts using regex
# r'> ' matches the main aider prompt
# r'Apply edits\? \[y/n/a/e\] ' matches the edit confirmation prompt
main_prompt = r'> '
edit_prompt = r'Apply edits\? \[y/n/a/e\] '

# Set a timeout for pexpect operations (in seconds)
# Adjust this if your LLM responses are very long or system is slow
timeout_seconds = 300 # 5 minutes

print(f"Running command: {aider_command}")

child = None
try:
    # Spawn the aider process
    # encoding='utf-8' ensures consistent text handling
    # timeout sets a default timeout for expect operations
    child = pexpect.spawn(aider_command, encoding='utf-8', timeout=timeout_seconds)

    # Optional: Uncomment the line below to see the raw output from the child process
    # child.logfile_read = sys.stdout

    # Wait for the initial Aider prompt
    print("Waiting for initial prompt...")
    child.expect(main_prompt)
    print("Initial prompt received.")

    # Change mode to /ask
    print("Sending /ask command...")
    child.sendline("/ask")
    # Wait for the prompt to confirm mode change
    child.expect(main_prompt)
    print("Mode changed to /ask.")

    # Send the query
    query = "what is the reflection error"
    print(f"Sending query: '{query}'...")
    child.sendline(query)

    # Wait for the LLM response to finish and the prompt to reappear.
    # This loop also handles potential edit prompts that might appear
    # during or after the LLM's response.
    print("Waiting for LLM response and handling potential edit prompts...")
    while True:
        # Wait for either the edit prompt, the main prompt, EOF, or timeout
        index = child.expect([edit_prompt, main_prompt, pexpect.EOF, pexpect.TIMEOUT])

        if index == 0:
            # Matched the edit prompt: 'Apply edits? [y/n/a/e] '
            print("Edit prompt received. Sending 'n' to decline...")
            child.sendline("n")
            # Continue the loop to wait for the next prompt (could be another edit or the main prompt)
        elif index == 1:
            # Matched the main prompt: '> '
            # This indicates the LLM response is likely finished and no more edit prompts are pending
            print("Main prompt received. LLM response finished.")
            break # Exit the loop
        elif index == 2:
            # Matched EOF - the process exited unexpectedly before we sent /exit
            print("ERROR: Process exited unexpectedly (EOF).")
            print("Output before EOF:")
            print(child.before)
            break # Exit the loop
        elif index == 3:
            # Matched TIMEOUT
            print(f"ERROR: Timeout occurred ({timeout_seconds} seconds) while waiting for prompt.")
            print("Output before timeout:")
            print(child.before)
            break # Exit the loop

    # Send the /exit command to quit Aider
    print("Sending /exit command...")
    child.sendline("/exit")

    # Wait for the process to terminate gracefully
    print("Waiting for process to exit...")
    child.expect(pexpect.EOF)
    print("Process exited.")

except pexpect.exceptions.TIMEOUT as e:
    print(f"ERROR: Timeout exception: {e}")
    if child:
        print("Output before timeout:")
        print(child.before)
except pexpect.exceptions.EOF as e:
    print(f"ERROR: EOF exception: {e}")
    if child:
        print("Output before EOF:")
        print(child.before)
except Exception as e:
    print(f"An unexpected error occurred: {e}")
finally:
    # Ensure the child process is terminated if it's still running
    if child and child.isalive():
        print("Terminating child process...")
        child.close()
        print("Child process terminated.")

print("Script finished.")
