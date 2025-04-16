import os
# import asyncio
from google.cloud import speech
from settings.config import config


class SpeechToText:
    def __init__(self):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(
            config.path_to_google_credentials / "STT.json"
        )
        self.client = speech.SpeechClient()

    def recognize(self, file_path):
        with open(file_path, "rb") as audio_file:
            audio_content = audio_file.read()

        audio = speech.RecognitionAudio(content=audio_content)

        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
            sample_rate_hertz=16000,
            language_code="en-US",
            alternative_language_codes=["ru-RU", "uk-UA"],
            enable_automatic_punctuation=True,
            max_alternatives=3
        )

        response = self.client.recognize(config=config, audio=audio)
        print(response)

        if response.results:
            print("Got result!")
            # return await asyncio.to_thread(self.recognize, file_path)
            return response.results[0].alternatives[0].transcript
        else:
            print("No transcription found.")
            return None


# stt = SpeechToText()
# file_path = str(config.path_to_google_credentials / "audio_test2_new.ogg")
# text = stt.recognize(file_path)
# print(text)