import os
from google.cloud import speech
from settings.config import config


class SpeechToText:
    def __init__(self, credentials_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_path)
        self.client = speech.SpeechClient()

    def recognize(self, file_path):
        with open(file_path, "rb") as audio_file:
            audio_content = audio_file.read()

        audio = {"content": audio_content}

        config_local = {
            "encoding": speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
            "sample_rate_hertz": 16000,
            "language_code": "ru-RU",
            "enable_automatic_punctuation": True,
            "max_alternatives": 3
        }

        response = self.client.recognize(config=config_local, audio=audio)

        if response.results:
            return response.results[0].alternatives[0].transcript
        return None


stt = SpeechToText(credentials_path=str(config.path_to_google_credentials / "STT.json"))
text = stt.recognize("audio_test2.ogg")
print(text)