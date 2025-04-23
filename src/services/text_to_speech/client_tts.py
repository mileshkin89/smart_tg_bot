"""
This module provides integration with Google Text-to-Speech API.

It defines a `TextToSpeech` class responsible for:
- Initializing the API client with Google credentials.
- Converting text into synthesized speech using customizable voice settings.
- Saving the resulting audio as a .ogg file in the configured directory.

Main Components:
- TextToSpeech: Handles initialization and text-to-speech synthesis.
- synthesize(): Converts input text into an OGG audio file.
"""

import os
import uuid
from pathlib import Path
import asyncio
from google.cloud import texttospeech
from settings.config import config


class TextToSpeech:
    def __init__(self):
        """
        Initializes the TextToSpeech client using Google Cloud credentials.

        Loads credentials from `TTS.json` and creates an instance
        of `google.cloud.texttospeech.TextToSpeechClient`.

        Environment variable:
            GOOGLE_APPLICATION_CREDENTIALS is set internally.
        """
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(
            config.path_to_google_credentials / "TTS.json"
        )
        self.client = texttospeech.TextToSpeechClient()

    async def synthesize(self, text: str, language_code: str = "en-US", voice_name: str = "en-US-Wavenet-D") -> Path:
        """
        Asynchronously converts the given text into synthesized speech and saves it as an audio file.

        Args:
            text (str): The text string to be synthesized into speech.
            language_code (str): The BCP-47 language code (default is "en-US").
            voice_name (str): The specific Google voice model to use (default is "en-US-Wavenet-D").

        Returns:
            Path: The full path to the generated OGG audio file.

        Side Effects:
            - Creates an audio file in the directory defined by `config.path_to_stt_audio_file`.
        """
        loop = asyncio.get_running_loop()

        def _synthesize_sync():
            input_text = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.OGG_OPUS
            )
            return self.client.synthesize_speech(
                input=input_text,
                voice=voice,
                audio_config=audio_config
            )

        response = await loop.run_in_executor(None, _synthesize_sync)

        output_dir = config.path_to_stt_audio_file
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"{uuid.uuid4().hex}.ogg"
        with open(output_path, "wb") as out:
            out.write(response.audio_content)

        return output_path

