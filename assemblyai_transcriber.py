import assemblyai as aai
from logging_module import log

class AssemblyAITranscriber:
    def __init__(self, api_key):
        # Set the API key globally for the assemblyai package
        aai.settings.api_key = api_key

    def transcribe_audio_file(self, audio_file_path):
        log('info', 'Transcription started.')
        # Instantiate the Transcriber object
        transcriber = aai.Transcriber()
        # Start the transcription process
        transcript = transcriber.transcribe(audio_file_path)
        log('info', f'Transcription result: {transcript.text}')
        
        # Check the transcription status and return the appropriate response
        if transcript.status == aai.TranscriptStatus.error:
            log('error', 'Transcription ended with an error.')
            return transcript.error
        else:
            log('info', 'Transcription completed successfully.')
            return transcript.text

# The following testing code should be commented out or removed in the integration
# if __name__ == "__main__":
#     transcriber = AssemblyAITranscriber(api_key="9c45c5934f8f4dcd9c13c54875145c77")
#     log('info', transcriber.transcribe_audio_file("./path_to_your_audio_file.wav"))
