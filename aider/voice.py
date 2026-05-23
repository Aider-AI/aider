
import math
import os
import queue
import tempfile
import time
import numpy as np
import warnings
from typing import Optional, Tuple, Union

from prompt_toolkit.shortcuts import prompt

from .dump import dump  # noqa: F401

warnings.filterwarnings(
    "ignore", message="Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work"
)
warnings.filterwarnings("ignore", category=SyntaxWarning)

from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError, CouldntEncodeError

try:
    import soundfile as sf
except (OSError, ModuleNotFoundError):
    sf = None

try:
    import google.cloud.speech as speech
except (OSError, ModuleNotFoundError):
    speech = None

try:
    import azure.cognitiveservices.speech as speech_sdk
except (OSError, ModuleNotFoundError):
    speech_sdk = None

try:
    import openai
except (OSError, ModuleNotFoundError):
    openai = None

from groq import Groq  # Updated import

class SoundDeviceError(Exception):
    pass

class Voice:
    """
    A class to handle audio recording and transcription using sounddevice and various transcription services.
    """

    def __init__(self, audio_format: str = "wav", device_name: Optional[str] = None, provider: str = "groq", api_key: Optional[str] = None):
        """
        Initialize the Voice class.

        Args:
            audio_format: The format of the output audio file. Supported formats: 'wav', 'mp3', 'webm'.
            device_name: The name of the audio input device to use. If None, the default device is used.
            provider: The transcription service provider. Supported providers: 'groq', 'google', 'microsoft', 'openai'.
            api_key: Optional API key for the transcription service. If not provided, it will be retrieved from environment variables.

        Raises:
            SoundDeviceError: If sounddevice or soundfile is not available.
            ValueError: If the audio_format is not supported or the device_name is not found.
        """
        if sf is None:
            raise SoundDeviceError("soundfile is not available. Please install it.")

        try:
            import sounddevice as sd
            self.sd = sd
        except (OSError, ModuleNotFoundError):
            raise SoundDeviceError("sounddevice is not available. Please install it.")

        if audio_format not in ["wav", "mp3", "webm"]:
            raise ValueError(f"Unsupported audio format: {audio_format}. Supported formats: wav, mp3, webm.")

        self.audio_format = audio_format
        self.device_id = None
        self.provider = provider
        self.api_key = api_key

        if device_name:
            devices = self.sd.query_devices()
            device_id = None
            for i, device in enumerate(devices):
                if device_name.lower() in device["name"].lower():
                    device_id = i
                    break
            if device_id is None:
                available_inputs = [d["name"] for d in devices if d["max_input_channels"] > 0]
                raise ValueError(
                    f"Device '{device_name}' not found. Available input devices: {available_inputs}"
                )
            self.device_id = device_id
            print(f"Using input device: {device_name} (ID: {device_id})")

        self._validate_provider()

    def _validate_provider(self):
        supported_providers = ['groq', 'google', 'microsoft', 'openai']
        if self.provider not in supported_providers:
            raise ValueError(f"Unsupported provider: {self.provider}. Supported providers: {supported_providers}")

        if self.provider == 'google' and speech is None:
            raise ValueError("google.cloud.speech is not available. Please install google-cloud-speech.")
        
        if self.provider == 'microsoft' and speech_sdk is None:
            raise ValueError("azure.cognitiveservices.speech is not available. Please install azure-cognitive-services-speech.")

        if self.provider == 'openai' and openai is None:
            raise ValueError("openai is not available. Please install openai.")

    def set_api_key(self):
        if self.provider == 'groq':
            self.api_key = os.getenv("GROQ_API_KEY")
            if not self.api_key:
                raise ValueError("Please set the GROQ_API_KEY environment variable.")
        elif self.provider == 'google':
            self.api_key = os.getenv("GOOGLE_API_KEY")
            if not self.api_key:
                raise ValueError("Please set the GOOGLE_API_KEY environment variable.")
        elif self.provider == 'microsoft':
            self.api_key = os.getenv("AZURE_SPEECH_KEY")
            if not self.api_key:
                raise ValueError("Please set the AZURE_SPEECH_KEY environment variable.")
        elif self.provider == 'openai':
            self.api_key = os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("Please set the OPENAI_API_KEY environment variable.")

    def callback(self, indata: np.ndarray, frames: int, time: float, status: int) -> None:
        """
        Callback function for audio data processing.

        Args:
            indata: The audio data.
            frames: The number of frames.
            time: The time stamp.
            status: The stream status.
        """
        import numpy as np

        rms = np.sqrt(np.mean(indata ** 2))
        self.max_rms = max(self.max_rms, rms)
        self.min_rms = min(self.min_rms, rms)

        rng = self.max_rms - self.min_rms
        if rng > 0.001:
            self.pct = (rms - self.min_rms) / rng
        else:
            self.pct = 0.5

        self.q.put(indata.copy())

    def get_prompt(self) -> str:
        """
        Generate a progress prompt string.

        Returns:
            A formatted string showing recording status and progress bar.
        """
        num = 10
        if math.isnan(self.pct) or self.pct < self.threshold:
            cnt = 0
        else:
            cnt = int(self.pct * 10)

        bar = "░" * cnt + "█" * (num - cnt)
        bar = bar[:num]

        dur = time.time() - self.start_time
        return f"Recording, press ENTER when done... {dur:.1f}s {bar}"

    def record_and_transcribe(self, history: Optional[list] = None, language: Optional[str] = None) -> Optional[str]:
        """
        Record audio and transcribe it.

        Args:
            history: Optional list of previous commands/transcripts for context.
            language: Optional language code for transcription.

        Returns:
            The transcribed text or None if an error occurs.
        """
        try:
            return self.raw_record_and_transcribe(history, language)
        except KeyboardInterrupt:
            print("\nRecording stopped by user.")
            return None
        except SoundDeviceError as e:
            print(f"Error: {e}")
            print("Please ensure you have a working audio input device connected and try again.")
            return None

    def raw_record_and_transcribe(self, history: Optional[list], language: Optional[str]) -> Optional[str]:
        """
        Raw method to record and transcribe audio without exception handling.

        Args:
            history: Optional list of previous commands/transcripts for context.
            language: Optional language code for transcription.

        Returns:
            The transcribed text or None if an error occurs.
        """
        self.max_rms = 0
        self.min_rms = 1e5
        self.pct = 0
        self.threshold = 0.15
        self.q = queue.Queue()

        temp_wav = tempfile.mktemp(suffix=".wav")

        try:
            sample_rate = int(self.sd.query_devices(self.device_id, "input")["default_samplerate"])
        except (TypeError, ValueError):
            sample_rate = 16000  # Fallback to 16kHz
        except self.sd.PortAudioError:
            raise SoundDeviceError(
                "No audio input device detected. Please check your audio settings and try again."
            )

        self.start_time = time.time()

        try:
            with self.sd.InputStream(
                samplerate=sample_rate, channels=1, callback=self.callback, device=self.device_id
            ) as stream:
                prompt(self.get_prompt, refresh_interval=0.1)
        except self.sd.PortAudioError as err:
            raise SoundDeviceError(f"Error accessing audio input device: {err}")

        # Write recorded data to file
        try:
            with sf.SoundFile(temp_wav, mode="x", samplerate=sample_rate, channels=1) as file:
                while not self.q.empty():
                    file.write(self.q.get())
        except Exception as e:
            print(f"Error writing audio data: {e}")
            return None

        # Convert audio format if necessary
        use_audio_format = self.audio_format
        filename = temp_wav

        # Check file size and offer to convert to mp3 if too large
        file_size = os.path.getsize(temp_wav)
        if file_size > 24.9 * 1024 * 1024 and self.audio_format == "wav":
            print("\nWarning: The WAV file is too large, switching to MP3 format.")
            use_audio_format = "mp3"

            try:
                new_filename = tempfile.mktemp(suffix=f".{use_audio_format}")
                audio = AudioSegment.from_wav(temp_wav)
                audio.export(new_filename, format=use_audio_format)
                os.remove(temp_wav)
                filename = new_filename
            except Exception as e:
                print(f"Error converting audio: {e}")
                use_audio_format = "wav"
                filename = temp_wav

        # Set API key based on provider
        self.set_api_key()

        # Transcribe audio using the selected provider
        if self.provider == 'groq':
            return self._transcribe_groq(filename, language)
        elif self.provider == 'google':
            return self._transcribe_google(filename, language)
        elif self.provider == 'microsoft':
            return self._transcribe_microsoft(filename, language)
        elif self.provider == 'openai':
            return self._transcribe_openai(filename, language)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _transcribe_groq(self, filename: str, language: Optional[str] = None) -> Optional[str]:
        """
        Transcribe audio using Groq's Whisper model.

        Args:
            filename: Path to the audio file.
            language: Optional language code for transcription.

        Returns:
            The transcribed text or None if an error occurs.
        """
        try:
            client = Groq(api_key=self.api_key)
            with open(filename, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    file=(os.path.basename(filename), audio_file.read()),
                    model="distil-whisper-large-v3-en"
                )
                return transcript.text
        except Exception as e:
            print(f"Unable to transcribe audio using Groq: {e}")
            return None

    def _transcribe_google(self, filename: str, language: Optional[str] = None) -> Optional[str]:
        """
        Transcribe audio using Google Cloud Speech-to-Text.

        Args:
            filename: Path to the audio file.
            language: Optional language code for transcription.

        Returns:
            The transcribed text or None if an error occurs.
        """
        if language is None:
            language = "en-US"

        try:
            client = speech.SpeechClient()
            with open(filename, "rb") as audio_file:
                audio = speech.RecognitionAudio(content=audio_file.read())
                config = speech.RecognitionConfig(
                    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                    language_code=language,
                )
                response = client.recognize(config, audio)
                return " ".join([result.alternatives[0].transcript for result in response.results])
        except Exception as e:
            print(f"Unable to transcribe audio using Google: {e}")
            return None

    def _transcribe_microsoft(self, filename: str, language: Optional[str] = None) -> Optional[str]:
        """
        Transcribe audio using Microsoft Azure Speech Services.

        Args:
            filename: Path to the audio file.
            language: Optional language code for transcription.

        Returns:
            The transcribed text or None if an error occurs.
        """
        if language is None:
            language = "en-US"

        try:
            speech_config = speech_sdk.SpeechConfig(subscription=self.api_key, region="global")
            audio_config = speech_sdk.AudioConfig(filename=filename)
            speech_recognizer = speech_sdk.SpeechRecognizer(speech_config, audio_config=audio_config)
            
            result = speech_recognizer.recognize_once()
            return result.text
        except Exception as e:
            print(f"Unable to transcribe audio using Microsoft: {e}")
            return None

    def _transcribe_openai(self, filename: str, language: Optional[str] = None) -> Optional[str]:
        """
        Transcribe audio using OpenAI Whisper model.

        Args:
            filename: Path to the audio file.
            language: Optional language code for transcription.

        Returns:
            The transcribed text or None if an error occurs.
        """
        try:
            client = openai.OpenAI(api_key=self.api_key)
            with open(filename, "rb") as audio_file:
                response = client.audio.transcriptions.create(
                    "whisper-1",
                    file=audio_file.read()
                )
                return response.text
        except Exception as e:
            print(f"Unable to transcribe audio using OpenAI: {e}")
            return None

if __name__ == "__main__":
    # Example usage with different providers
    voice_groq = Voice(provider='groq')
    transcript_groq = voice_groq.record_and_transcribe()
    if transcript_groq:
        print("\nTranscript (Groq):")
        print(transcript_groq)

    voice_google = Voice(provider='google')
    transcript_google = voice_google.record_and_transcribe()
    if transcript_google:
        print("\nTranscript (Google):")
        print(transcript_google)

    voice_microsoft = Voice(provider='microsoft')
    transcript_microsoft = voice_microsoft.record_and_transcribe()
    if transcript_microsoft:
        print("\nTranscript (Microsoft):")
        print(transcript_microsoft)

    voice_openai = Voice(provider='openai')
    transcript_openai = voice_openai.record_and_transcribe()
    if transcript_openai:
        print("\nTranscript (OpenAI):")
        print(transcript_openai)