import math
import os
import queue
import tempfile
import time
import warnings

import av
import av.codec
import av.container
import av.filter
import av.stream
from prompt_toolkit.shortcuts import prompt

from aider.llm import litellm

from .dump import dump  # noqa: F401

warnings.filterwarnings(
    "ignore", message="Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work"
)
warnings.filterwarnings("ignore", category=SyntaxWarning)

try:
    import soundfile as sf
except (OSError, ModuleNotFoundError):
    sf = None


# Custom exception for FFmpeg-related errors during audio processing
class FFmpegError(Exception):
    pass


class SoundDeviceError(Exception):
    pass


class Voice:
    max_rms = 0
    min_rms = 1e5
    pct = 0

    threshold = 0.15

    def __init__(self, audio_format="wav", device_name=None):
        if sf is None:
            raise SoundDeviceError
        try:
            print("Initializing sound device...")
            import sounddevice as sd

            self.sd = sd

            devices = sd.query_devices()

            if device_name:
                # Find the device with matching name
                device_id = None
                for i, device in enumerate(devices):
                    if device_name in device["name"]:
                        device_id = i
                        break
                if device_id is None:
                    available_inputs = [d["name"] for d in devices if d["max_input_channels"] > 0]
                    raise ValueError(
                        f"Device '{device_name}' not found. Available input devices:"
                        f" {available_inputs}"
                    )

                print(f"Using input device: {device_name} (ID: {device_id})")

                self.device_id = device_id
            else:
                self.device_id = None

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
            sample_rate = int(self.sd.query_devices(self.device_id, "input")["default_samplerate"])
        except (TypeError, ValueError):
            sample_rate = 16000  # fallback to 16kHz if unable to query device
        except self.sd.PortAudioError:
            raise SoundDeviceError(
                "No audio input device detected. Please check your audio settings and try again."
            )

        self.start_time = time.time()

        try:
            with self.sd.InputStream(
                samplerate=sample_rate, channels=1, callback=self.callback, device=self.device_id
            ):
                prompt(self.get_prompt, refresh_interval=0.1)
        except self.sd.PortAudioError as err:
            raise SoundDeviceError(f"Error accessing audio input device: {err}")

        with sf.SoundFile(temp_wav, mode="x", samplerate=sample_rate, channels=1) as file:
            while not self.q.empty():
                file.write(self.q.get())

        use_audio_format = self.audio_format

        # Check file size and offer to convert to mp3 if too large
        file_size = os.path.getsize(temp_wav)
        filename = temp_wav
        output_filename = None

        if file_size > 24.9 * 1024 * 1024 and self.audio_format == "wav":
            print(
                f"\nWarning: {temp_wav} is too large ({file_size / (1024 * 1024):.2f}MB),"
                " switching to mp3 format."
            )
            use_audio_format = "mp3"

        if use_audio_format != "wav":
            try:
                output_filename = tempfile.mktemp(suffix=f".{use_audio_format}")

                with av.open(temp_wav, "r") as in_container:
                    in_stream = in_container.streams.audio[0]

                    with av.open(output_filename, "w") as out_container:
                        stream_options = {}

                        # Attempt to match input properties
                        if in_stream.sample_rate:
                            stream_options["sample_rate"] = str(in_stream.sample_rate)
                        if in_stream.channels:
                            stream_options["channels"] = str(in_stream.channels)
                        if in_stream.format.name:
                            # Use an appropriate sample format if possible, otherwise default
                            # For simplicity, we'll try to set common sensible defaults
                            if use_audio_format == "mp3":
                                stream_options["sample_fmt"] = "fltp"  # MP3 often uses float planar
                            else:
                                # Ensure default format is string if in_stream.format.name is None
                                stream_options["sample_fmt"] = (
                                    in_stream.format.name if in_stream.format.name else "s16"
                                )

                        # Set bitrate, common for MP3
                        if use_audio_format == "mp3":
                            stream_options["bit_rate"] = str(128000)  # 128 kbps

                        out_stream = out_container.add_stream(
                            use_audio_format, options=stream_options
                        )

                        for frame in in_container.decode(in_stream):
                            for packet in out_stream.encode(frame):
                                out_container.mux(packet)
                        # Flush stream
                        for packet in out_stream.encode():
                            out_container.mux(packet)

                os.remove(temp_wav)
                filename = output_filename

            except av.FFmpegError as e:
                print(f"Error converting audio with FFmpeg: {e}")
                if output_filename and os.path.exists(output_filename):
                    os.remove(output_filename)
                # Fallback to original wav if conversion fails and continue attempting transcription
            except (OSError, FileNotFoundError) as e:
                print(f"File system error during conversion: {e}")
                # Fallback to original wav
            except Exception as e:
                print(f"Unexpected error during audio conversion: {e}")
                # Fallback to original wav

        # Ensure filename is set to the correct file for transcription
        if output_filename and os.path.exists(output_filename):
            filename = output_filename
        else:
            filename = temp_wav  # Use the original WAV if conversion failed or wasn't needed

        with open(filename, "rb") as fh:
            try:
                transcript = litellm.transcription(
                    model="whisper-1", file=fh, prompt=history, language=language
                )
            except Exception as err:
                print(f"Unable to transcribe {filename}: {err}")
                if output_filename and os.path.exists(output_filename):
                    os.remove(output_filename)
                os.remove(temp_wav)
                return

        # Clean up files regardless of transcription success, but only if they exist
        if output_filename and os.path.exists(output_filename):
            os.remove(output_filename)
        if temp_wav and os.path.exists(temp_wav):  # Always remove the initial temp wav
            os.remove(temp_wav)

        return transcript.text


if __name__ == "__main__":
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set the OPENAI_API_KEY environment variable.")
    print(Voice().record_and_transcribe())
