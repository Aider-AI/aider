import base64
import hashlib
import http.server
import os
import secrets
import socketserver
import threading
import time
import webbrowser
from urllib.parse import parse_qs, urlparse

import requests

from aider import urls
from aider.io import InputOutput


def check_openrouter_tier(api_key):
    """
    Checks if the user is on a free tier for OpenRouter.

    Args:
        api_key: The OpenRouter API key to check.

    Returns:
        A boolean indicating if the user is on a free tier (True) or paid tier (False).
        Returns True if the check fails.
    """
    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/auth/key",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=5,  # Add a reasonable timeout
        )
        response.raise_for_status()
        data = response.json()
        # According to the documentation, 'is_free_tier' will be true if the user has never paid
        return data.get("data", {}).get("is_free_tier", True)  # Default to True if not found
    except Exception:
        # If there's any error, we'll default to assuming free tier
        return True


def try_to_select_default_model():
    """
    Attempts to select a default model based on available API keys.
    Checks OpenRouter tier status to select appropriate model.

    Returns:
        The name of the selected model, or None if no suitable default is found.
    """
    # Special handling for OpenRouter
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_key:
        # Check if the user is on a free tier
        is_free_tier = check_openrouter_tier(openrouter_key)
        if is_free_tier:
            return "openrouter/google/gemini-2.5-pro-exp-03-25:free"
        else:
            return "openrouter/anthropic/claude-3.7-sonnet"

    # Select model based on other available API keys
    model_key_pairs = [
        ("ANTHROPIC_API_KEY", "sonnet"),
        ("DEEPSEEK_API_KEY", "deepseek"),
        ("OPENAI_API_KEY", "gpt-4o"),
        ("GEMINI_API_KEY", "gemini/gemini-2.5-pro-exp-03-25"),
        ("VERTEXAI_PROJECT", "vertex_ai/gemini-2.5-pro-exp-03-25"),
    ]

    for env_key, model_name in model_key_pairs:
        api_key_value = os.environ.get(env_key)
        if api_key_value:
            return model_name

    return None


def offer_openrouter_oauth(io, analytics):
    """
    Offers OpenRouter OAuth flow to the user if no API keys are found.

    Args:
        io: The InputOutput object for user interaction.
        analytics: The Analytics object for tracking events.

    Returns:
        True if authentication was successful, False otherwise.
    """
    # No API keys found - Offer OpenRouter OAuth
    io.tool_output("OpenRouter provides free and paid access to many LLMs.")
    # Use confirm_ask which handles non-interactive cases
    if io.confirm_ask(
        "Login to OpenRouter or create a free account?",
        default="y",
    ):
        analytics.event("oauth_flow_initiated", provider="openrouter")
        openrouter_key = start_openrouter_oauth_flow(io, analytics)
        if openrouter_key:
            # Successfully got key via OAuth, use the default OpenRouter model
            # Ensure OPENROUTER_API_KEY is now set in the environment for later use
            os.environ["OPENROUTER_API_KEY"] = openrouter_key
            # Track OAuth success leading to model selection
            analytics.event("oauth_flow_success")
            return True

        # OAuth failed or was cancelled by user implicitly (e.g., closing browser)
        # Error messages are handled within start_openrouter_oauth_flow
        analytics.event("oauth_flow_failure")
        io.tool_error("OpenRouter authentication did not complete successfully.")
        # Fall through to the final error message

    return False


def select_default_model(args, io, analytics):
    """
    Selects a default model based on available API keys if no model is specified.
    Offers OAuth flow for OpenRouter if no keys are found.

    Args:
        args: The command line arguments object.
        io: The InputOutput object for user interaction.
        analytics: The Analytics object for tracking events.

    Returns:
        The name of the selected model, or None if no suitable default is found.
    """
    if args.model:
        return args.model  # Model already specified

    model = try_to_select_default_model()
    if model:
        io.tool_warning(f"Using {model} model with API key from environment.")
        analytics.event("auto_model_selection", model=model)
        return model

    no_model_msg = "No LLM model was specified and no API keys were provided."
    io.tool_warning(no_model_msg)

    # Try OAuth if no model was detected
    offer_openrouter_oauth(io, analytics)

    # Check again after potential OAuth success
    model = try_to_select_default_model()
    if model:
        return model

    io.offer_url(urls.models_and_keys, "Open documentation URL for more info?")


# Helper function to find an available port
def find_available_port(start_port=8484, end_port=8584):
    for port in range(start_port, end_port + 1):
        try:
            # Check if the port is available by trying to bind to it
            with socketserver.TCPServer(("localhost", port), None):
                return port
        except OSError:
            # Port is likely already in use
            continue
    return None


# PKCE code generation
def generate_pkce_codes():
    code_verifier = secrets.token_urlsafe(64)
    hasher = hashlib.sha256()
    hasher.update(code_verifier.encode("utf-8"))
    code_challenge = base64.urlsafe_b64encode(hasher.digest()).rstrip(b"=").decode("utf-8")
    return code_verifier, code_challenge


# Function to exchange the authorization code for an API key
def exchange_code_for_key(code, code_verifier, io):
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/auth/keys",
            headers={"Content-Type": "application/json"},
            json={
                "code": code,
                "code_verifier": code_verifier,
                "code_challenge_method": "S256",
            },
            timeout=30,  # Add a timeout
        )
        response.raise_for_status()  # Raise exception for bad status codes (4xx or 5xx)
        data = response.json()
        api_key = data.get("key")
        if not api_key:
            io.tool_error("Error: 'key' not found in OpenRouter response.")
            io.tool_error(f"Response: {response.text}")
            return None
        return api_key
    except requests.exceptions.Timeout:
        io.tool_error("Error: Request to OpenRouter timed out during code exchange.")
        return None
    except requests.exceptions.HTTPError as e:
        io.tool_error(
            "Error exchanging code for OpenRouter key:"
            f" {e.response.status_code} {e.response.reason}"
        )
        io.tool_error(f"Response: {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        io.tool_error(f"Error exchanging code for OpenRouter key: {e}")
        return None
    except Exception as e:
        io.tool_error(f"Unexpected error during code exchange: {e}")
        return None


# Function to start the OAuth flow
def start_openrouter_oauth_flow(io, analytics):
    """Initiates the OpenRouter OAuth PKCE flow using a local server."""

    port = find_available_port()
    if not port:
        io.tool_error("Could not find an available port between 8484 and 8584.")
        io.tool_error("Please ensure a port in this range is free, or configure manually.")
        return None

    callback_url = f"http://localhost:{port}/callback/aider"
    auth_code = None
    server_error = None
    server_started = threading.Event()
    shutdown_server = threading.Event()

    class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            nonlocal auth_code, server_error
            parsed_path = urlparse(self.path)
            if parsed_path.path == "/callback/aider":
                query_params = parse_qs(parsed_path.query)
                if "code" in query_params:
                    auth_code = query_params["code"][0]
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(
                        b"<html><body><h1>Success!</h1>"
                        b"<p>Aider has received the authentication code. "
                        b"You can close this browser tab.</p></body></html>"
                    )
                    # Signal the main thread to shut down the server
                    # Signal the main thread to shut down the server
                    shutdown_server.set()
                else:
                    # Redirect to aider website if 'code' is missing (e.g., user visited manually)
                    self.send_response(302)  # Found (temporary redirect)
                    self.send_header("Location", urls.website)
                    self.end_headers()
                    # No need to set server_error, just redirect.
                    # Do NOT shut down the server here; wait for timeout or success.
            else:
                # Redirect anything else (e.g., favicon.ico) to the main website as well
                self.send_response(302)
                self.send_header("Location", urls.website)
                self.end_headers()
                self.wfile.write(b"Not Found")

        def log_message(self, format, *args):
            # Suppress server logging to keep terminal clean
            pass

    def run_server():
        nonlocal server_error
        try:
            with socketserver.TCPServer(("localhost", port), OAuthCallbackHandler) as httpd:
                io.tool_output(f"Temporary server listening on {callback_url}", log_only=True)
                server_started.set()  # Signal that the server is ready
                # Wait until shutdown is requested or timeout occurs (handled by main thread)
                while not shutdown_server.is_set():
                    httpd.handle_request()  # Handle one request at a time
                    # Add a small sleep to prevent busy-waiting if needed,
                    # though handle_request should block appropriately.
                    time.sleep(0.1)
                io.tool_output("Shutting down temporary server.", log_only=True)
        except Exception as e:
            server_error = f"Failed to start or run temporary server: {e}"
            server_started.set()  # Signal even if failed, error will be checked
            shutdown_server.set()  # Ensure shutdown logic proceeds

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Wait briefly for the server to start, or for an error
    if not server_started.wait(timeout=5):
        io.tool_error("Temporary authentication server failed to start in time.")
        shutdown_server.set()  # Ensure thread exits if it eventually starts
        server_thread.join(timeout=1)
        return None

    # Check if server failed during startup
    if server_error:
        io.tool_error(server_error)
        shutdown_server.set()  # Ensure thread exits
        server_thread.join(timeout=1)
        return None

    # Generate codes and URL
    code_verifier, code_challenge = generate_pkce_codes()
    auth_url_base = "https://openrouter.ai/auth"
    auth_params = {
        "callback_url": callback_url,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"{auth_url_base}?{'&'.join(f'{k}={v}' for k, v in auth_params.items())}"

    io.tool_output("\nPlease open this URL in your browser to connect Aider with OpenRouter:")
    io.tool_output()
    print(auth_url)

    MINUTES = 5
    io.tool_output(f"\nWaiting up to {MINUTES} minutes for you to finish in the browser...")
    io.tool_output("Use Control-C to interrupt.")

    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    # Wait for the callback to set the auth_code or for timeout/error
    interrupted = False
    try:
        shutdown_server.wait(timeout=MINUTES * 60)  # Convert minutes to seconds
    except KeyboardInterrupt:
        io.tool_warning("\nOAuth flow interrupted.")
        analytics.event("oauth_flow_failed", provider="openrouter", reason="user_interrupt")
        interrupted = True
        # Ensure the server thread is signaled to shut down
        shutdown_server.set()

    # Join the server thread to ensure it's cleaned up
    server_thread.join(timeout=1)

    if interrupted:
        return None  # Return None if interrupted by user

    if server_error:
        io.tool_error(f"Authentication failed: {server_error}")
        analytics.event("oauth_flow_failed", provider="openrouter", reason=server_error)
        return None

    if not auth_code:
        io.tool_error("Authentication with OpenRouter failed.")
        analytics.event("oauth_flow_failed", provider="openrouter")
        return None

    io.tool_output("Completing authentication...")
    analytics.event("oauth_flow_code_received", provider="openrouter")

    # Exchange code for key
    api_key = exchange_code_for_key(auth_code, code_verifier, io)

    if api_key:
        # Set env var for the current session immediately
        os.environ["OPENROUTER_API_KEY"] = api_key

        # Save the key to the oauth-keys.env file
        try:
            config_dir = os.path.expanduser("~/.aider")
            os.makedirs(config_dir, exist_ok=True)
            key_file = os.path.join(config_dir, "oauth-keys.env")
            with open(key_file, "a", encoding="utf-8") as f:
                f.write(f'OPENROUTER_API_KEY="{api_key}"\n')

            io.tool_warning("Aider will load the OpenRouter key automatically in future sessions.")
            io.tool_output()

            analytics.event("oauth_flow_success", provider="openrouter")
            return api_key
        except Exception as e:
            io.tool_error(f"Successfully obtained key, but failed to save it to file: {e}")
            io.tool_warning("Set OPENROUTER_API_KEY environment variable for this session only.")
            # Still return the key for the current session even if saving failed
            analytics.event("oauth_flow_save_failed", provider="openrouter", reason=str(e))
            return api_key
    else:
        io.tool_error("Authentication with OpenRouter failed.")
        analytics.event("oauth_flow_failed", provider="openrouter", reason="code_exchange_failed")
        return None


# Dummy Analytics class for testing
class DummyAnalytics:
    def event(self, *args, **kwargs):
        # print(f"Analytics Event: {args} {kwargs}") # Optional: print events
        pass


def main():
    """Main function to test the OpenRouter OAuth flow."""
    print("Starting OpenRouter OAuth flow test...")

    # Use a real IO object for interaction
    io = InputOutput(
        pretty=True,
        yes=False,
        input_history_file=None,
        chat_history_file=None,
        tool_output_color="BLUE",
        tool_error_color="RED",
    )
    # Use a dummy analytics object
    analytics = DummyAnalytics()

    # Ensure OPENROUTER_API_KEY is not set, to trigger the flow naturally
    # (though start_openrouter_oauth_flow doesn't check this itself)
    if "OPENROUTER_API_KEY" in os.environ:
        print("Warning: OPENROUTER_API_KEY is already set in environment.")
        # del os.environ["OPENROUTER_API_KEY"] # Optionally unset it for testing

    api_key = start_openrouter_oauth_flow(io, analytics)

    if api_key:
        print("\nOAuth flow completed successfully!")
        print(f"Obtained API Key (first 5 chars): {api_key[:5]}...")
        # Be careful printing the key, even partially
    else:
        print("\nOAuth flow failed or was cancelled.")

    print("\nOpenRouter OAuth flow test finished.")


if __name__ == "__main__":
    main()
