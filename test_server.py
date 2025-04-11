#!/usr/bin/env python3

import argparse
import json

import requests


def parse_args():
    parser = argparse.ArgumentParser(description="Test the aider API server")
    parser.add_argument(
        "--url", default="http://127.0.0.1:8000", help="URL of the aider API server"
    )
    parser.add_argument(
        "--message",
        default='Hello, write a simple "Hello, World!" program in Python',
        help="Message to send to the chat endpoint",
    )
    return parser.parse_args()


def test_chat_streaming(url, message):
    """Test the streaming API endpoint."""
    print(f"Sending message to {url}/chat:")
    print(f"> {message}")
    print("\nResponse:")

    # Prepare the request
    endpoint = f"{url}/chat"
    data = {"message": message, "stream": True}

    # Send the request with stream=True to get the response incrementally
    with requests.post(endpoint, json=data, stream=True) as response:
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            try:
                print(response.json())
            except json.JSONDecodeError:
                print(response.text)
            return

        # Process the streaming response
        for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
            if chunk:
                print(chunk, end="", flush=True)

    print("\n\nDone!")


if __name__ == "__main__":
    args = parse_args()
    test_chat_streaming(args.url, args.message)
