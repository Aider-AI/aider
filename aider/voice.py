import sounddevice as sd
import numpy as np
import keyboard
import openai
import io

def record_and_transcribe():
    # Set your OpenAI API key
    openai.api_key = 'your-api-key'

    # Set the sample rate and duration for the recording
    sample_rate = 16000  # 16kHz
    duration = 10  # in seconds

    # Create a callback function to stop recording when a key is pressed
    def on_key_press(e):
        print("Key pressed, stopping recording...")
        sd.stop()

    # Start the recording
    print("Recording started, press any key to stop...")
    recording = sd.rec(int(sample_rate * duration), samplerate=sample_rate, channels=1, callback=on_key_press)

    # Wait for a key press
    keyboard.wait()

    # Convert the recording to bytes
    recording_bytes = io.BytesIO()
    np.save(recording_bytes, recording, allow_pickle=False)
    recording_bytes = recording_bytes.getvalue()

    # Transcribe the audio using the Whisper API
    response = openai.Whisper.asr.create(audio_data=recording_bytes)

    # Return the transcription
    return response['choices'][0]['text']
