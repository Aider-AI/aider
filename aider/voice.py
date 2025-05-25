import math
import os
import queue
import tempfile
import time
import warnings

from prompt_toolkit.shortcuts import prompt
from aider.llm import litellm

# Optional imports
try:
    from pywhispercpp.model import Model as WhisperModel

    HAS_WHISPER_CPP = True
except ImportError:
    HAS_WHISPER_CPP = False

from .dump import dump  # noqa: F401

warnings.filterwarnings(
    "ignore",
    message="Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work",
)
warnings.filterwarnings("ignore", category=SyntaxWarning)

try:
    from pydub import AudioSegment
    from pydub.exceptions import CouldntDecodeError, CouldntEncodeError
except ImportError:
    AudioSegment = None
    CouldntDecodeError = CouldntEncodeError = Exception

try:
    import soundfile as sf
except (OSError, ModuleNotFoundError):
    sf = None


class SoundDeviceError(Exception):
    pass


class Voice:
    """
    Voice recording and transcription utility.
    Supports both OpenAI Whisper API and local WhisperCpp transcription.
    """

    def __init__(
        self, audio_format="wav", device_name=None, use_local=False, local_model="tiny"
    ):
        self.use_local = use_local
        self.local_model = local_model
        self.audio_format = audio_format
        self.max_rms = 0
        self.min_rms = 1e5
        self.pct = 0
        self.threshold = 0.15

        if sf is None:
            raise SoundDeviceError("soundfile is not available.")

        try:
            import sounddevice as sd

            self.sd = sd
            devices = sd.query_devices()
            self.device_id = self._find_device_id(devices, device_name)
        except (OSError, ModuleNotFoundError):
            raise SoundDeviceError("sounddevice is not available.")

        if audio_format not in ["wav", "mp3", "webm"]:
            raise ValueError(f"Unsupported audio format: {audio_format}")

    def _find_device_id(self, devices, device_name):
        if not device_name:
            return None
        for i, device in enumerate(devices):
            if device_name in device["name"]:
                print(f"Using input device: {device_name} (ID: {i})")
                return i
        available_inputs = [d["name"] for d in devices if d["max_input_channels"] > 0]
        raise ValueError(
            f"Device '{device_name}' not found. Available input devices: {available_inputs}"
        )

    def callback(self, indata, frames, time, status):
        import numpy as np

        rms = np.sqrt(np.mean(indata**2))
        self.max_rms = max(self.max_rms, rms)
        self.min_rms = min(self.min_rms, rms)
        rng = self.max_rms - self.min_rms
        self.pct = (rms - self.min_rms) / rng if rng > 0.001 else 0.5
        self.q.put(indata.copy())

    def get_prompt(self):
        num = 10
        cnt = (
            0
            if math.isnan(self.pct) or self.pct < self.threshold
            else int(self.pct * 10)
        )
        bar = "░" * cnt + "█" * (num - cnt)
        bar = bar[:num]
        dur = time.time() - self.start_time
        return f"Recording, press ENTER when done... {dur:.1f}sec {bar}"

    def record_and_transcribe(self, history=None, language=None):
        try:
            return self._record_and_transcribe(history, language)
        except KeyboardInterrupt:
            return
        except SoundDeviceError as e:
            print(f"Error: {e}")
            print(
                "Please ensure you have a working audio input device connected and try again."
            )
            return

    def _get_target_sample_rate(self):
        if self.use_local:
            return 16000
        try:
            return int(
                self.sd.query_devices(self.device_id, "input")["default_samplerate"]
            )
        except (TypeError, ValueError, AttributeError):
            return 16000
        except self.sd.PortAudioError:
            raise SoundDeviceError(
                "No audio input device detected. Please check your audio settings and try again."
            )

    def _check_audio_device(self):
        try:
            self.sd.query_devices(self.device_id, "input")
        except self.sd.PortAudioError as pa_err:
            raise SoundDeviceError(
                f"Audio input device issue: {pa_err}. Please check your audio settings."
            )
        except Exception as e:
            raise SoundDeviceError(f"Unexpected error querying audio device: {e}")

    def _record_and_transcribe(self, history, language):
        self.q = queue.Queue()
        temp_wav = tempfile.mktemp(suffix=".wav")
        target_sample_rate = self._get_target_sample_rate()
        self._check_audio_device()
        self.start_time = time.time()

        try:
            with self.sd.InputStream(
                samplerate=target_sample_rate,
                channels=1,
                callback=self.callback,
                device=self.device_id,
            ):
                prompt(self.get_prompt, refresh_interval=0.1)
        except self.sd.PortAudioError as err:
            device_name = self.device_id if self.device_id is not None else "default"
            raise SoundDeviceError(
                f"Error opening audio stream at {target_sample_rate} Hz on device"
                f" '{device_name}': {err}. This might mean the sample rate is not supported"
                " or the device is in use."
            )
        except Exception as e:
            raise SoundDeviceError(f"Unexpected error opening audio stream: {e}")

        with sf.SoundFile(
            temp_wav, mode="x", samplerate=target_sample_rate, channels=1
        ) as file:
            while not self.q.empty():
                file.write(self.q.get())

        filename, use_audio_format = self._maybe_convert_audio(temp_wav)
        try:
            if self.use_local:
                return self._transcribe_local(
                    filename, use_audio_format, temp_wav, language
                )
            else:
                return self._transcribe_api(
                    filename, use_audio_format, temp_wav, history, language
                )
        finally:
            self._cleanup_files(filename, temp_wav, use_audio_format)

    def _maybe_convert_audio(self, temp_wav):
        use_audio_format = self.audio_format
        file_size = os.path.getsize(temp_wav)
        if file_size > 24.9 * 1024 * 1024 and self.audio_format == "wav":
            print(f"\nWarning: {temp_wav} is too large, switching to mp3 format.")
            use_audio_format = "mp3"
        filename = temp_wav
        if use_audio_format != "wav" and AudioSegment:
            try:
                new_filename = tempfile.mktemp(suffix=f".{use_audio_format}")
                audio = AudioSegment.from_wav(temp_wav)
                audio.export(new_filename, format=use_audio_format)
                os.remove(temp_wav)
                filename = new_filename
            except (CouldntDecodeError, CouldntEncodeError) as e:
                print(f"Error converting audio: {e}")
            except (OSError, FileNotFoundError) as e:
                print(f"File system error during conversion: {e}")
            except Exception as e:
                print(f"Unexpected error during audio conversion: {e}")
        return filename, use_audio_format

    def _transcribe_local(self, filename, use_audio_format, temp_wav, language):
        if not HAS_WHISPER_CPP:
            print(
                "pywhispercpp is not installed. Please install it to use local transcription."
            )
            return
        try:
            model = WhisperModel(
                self.local_model,
                language=language,
            )
            segments = model.transcribe(filename)
            return "".join(segment.text for segment in segments)
        except Exception as err:
            print(f"Unable to transcribe {filename} using pywhispercpp: {err}")
            return

    def _transcribe_api(self, filename, use_audio_format, temp_wav, history, language):
        try:
            with open(filename, "rb") as fh:
                transcript = litellm.transcription(
                    model="whisper-1",
                    file=fh,
                    prompt=history,
                    language=language,
                )
            return transcript.text
        except Exception as err:
            print(f"Unable to transcribe {filename}: {err}")
            return

    def _cleanup_files(self, filename, temp_wav, use_audio_format):
        # Remove temp files
        if filename != temp_wav and os.path.exists(filename):
            os.remove(filename)
        if os.path.exists(temp_wav):
            os.remove(temp_wav)


if __name__ == "__main__":
    use_local = HAS_WHISPER_CPP
    try:
        if use_local:
            print("Using local transcription with pywhispercpp")
            print(Voice(use_local=True).record_and_transcribe())
        else:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "Please set the OPENAI_API_KEY environment variable for API transcription."
                )
            print(Voice().record_and_transcribe())
    except SoundDeviceError as e:
        print(f"SoundDeviceError: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
