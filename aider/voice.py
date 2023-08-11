import os
import queue
import tempfile
import time

import numpy as np
import openai
from prompt_toolkit.shortcuts import prompt

try:
    import sounddevice as sd
except OSError:
    sd = None

import soundfile as sf

from .dump import dump  # noqa: F401


class Voice:
    max_rms = 0
    min_rms = 1e5
    pct = 0

    def is_audio_available(self):
        return sd is not None

    def callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        self.q.put(indata.copy())
        rms = np.sqrt(np.mean(indata**2))
        self.max_rms = max(self.max_rms, rms)
        self.min_rms = min(self.min_rms, rms)

        rng = self.max_rms - self.min_rms
        if rng > 0.001:
            self.pct = (rms - self.min_rms) / rng

    def get_prompt(self):
        if np.isnan(self.pct):
            bar = ""
        else:
            bar = "█" * int(self.pct * 10)

        dur = time.time() - self.start_time
        return f"Recording, press ENTER when done... {dur:.1f}sec {bar}"

    def record_and_transcribe(self):
        self.q = queue.Queue()

        filename = tempfile.mktemp(suffix=".wav")

        sample_rate = 16000  # 16kHz

        self.start_time = time.time()

        with sf.SoundFile(filename, mode="x", samplerate=sample_rate, channels=1) as file:
            with sd.InputStream(samplerate=sample_rate, channels=1, callback=self.callback):
                prompt(self.get_prompt, refresh_interval=0.1)

            while not self.q.empty():
                file.write(self.q.get())

        with open(filename, "rb") as fh:
            transcript = openai.Audio.transcribe("whisper-1", fh)

        text = transcript["text"]
        return text


if __name__ == "__main__":
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set the OPENAI_API_KEY environment variable.")
    print(Voice().record_and_transcribe())
