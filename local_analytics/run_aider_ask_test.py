import subprocess
import time
import os
import sys
import threading
import queue

# Define the aider command
# Use the full path to the .env file
# Assumes the script is run from the project root or a location where
# ~/Dev/aider/.env is the correct path.
# Using sys.executable ensures the script runs aider with the same python env.
aider_command = [
    sys.executable,
    "-m", "aider",
    "--env-file", os.path.expanduser("~/Dev/aider/.env")
]

# Inputs to send to aider
inputs = [
    "/ask",
    "what is the reflection error",
    "/exit"
]

# Expected prompts (as bytes, since we read bytes)
# Use strip() because rich might add spaces or other control characters
MAIN_PROMPT = b"> "
EDIT_PROMPT = b"Apply edits? (y/n/commit/diff/quit) "

def enqueue_output(out, queue):
    """Helper function to read output from a stream and put it in a queue."""
    # Read line by line
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()

def run_aider_session():
    print(f"[SCRIPT] Starting aider with command: {' '.join(aider_command)}")

    # Start the subprocess
    # Use bufsize=1 for line buffering
    # universal_newlines=False to read bytes and reliably detect byte prompts
    # stderr is also piped as rich often prints to stderr
    process = subprocess.Popen(
        aider_command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
        universal_newlines=False
    )

    # Queues for stdout and stderr
    q_stdout = queue.Queue()
    q_stderr = queue.Queue()

    # Start threads to read stdout and stderr asynchronously
    t_stdout = threading.Thread(target=enqueue_output, args=(process.stdout, q_stdout))
    t_stderr = threading.Thread(target=enqueue_output, args=(process.stderr, q_stderr))
    t_stdout.daemon = True # Thread dies with the main program
    t_stderr.daemon = True
    t_stdout.start()
    t_stderr.start()

    # Give aider a moment to start and print initial messages
    time.sleep(3) # Increased initial sleep slightly

    current_input_index = 0
    # State machine: WAITING_FOR_MAIN_PROMPT, WAITING_FOR_RESPONSE
    state = "WAITING_FOR_MAIN_PROMPT"

    print(f"[SCRIPT] Initial state: {state}")

    try:
        # Continue as long as the process is running OR there is output in the queues
        while process.poll() is None or not q_stdout.empty() or not q_stderr.empty():
            try:
                # Get a line from stdout queue with a timeout
                # A small timeout allows the loop to check process.poll() and stderr queue
                line = q_stdout.get(timeout=0.05)
                sys.stdout.buffer.write(line)
                sys.stdout.buffer.flush()

                # Check for prompts based on the state
                if state == "WAITING_FOR_MAIN_PROMPT":
                    # Check if the line ends with the main prompt bytes (after stripping)
                    if line.strip().endswith(MAIN_PROMPT.strip()):
                         print("\n[SCRIPT] Detected main prompt.")
                         if current_input_index < len(inputs):
                             command = inputs[current_input_index]
                             print(f"[SCRIPT] Sending: {command}")
                             process.stdin.write((command + "\n").encode()) # Encode string to bytes
                             process.stdin.flush()
                             current_input_index += 1
                             state = "WAITING_FOR_RESPONSE" # After sending input, wait for response/next prompt
                             print(f"[SCRIPT] State transition: {state}")
                         else:
                             # Should not happen if /exit is the last input, but as a safeguard
                             print("[SCRIPT] No more inputs defined, waiting for process exit.")
                             state = "SESSION_COMPLETE"
                             print(f"[SCRIPT] State transition: {state}")

                elif state == "WAITING_FOR_RESPONSE":
                    # While waiting for response, we might see an edit prompt or the main prompt
                    if line.strip().endswith(EDIT_PROMPT.strip()):
                        print("\n[SCRIPT] Detected edit prompt.")
                        print("[SCRIPT] Sending: n")
                        process.stdin.write(b"n\n") # Send 'n' to decline edits
                        process.stdin.flush()
                        # Stay in WAITING_FOR_RESPONSE state, as declining might lead to another prompt
                        print(f"[SCRIPT] State remains: {state}")
                    elif line.strip().endswith(MAIN_PROMPT.strip()):
                         print("\n[SCRIPT] Detected main prompt (while waiting for response).")
                         # Response finished, now ready for next main input
                         state = "WAITING_FOR_MAIN_PROMPT"
                         print(f"[SCRIPT] State transition: {state}")

            except queue.Empty:
                # No output from stdout, check stderr queue
                try:
                    err_line = q_stderr.get(timeout=0.01)
                    sys.stderr.buffer.write(err_line)
                    sys.stderr.buffer.flush()
                except queue.Empty:
                    # No output from either queue, check if process is still running
                    if process.poll() is not None:
                        # Process exited and queues are empty, we are done
                        print("[SCRIPT] Process exited and queues are empty.")
                        break
                    # If process is still running but no output, just continue loop and wait

            # Add a small sleep to prevent tight loop if process is slow to produce output
            time.sleep(0.01)

        # End of while loop: process exited and queues are drained

    except Exception as e:
        print(f"[SCRIPT] An error occurred: {e}")
        # Attempt to read remaining output before terminating
        try:
            # Give threads a moment to finish putting data in queues
            t_stdout.join(timeout=1)
            t_stderr.join(timeout=1)
            # Drain queues
            while not q_stdout.empty():
                 sys.stdout.buffer.write(q_stdout.get_nowait())
                 sys.stdout.buffer.flush()
            while not q_stderr.empty():
                 sys.stderr.buffer.write(q_stderr.get_nowait())
                 sys.stdout.buffer.flush()
        except Exception as e_drain:
             print(f"[SCRIPT] Error draining queues: {e_drain}")


        if process.poll() is None:
             print("[SCRIPT] Terminating process...")
             process.terminate() # Ensure process is terminated on error
             try:
                 process.wait(timeout=5)
             except subprocess.TimeoutExpired:
                 print("[SCRIPT] Process did not terminate, killing...")
                 process.kill()
                 process.wait()


    finally:
        # Ensure process is waited upon if not already
        if process.poll() is None:
             print("[SCRIPT] Waiting for process to finish...")
             process.wait()

        # Final drain of queues just in case
        while not q_stdout.empty():
             sys.stdout.buffer.write(q_stdout.get_nowait())
             sys.stdout.buffer.flush()
        while not q_stderr.empty():
             sys.stderr.buffer.write(q_stderr.get_nowait())
             sys.stderr.buffer.flush()

        print(f"[SCRIPT] Aider process finished with return code {process.returncode}")

if __name__ == "__main__":
    run_aider_session()
