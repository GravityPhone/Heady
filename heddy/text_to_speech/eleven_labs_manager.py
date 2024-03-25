import requests
import os
# from pydub import AudioSegment
# Import the play function from elevenlabs/utils.py
from elevenlabs import play
import io

class ElevenLabsManager:
    def __init__(self, api_key):
        self.api_key = api_key
        self.voice_id = "RXZFrCz94YM9cSj7aieu"
        self.model_id = "eleven_turbo_v2"
        self.url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream"

    def play_text(self, text):
        query_params = {
            "optimize_streaming_latency": 0,
            "output_format": "mp3_44100_128"
        }

        payload = {
            "model_id": self.model_id,
            "text": text,
            "voice_settings": {
                "similarity_boost": 1.0,
                "stability": 1.0,
                "style": 1.0,
                "use_speaker_boost": True
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Xi-Api-Key": self.api_key
        }

        response = requests.post(self.url, params=query_params, json=payload, headers=headers)

        if response.status_code == 200:
            # Directly play the audio content without saving
            play(response.content)
        else:
            print(f"Failed to convert text to speech. Status code: {response.status_code}, Response: {response.text}")
