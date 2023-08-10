import sounddevice as sd
import numpy as np
import keyboard
import openai
import io
import tempfile
import queue
import soundfile as sf
import os

def record_and_transcribe(api_key):

    # Set the sample rate and duration for the recording
    sample_rate = 16000  # 16kHz
    duration = 10  # in seconds

    def callback(indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, file=sys.stderr)
        q.put(indata.copy())


    filename = tempfile.mktemp(prefix='delme_rec_unlimited_', suffix='.wav', dir='')

    q = queue.Queue()

    # Make sure the file is opened before recording anything:
    with sf.SoundFile(filename, mode='x', samplerate=sample_rate, channels=1) as file:
        with sd.InputStream(samplerate=sample_rate, channels=1, callback=callback):
            input('Press enter when done')

        while not q.empty():
            print('.')
            file.write(q.get())

    print('done')

    # Transcribe the audio using the Whisper API
    response = openai.Whisper.asr.create(audio_data=recording_bytes)

    # Return the transcription
    return response['choices'][0]['text']

if __name__ == "__main__":
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("Please set the OPENAI_API_KEY environment variable.")
    print(record_and_transcribe(api_key))
