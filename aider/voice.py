import math
import os
import queue
import tempfile
import time
import warnings

from prompt_toolkit.shortcuts import prompt

from aider.llm import litellm

from .dump import dump  # noqa: F401

warnings.filterwarnings(
    "ignore", message="Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work"
)

from pydub import AudioSegment  # noqa

try:
    import soundfile as sf
except (OSError, ModuleNotFoundError):
    sf = None


class SoundDeviceError(Exception):
    pass


class Voice:
    max_rms = 0
    min_rms = 1e5
    pct = 0

    threshold = 0.15

    def __init__(self, audio_format="wav"):
        if sf is None:
            raise SoundDeviceError
        try:
            print("Initializing sound device...")
            import sounddevice as sd

            self.sd = sd
        except (OSError, ModuleNotFoundError):
            raise SoundDeviceError
        if audio_format not in ["wav", "mp3", "webm"]:
            raise ValueError(f"Unsupported audio format: {audio_format}")
        self.audio_format = audio_format

    def callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        import numpy as np

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
        if math.isnan(self.pct) or self.pct < self.threshold:
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
        except SoundDeviceError as e:
            print(f"Error: {e}")
            print("Please ensure you have a working audio input device connected and try again.")
            return

    def raw_record_and_transcribe(self, history, language):
        self.q = queue.Queue()

        temp_wav = tempfile.mktemp(suffix=".wav")

        try:
            sample_rate = int(self.sd.query_devices(None, "input")["default_samplerate"])
        except (TypeError, ValueError):
            sample_rate = 16000  # fallback to 16kHz if unable to query device
        except self.sd.PortAudioError:
            raise SoundDeviceError(
                "No audio input device detected. Please check your audio settings and try again."
            )

        self.start_time = time.time()

        try:
            with self.sd.InputStream(samplerate=sample_rate, channels=1, callback=self.callback):
                prompt(self.get_prompt, refresh_interval=0.1)
        except self.sd.PortAudioError as err:
            raise SoundDeviceError(f"Error accessing audio input device: {err}")

        with sf.SoundFile(temp_wav, mode="x", samplerate=sample_rate, channels=1) as file:
            while not self.q.empty():
                file.write(self.q.get())

        if self.audio_format != "wav":
            filename = tempfile.mktemp(suffix=f".{self.audio_format}")
            audio = AudioSegment.from_wav(temp_wav)
            audio.export(filename, format=self.audio_format)
            os.remove(temp_wav)
        else:
            filename = temp_wav

        with open(filename, "rb") as fh:
            try:
                transcript = litellm.transcription(
                    model="whisper-1", file=fh, prompt=history, language=language
                )
            except Exception as err:
                print(f"Unable to transcribe {filename}: {err}")
                return

        if self.audio_format != "wav":
            os.remove(filename)

        text = transcript.text
        return text


if __name__ == "__main__":
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set the OPENAI_API_KEY environment variable.")
    print(Voice().record_and_transcribe())
