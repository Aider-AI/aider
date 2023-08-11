import os
import queue
import tempfile

import openai

try:
    import sounddevice as sd
except OSError:
    sd = None

import soundfile as sf

from .dump import dump  # noqa: F401


def is_audio_available():
    return sd is not None


def record_and_transcribe():
    q = queue.Queue()

    def callback(indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        q.put(indata.copy())

    filename = tempfile.mktemp(suffix=".wav")

    sample_rate = 16000  # 16kHz

    with sf.SoundFile(filename, mode="x", samplerate=sample_rate, channels=1) as file:
        with sd.InputStream(samplerate=sample_rate, channels=1, callback=callback):
            input("Recording... Press ENTER when done speaking...")

        while not q.empty():
            file.write(q.get())

    with open(filename, "rb") as fh:
        transcript = openai.Audio.transcribe("whisper-1", fh)

    text = transcript["text"]
    return text


if __name__ == "__main__":
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set the OPENAI_API_KEY environment variable.")
    print(record_and_transcribe())
