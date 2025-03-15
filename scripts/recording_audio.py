#!/usr/bin/env python3
"""
Generate TTS audio files for recording commentary using OpenAI's API.
Usage: python scripts/recording_audio.py path/to/recording.md
"""

import argparse
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OUTPUT_DIR = "aider/website/assets/audio"
VOICE = "onyx"  # Options: alloy, echo, fable, onyx, nova, shimmer


def extract_recording_id(markdown_file):
    """Extract recording ID from the markdown file path."""
    return Path(markdown_file).stem


def extract_commentary(markdown_file):
    """Extract commentary markers from markdown file."""
    with open(markdown_file, "r") as f:
        content = f.read()

    # Find Commentary section
    commentary_match = re.search(r"## Commentary\s+(.*?)(?=##|\Z)", content, re.DOTALL)
    if not commentary_match:
        print(f"No Commentary section found in {markdown_file}")
        return []

    commentary = commentary_match.group(1).strip()

    # Extract timestamp-message pairs
    markers = []
    for line in commentary.split("\n"):
        line = line.strip()
        if line.startswith("- "):
            line = line[2:]  # Remove the list marker
            match = re.match(r"(\d+):(\d+)\s+(.*)", line)
            if match:
                minutes, seconds, message = match.groups()
                time_in_seconds = int(minutes) * 60 + int(seconds)
                markers.append((time_in_seconds, message))

    return markers


def generate_audio_openai(text, output_file, voice=VOICE):
    """Generate audio using OpenAI TTS API."""
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY environment variable not set")
        return False

    url = "https://api.openai.com/v1/audio/speech"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "tts-1", "input": text, "voice": voice}

    try:
        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            with open(output_file, "wb") as f:
                f.write(response.content)
            return True
        else:
            print(f"Error: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        print(f"Exception during API call: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate TTS audio for recording commentary.")
    parser.add_argument("markdown_file", help="Path to the recording markdown file")
    parser.add_argument("--voice", default=VOICE, help=f"OpenAI voice to use (default: {VOICE})")
    parser.add_argument(
        "--output-dir", default=OUTPUT_DIR, help=f"Output directory (default: {OUTPUT_DIR})"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print what would be done without generating audio"
    )

    args = parser.parse_args()
    
    # Use args.voice directly instead of modifying global VOICE
    selected_voice = args.voice
    
    recording_id = extract_recording_id(args.markdown_file)
    print(f"Processing recording: {recording_id}")

    # Create output directory
    output_dir = os.path.join(args.output_dir, recording_id)
    if not args.dry_run:
        os.makedirs(output_dir, exist_ok=True)

    # Extract commentary markers
    markers = extract_commentary(args.markdown_file)

    if not markers:
        print("No commentary markers found!")
        return

    print(f"Found {len(markers)} commentary markers")

    # Generate audio for each marker
    for time_sec, message in markers:
        minutes = time_sec // 60
        seconds = time_sec % 60
        timestamp = f"{minutes:02d}-{seconds:02d}"
        filename = f"{timestamp}.mp3"
        output_file = os.path.join(output_dir, filename)

        print(f"Marker at {minutes}:{seconds:02d} - {message}")
        if args.dry_run:
            print(f"  Would generate: {output_file}")
        else:
            print(f"  Generating: {output_file}")
            success = generate_audio_openai(message, output_file, voice=selected_voice)
            if success:
                print(f"  ✓ Generated audio file")
            else:
                print(f"  ✗ Failed to generate audio")


if __name__ == "__main__":
    main()
