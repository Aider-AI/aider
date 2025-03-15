#!/usr/bin/env python3
"""
Generate TTS audio files for recording commentary using OpenAI's API.
Usage: python scripts/recording_audio.py path/to/recording.md
"""

import argparse
import json
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


def load_metadata(output_dir):
    """Load the audio metadata JSON file if it exists."""
    metadata_file = os.path.join(output_dir, "metadata.json")

    if os.path.exists(metadata_file):
        try:
            with open(metadata_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Could not parse metadata file {metadata_file}, will recreate it")

    return {}


def save_metadata(output_dir, metadata):
    """Save the audio metadata to JSON file."""
    metadata_file = os.path.join(output_dir, "metadata.json")

    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)


def get_timestamp_key(time_sec):
    """Generate a consistent timestamp key format for metadata."""
    minutes = time_sec // 60
    seconds = time_sec % 60
    return f"{minutes:02d}-{seconds:02d}"


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
    parser.add_argument(
        "--force", action="store_true", help="Force regeneration of all audio files"
    )

    args = parser.parse_args()

    # Use args.voice directly instead of modifying global VOICE
    selected_voice = args.voice

    recording_id = extract_recording_id(args.markdown_file)
    print(f"Processing recording: {recording_id}")

    # Create output directory
    output_dir = os.path.join(args.output_dir, recording_id)
    print(f"Audio directory: {output_dir}")
    if not args.dry_run:
        os.makedirs(output_dir, exist_ok=True)

    # Extract commentary markers
    markers = extract_commentary(args.markdown_file)

    if not markers:
        print("No commentary markers found!")
        return

    print(f"Found {len(markers)} commentary markers")

    # Load existing metadata
    metadata = load_metadata(output_dir)

    # Create a dictionary of current markers for easier comparison
    current_markers = {}
    for time_sec, message in markers:
        timestamp_key = get_timestamp_key(time_sec)
        current_markers[timestamp_key] = message

    # Track files that need to be deleted (no longer in the markdown)
    files_to_delete = []
    for timestamp_key in metadata:
        if timestamp_key not in current_markers:
            files_to_delete.append(f"{timestamp_key}.mp3")

    # Delete files that are no longer needed
    if files_to_delete and not args.dry_run:
        for filename in files_to_delete:
            file_path = os.path.join(output_dir, filename)
            if os.path.exists(file_path):
                print(f"Removing obsolete file: {filename}")
                os.remove(file_path)
    elif files_to_delete:
        print(f"Would remove {len(files_to_delete)} obsolete files: {', '.join(files_to_delete)}")

    # Generate audio for each marker
    for time_sec, message in markers:
        timestamp_key = get_timestamp_key(time_sec)
        filename = f"{timestamp_key}.mp3"
        output_file = os.path.join(output_dir, filename)

        # Check if we need to generate this file
        needs_update = args.force or (
            timestamp_key not in metadata or metadata[timestamp_key] != message
        )

        minutes = time_sec // 60
        seconds = time_sec % 60

        print(f"Marker at {minutes}:{seconds:02d} - {message}")

        if not needs_update:
            print(f"  ✓ Audio file already exists with correct content")
            continue

        if args.dry_run:
            print(f"  Would generate: {output_file}")
        else:
            print(f"  Generating: {output_file}")
            success = generate_audio_openai(message, output_file, voice=selected_voice)
            if success:
                print(f"  ✓ Generated audio file")
                # Update metadata with the new message
                metadata[timestamp_key] = message
            else:
                print(f"  ✗ Failed to generate audio")

    # Save updated metadata
    if not args.dry_run:
        # Remove entries for deleted files
        for timestamp_key in list(metadata.keys()):
            if timestamp_key not in current_markers:
                del metadata[timestamp_key]

        save_metadata(output_dir, metadata)


if __name__ == "__main__":
    main()
