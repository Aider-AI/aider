import os
import queue
import tempfile
import time

import numpy as np

try:
    import soundfile as sf
except (OSError, ModuleNotFoundError):
    sf = None

from prompt_toolkit.shortcuts import prompt

from .dump import dump  # noqa: F401


class SoundDeviceError(Exception):
    pass


class Voice:
    max_rms = 0
    min_rms = 1e5
    pct = 0

    threshold = 0.15

    def __init__(self, client):
        if sf is None:
            raise SoundDeviceError
        try:
            print("Initializing sound device...")
            import sounddevice as sd

            self.sd = sd
        except (OSError, ModuleNotFoundError):
            raise SoundDeviceError

        self.client = client

    def callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        rms = np.sqrt(np.mean(indata**2))
        self.max_rms = max(self.max_rms, rms)
        self.min_rms = min(self.min_rms, rms)

        rng = self.max_rms - self.min_rms
        if rng > 0.001:
            self.pct = (rms - self.min_rms) / rng
        else:
            self.pct = 0.5

        self.q.put(indata.copy())

    def get_prompt(self):
        num = 10
        if np.isnan(self.pct) or self.pct < self.threshold:
            cnt = 0
        else:
            cnt = int(self.pct * 10)

        bar = "░" * cnt + "█" * (num - cnt)
        bar = bar[:num]

        dur = time.time() - self.start_time
        return f"Recording, press ENTER when done... {dur:.1f}sec {bar}"

    def record_and_transcribe(self, history=None, language=None):
        try:
            return self.raw_record_and_transcribe(history, language)
        except KeyboardInterrupt:
            return

    def raw_record_and_transcribe(self, history, language):
        self.q = queue.Queue()

        filename = tempfile.mktemp(suffix=".wav")

        sample_rate = 16000  # 16kHz

        self.start_time = time.time()

        with self.sd.InputStream(samplerate=sample_rate, channels=1, callback=self.callback):
            prompt(self.get_prompt, refresh_interval=0.1)

        with sf.SoundFile(filename, mode="x", samplerate=sample_rate, channels=1) as file:
            while not self.q.empty():
                file.write(self.q.get())

        with open(filename, "rb") as fh:
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1", file=fh, prompt=history, language=language
            )

        text = transcript.text
        return text


if __name__ == "__main__":
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set the OPENAI_API_KEY environment variable.")
    print(Voice().record_and_transcribe())
