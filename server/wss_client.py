import argparse
import asyncio
import json
import os
import ssl
import sys
import uuid

import aioconsole  # You'll need to install this: pip install aioconsole
import websockets


async def get_user_prompt():
    """Get prompt from user input asynchronously."""
    try:
        user_input = await aioconsole.ainput("Enter your prompt (or 'exit' to quit): ")
        return user_input
    except EOFError:
        return "exit"


async def pong_handler(websocket):
    """Handle ping/pong messages in the background."""
    try:
        while True:
            await websocket.ping()
            await asyncio.sleep(
                15
            )  # Send a ping every 15 seconds to keep connection alive
    except websockets.exceptions.ConnectionClosed:
        pass  # Connection is closed, stop pinging


async def connect_to_websocket(
    uri,
    session_id,
    path,
    cert_path = None,
    file_patterns=None,
    exclude_dirs=None,
    exclude_hidden=True,
    max_retries=3,
    graph_mode=False,
):
    """
    Connects to the CodeDroid WebSocket server accepting a self-signed certificate and
    enters an interactive loop to get user prompts and send them.

    Args:
        uri (str): The WebSocket URI (e.g., "wss://localhost:8000/ws").
        session_id (str): The session ID for the LLM conversation.
        path (str): The path to the project directory.
        cert_path (str): Path to the self-signed certificate file.
        file_patterns (str): File patterns to include (default: "*").
        exclude_dirs (str): Directories to exclude (default: "None").
        exclude_hidden (bool): Exclude hidden directories (default: True).
        max_retries (int): Maximum number of reconnection attempts.
        graph_mode (bool): Whether to use the graph implementation (default: False).
    """
    retry_count = 0
    file_patterns = file_patterns.split(",") if file_patterns else ["*"]
    exclude_dirs = exclude_dirs.split(",") if exclude_dirs else []

    ssl_context = None

    # Only provide an SSL context if a certificate is provided. 
    if cert_path:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.load_verify_locations(cert_path)
        ssl_context.check_hostname = (
            False  # Disable hostname verification (for testing purposes only!)
        )

    while retry_count <= max_retries:
        try:
            print(f"Connecting to {uri}...")
            async with websockets.connect(
                uri,
                ssl=ssl_context,
                ping_interval=20,  # Send pings every 20 seconds
                ping_timeout=60,  # Wait up to 60 seconds for a pong response
                close_timeout=10,  # Wait up to 10 seconds for a close frame
            ) as websocket:
                print("Connection established!")
                print("-" * 50)
                retry_count = 0  # Reset retry counter on successful connection

                # Start background ping/pong handler
                pong_task = asyncio.create_task(pong_handler(websocket))

                try:
                    # Interactive loop
                    while True:
                        # Get user prompt asynchronously
                        user_prompt = await get_user_prompt()

                        # Check if user input is empty
                        if not user_prompt:
                            continue

                        # Check if user wants to exit
                        if user_prompt.lower() in ["exit", "quit", "bye"]:
                            print("Exiting...")
                            pong_task.cancel()
                            return

                        # Send user prompt
                        json_message = json.dumps(
                            {
                                "session_id": session_id,
                                "project_path": path,
                                "prompt": user_prompt,
                                "file_patterns": file_patterns,
                                "exclude_dirs": exclude_dirs,
                                "exclude_hidden": exclude_hidden,
                                "graph_mode": graph_mode,
                            }
                        )
                        print(f"\nSending: {user_prompt}")
                        await websocket.send(json_message)

                        # Receive and print response
                        response = await websocket.recv()
                        print(f"Received: {response}")

                        try:
                            # Try to receive additional responses with a timeout
                            while True:
                                response = await asyncio.wait_for(
                                    websocket.recv(), timeout=1.0
                                )
                                print(f"Received additional: {response}")
                        except asyncio.TimeoutError:
                            # No more responses available
                            pass

                        print("-" * 50)

                except asyncio.CancelledError:
                    pong_task.cancel()
                    raise
                except websockets.exceptions.ConnectionClosed as e:
                    pong_task.cancel()
                    print(f"Connection closed: {e}")
                    raise  # Re-raise to trigger reconnection

        except websockets.exceptions.ConnectionClosed as e:
            retry_count += 1
            wait_time = min(30, 2**retry_count)  # Exponential backoff
            print(
                f"Connection closed: {e}. Retrying in {wait_time} seconds... (Attempt {retry_count}/{max_retries})"
            )
            if retry_count <= max_retries:
                await asyncio.sleep(wait_time)
            else:
                print(f"Max retries ({max_retries}) reached. Giving up.")
                break

        except Exception as e:
            retry_count += 1
            wait_time = min(30, 2**retry_count)  # Exponential backoff
            print(
                f"An error occurred: {e}. Retrying in {wait_time} seconds... (Attempt {retry_count}/{max_retries})"
            )
            if retry_count <= max_retries:
                await asyncio.sleep(wait_time)
            else:
                print(f"Max retries ({max_retries}) reached. Giving up.")
                break


if __name__ == "__main__":
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(
        description="Interactive WebSocket client with custom prompt"
    )
    parser.add_argument(
        "--uri",
        type=str,
        default="wss://localhost:8000/ws",
        help="WebSocket server URI (default: wss://localhost:8000/ws)",
    )
    parser.add_argument(
        "--cert",
        type=str,
        default="/Users/mchan/ssl/cert.pem",
        help="Path to the self-signed certificate file",
    )
    parser.add_argument(
        "--session",
        type=str,
        default=str(uuid.uuid4()),
        help="The session ID used for LLM conversation (default: UUID)",
    )
    parser.add_argument(
        "--path", type=str, default="", help="Path to the project directory"
    )
    parser.add_argument(
        "--file_patterns",
        type=str,
        default=None,
        help="File patterns to include (default: '*')",
    )
    parser.add_argument(
        "--exclude_dirs",
        type=str,
        default=None,
        help="Directories to exclude (default: None)",
    )
    parser.add_argument(
        "--exclude_hidden",
        type=bool,
        default=True,
        help="Exclude hidden directories (default: True)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of reconnection attempts (default: 3)",
    )
    parser.add_argument(
        "--graph_mode",
        type=bool,
        default=True,
        help="Whether to use the graph implementation of gpte",
    )

    args = parser.parse_args()

    try:
        # Check if cert file exists if using wss.
        if not os.path.isfile(args.cert) and uri.startswith("wss"):
            print(f"Error: Certificate file '{args.cert}' does not exist.")
            sys.exit(1)

        asyncio.run(
            connect_to_websocket(
                args.uri,
                args.session,
                args.path,
                args.cert,
                args.file_patterns,
                args.exclude_dirs,
                args.exclude_hidden,
                args.max_retries,
                args.graph_mode,
            )
        )
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
    except Exception as e:
        print(f"Fatal error: {e}")
