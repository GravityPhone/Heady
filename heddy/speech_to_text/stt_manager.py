from dataclasses import dataclass
from typing import Optional
from enum import Enum

class STTStatus(Enum):
    SUCCESS = 1
    ERROR = -1

@dataclass
class STTResult:
    text: Optional[str]
    error: Optional[str]
    status: STTStatus

class STTManager:
    def __init__(self, transcriber) -> None:
        self.transcriber = transcriber

    def transcribe_audio_file(self, audio_file_path):
        return self.transcriber.transcribe_audio_file(audio_file_path)
    