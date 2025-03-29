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
from aider.utils import check_pip_install_extra


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

    # Select model based on available API keys
    model_key_pairs = [
        ("ANTHROPIC_API_KEY", "sonnet"),
        ("DEEPSEEK_API_KEY", "deepseek"),
        ("OPENROUTER_API_KEY", "openrouter/anthropic/claude-3.7-sonnet"),
        ("OPENAI_API_KEY", "gpt-4o"),
        ("GEMINI_API_KEY", "gemini/gemini-2.5-pro-exp-03-25"),
        ("VERTEXAI_PROJECT", "vertex_ai/gemini-2.5-pro-exp-03-25"),
    ]

    selected_model = None
    found_key_env_var = None
    for env_key, model_name in model_key_pairs:
        api_key_value = os.environ.get(env_key)
        # Special check for Vertex AI project which isn't a key but acts like one for selection
        is_vertex = env_key == "VERTEXAI_PROJECT" and api_key_value
        if api_key_value and (not is_vertex or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")):
            selected_model = model_name
            # found_key_env_var = env_key # Not used
            io.tool_warning(f"Using {model_name} model with {env_key} environment variable.")
            # Track which API key was used for auto-selection
            analytics.event("auto_model_selection", api_key=env_key)
            break

    if selected_model:
        return selected_model

    # No API keys found - Offer OpenRouter OAuth
    io.tool_warning(
        "No API key environment variables found (e.g., OPENAI_API_KEY, ANTHROPIC_API_KEY...)."
    )
    # Use confirm_ask which handles non-interactive cases
    if io.confirm_ask(
        "Authenticate with OpenRouter via browser to get an API key?",
        default="y",
        group="openrouter_oauth",
    ):
        analytics.event("oauth_flow_initiated", provider="openrouter")
        openrouter_key = start_openrouter_oauth_flow(io, analytics)
        if openrouter_key:
            # Successfully got key via OAuth, use the default OpenRouter model
            # Ensure OPENROUTER_API_KEY is now set in the environment for later use
            os.environ["OPENROUTER_API_KEY"] = openrouter_key
            selected_model = "openrouter/anthropic/claude-3.7-sonnet"  # Default OR model
            io.tool_warning(f"Using {selected_model} model via OpenRouter OAuth.")
            # Track OAuth success leading to model selection
            analytics.event("auto_model_selection", api_key="OPENROUTER_API_KEY_OAUTH")
            return selected_model
        else:
            # OAuth failed or was cancelled by user implicitly (e.g., closing browser)
            # Error messages are handled within start_openrouter_oauth_flow
            io.tool_error("OpenRouter authentication did not complete successfully.")
            # Fall through to the final error message

    # Final fallback if no key found and OAuth not attempted or failed/declined
    io.tool_error(
        "No model specified and no API key found or configured.\n"
        "Please set an API key environment variable (e.g., OPENAI_API_KEY),\n"
        "use the OpenRouter authentication flow (if offered),\n"
        "or specify both --model and --api-key."
    )
    io.offer_url(urls.models_and_keys, "Open documentation URL for more info?")
    analytics.event("auto_model_selection", api_key=None)  # Track failure
    return None


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
            f"Error exchanging code for OpenRouter key: {e.status_code} {e.response.reason}"
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

    # Check for requests library
    if not check_pip_install_extra(io, "requests", "OpenRouter OAuth", "aider[oauth]"):
        return None

    port = find_available_port()
    if not port:
        io.tool_error("Could not find an available port between 8484 and 8584.")
        io.tool_error("Please ensure a port in this range is free, or configure manually.")
        return None

    callback_url = f"http://localhost:{port}/callback"
    auth_code = None
    server_error = None
    server_started = threading.Event()
    shutdown_server = threading.Event()

    class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            nonlocal auth_code, server_error
            parsed_path = urlparse(self.path)
            if parsed_path.path == "/callback":
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
                    shutdown_server.set()
                else:
                    server_error = "Missing 'code' parameter in callback URL."
                    self.send_response(400)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(
                        b"<html><body><h1>Error</h1>"
                        b"<p>Missing 'code' parameter in callback URL.</p>"
                        b"<p>Please check the Aider terminal.</p></body></html>"
                    )
                    shutdown_server.set()
            else:
                self.send_response(404)
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

    io.tool_output(
        "\nPlease open the following URL in your web browser to authorize Aider with OpenRouter:"
    )
    io.tool_output(auth_url)
    io.tool_output("\nWaiting for authentication... (Timeout: 2 minutes)")

    try:
        webbrowser.open(auth_url)
    except Exception as e:
        io.tool_warning(f"Could not automatically open browser: {e}")
        io.tool_output("Please manually open the URL above.")

    # Wait for the callback to set the auth_code or for timeout/error
    shutdown_server.wait(timeout=120)  # 2 minute timeout

    # Join the server thread to ensure it's cleaned up
    server_thread.join(timeout=1)

    if server_error:
        io.tool_error(f"Authentication failed: {server_error}")
        analytics.event("oauth_flow_failed", provider="openrouter", reason=server_error)
        return None

    if not auth_code:
        io.tool_error("Authentication timed out. No code received from OpenRouter.")
        analytics.event("oauth_flow_failed", provider="openrouter", reason="timeout")
        return None

    io.tool_output("Authentication code received. Exchanging for API key...")
    analytics.event("oauth_flow_code_received", provider="openrouter")

    # Exchange code for key
    api_key = exchange_code_for_key(auth_code, code_verifier, io)

    if api_key:
        io.tool_output("Successfully obtained and configured OpenRouter API key.")
        # Securely store this key? For now, set env var for the session.
        os.environ["OPENROUTER_API_KEY"] = api_key
        io.tool_warning("Set OPENROUTER_API_KEY environment variable for this session.")
        analytics.event("oauth_flow_success", provider="openrouter")
        return api_key
    else:
        io.tool_error("Failed to obtain OpenRouter API key from code.")
        analytics.event("oauth_flow_failed", provider="openrouter", reason="code_exchange_failed")
        return None
