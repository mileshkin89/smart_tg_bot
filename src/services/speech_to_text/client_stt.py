"""
This module integrates with the Google Cloud Speech-to-Text API.

It defines the `SpeechToText` class, which allows converting audio files
(in .ogg format) into text using Google's automatic speech recognition.

Main Components:
- SpeechToText: Initializes the API client and performs transcription.
- recognize(): Reads and transcribes audio files using multiple language options.
"""

import os
from google.cloud import speech
from settings.config import config


class SpeechToText:
    def __init__(self):
        """
        Initializes the Speech-to-Text client using Google Cloud credentials.

        Loads credentials from 'STT.json' and sets the GOOGLE_APPLICATION_CREDENTIALS
        environment variable required by the Google Cloud client.
        """
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(
            config.path_to_google_credentials / "STT.json"
        )
        self.client = speech.SpeechClient()


    def recognize(self, file_path):
        """
        Transcribes speech from a given audio file using Google Speech-to-Text API.

        Args:
            file_path (str or Path): Path to the audio file to be transcribed (expected format: OGG_OPUS, mono, 16kHz).

        Returns:
            str or None: The transcribed text if successful, otherwise None.

        Supported Languages (in total no more than 4):
            - Primary: English ("en-US")
            - Alternatives: Ukrainian ("uk-UA"), Russian ("ru-RU")

        Side Effects:
            - Logs transcription result to the console for debugging.
        """

        with open(file_path, "rb") as audio_file:
            audio_content = audio_file.read()

        audio = speech.RecognitionAudio(content=audio_content)

        config_stt = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
            sample_rate_hertz=16000,
            language_code="en-US",
            alternative_language_codes=["uk-UA" ,"ru-RU"],
            enable_automatic_punctuation=True,
            max_alternatives=3
        )

        response = self.client.recognize(config=config_stt, audio=audio)
        print(response)

        if response.results:
            print("Got result!")
            return response.results[0].alternatives[0].transcript
        else:
            print("No transcription found.")
            return None

