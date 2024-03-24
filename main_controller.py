import os
import time
import re
from word_detector import setup_keyword_detection, set_message_handler
from audio_recorder import start_recording, stop_recording
from assemblyai_transcriber import AssemblyAITranscriber
from assistant_manager import AssistantManager
from eleven_labs_manager import ElevenLabsManager
from vision_module import VisionModule
import openai
from openai import AssistantEventHandler

# Initialize OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY")
openai_client = openai # This line initializes openai_client with the openai library itself

# Initialize modules with provided API keys
assemblyai_transcriber = AssemblyAITranscriber(api_key=os.getenv("ASSEMBLYAI_API_KEY"))
# Adjusted to use the hardcoded Assistant ID
eleven_labs_manager = ElevenLabsManager(api_key=os.getenv("ELEVENLABS_API_KEY"))
vision_module = VisionModule(openai_api_key=os.getenv("OPENAI_API_KEY"))

# State variables
is_recording = False
picture_mode = False
last_thread_id = None
last_interaction_time = None

# Global variable to hold the concatenated text
concatenated_text = ""

# Global set to track processed message IDs
processed_messages = set()

# Global variable for transcription
transcription = ""

def handle_detected_words(words):
    global is_recording, picture_mode, last_thread_id, last_interaction_time
    detected_phrase = ' '.join(words).lower().strip()
    print(f"Detected phrase: {detected_phrase}")

    if "computer" in detected_phrase and not is_recording:
        start_recording()
        is_recording = True
        print("Recording started...")
    elif "snapshot" in detected_phrase and is_recording:
        picture_mode = True
        print("Picture mode activated...")
    elif "reply" in detected_phrase and is_recording:
        stop_recording()
        is_recording = False
        print("Recording stopped. Processing...")
        process_recording()

def process_recording():
    global picture_mode, last_thread_id, last_interaction_time, transcription, assistant_manager
    transcription = assemblyai_transcriber.transcribe_audio_file("recorded_audio.wav")
    print(f"Transcription result: '{transcription}'")

    assistant_manager = AssistantManager(openai_client, eleven_labs_manager, assistant_id="asst_3D8tACoidstqhbw5JE2Et2st")

    assistant_manager.handle_initial_interaction(content=transcription)

    if picture_mode:
        vision_module.capture_image_async()
        description = vision_module.describe_captured_image(transcription=transcription)
        interact_with_assistant(description)
        picture_mode = False
    else:
        interact_with_assistant(transcription)

class CustomAssistantEventHandler(AssistantEventHandler):
    def __init__(self, eleven_labs_manager):
        self.eleven_labs_manager = eleven_labs_manager
        self.complete_response = ""  

    def on_text_created(self, text) -> None:
        self.complete_response += text  
        self.play_response()

    def on_text_delta(self, delta, snapshot):
        if 'content' in delta:  
            for content_change in delta['content']:  
                if content_change['type'] == 'text':
                    text_value = content_change['text']['value']
                    print(text_value, end="", flush=True)
                    global concatenated_text
                    concatenated_text += text_value

    def play_response(self):
        if self.complete_response.strip():
            print(f"Playing message: {self.complete_response}")  
            self.eleven_labs_manager.play_text(self.complete_response)
            self.complete_response = ""  

def process_and_play_text():
    global concatenated_text
    sentences = re.split(r'[.?\n]+', concatenated_text)
    sentences = [sentence.strip() for sentence in sentences if sentence]

    for sentence in sentences:
        print(f"Playing: {sentence}")
        eleven_labs_manager.play_text(sentence)

    concatenated_text = ""

def interact_with_assistant(transcription):
    global last_thread_id, last_interaction_time
    print("Interacting with assistant...")  

    custom_event_handler = CustomAssistantEventHandler(eleven_labs_manager)
    assistant_manager = AssistantManager(openai_client, eleven_labs_manager, assistant_id="asst_3D8tACoidstqhbw5JE2Et2st")
    assistant_manager.set_event_handler(custom_event_handler)

    if last_thread_id and time.time() - last_interaction_time <= 90:
        print(f"Using existing thread: {last_thread_id}")
        assistant_manager.thread_id = last_thread_id
    else:
        print("Creating new thread...")
        last_thread_id = assistant_manager.create_thread()
        assistant_manager.thread_id = last_thread_id

    assistant_manager.add_message_to_thread(transcription)
    last_interaction_time = time.time()

    assistant_manager.handle_streaming_interaction()

def on_thread_message_completed(data):
    global processed_messages, last_thread_id
    message_id = data.get('id')
    if message_id in processed_messages:
        print(f"Message {message_id} already processed.")
        return
    processed_messages.add(message_id)
    print("Handling ThreadMessageCompleted event...")
    message_content = data.get('content', [])
    for content_block in message_content:
        if content_block['type'] == 'text':
            message_text = content_block['text']['value']
            print(f"Received message: {message_text}")
            print(f"Playing message: {message_text}")  
            eleven_labs_manager.play_text(message_text)

    setup_keyword_detection()

    last_thread_id = data.get('thread_id')
    
    

event_handlers = {
    'thread.message.completed': on_thread_message_completed,
}

def dispatch_event(event_type, data):
    handler = event_handlers.get(event_type)
    if handler:
        handler(data)
    else:
        print(f"No handler for event type: {event_type}")

def on_thread_run_step_completed(data):
    message_content = data.get('content', [])
    response_text = ""
    for content_block in message_content:
        if content_block['type'] == 'text':
            response_text += content_block['text']['value']
    if response_text.strip():
        print(f"Playing response: {response_text}")  
        eleven_labs_manager.play_text(response_text)
        print(f"Playing response: {response_text}")
    last_thread_id = data.get('thread_id')
    setup_keyword_detection()


def initialize():
    print("System initializing...")
    set_message_handler(handle_detected_words)
    setup_keyword_detection()

if __name__ == "__main__":
    initialize()
    while True:
        time.sleep(1)
        
        event_received = {
            'event': 'thread.message.completed',
            'data': {
                'id': 'msg_jsoCM86BSagjg4OzAjPKcwhx',
                'content': [
                    {
                        'text': {
                            'value': 'Hello! How can I assist you today?'
                        },
                        'type': 'text'
                    }
                ],
                # Other fields omitted for brevity
            }
        }
        dispatch_event(event_received['event'], event_received['data'])
