import sys
import traceback
try:
    import os
    import time
    from logging_module import log
    from word_detector import setup_keyword_detection, set_message_handler
    from audio_recorder import start_recording, stop_recording
    from assemblyai_transcriber import AssemblyAITranscriber
    from assistant_manager import AssistantManager
    from eleven_labs_manager import ElevenLabsManager
    from vision_module import VisionModule

    # Initialize modules with provided API keys
    assemblyai_transcriber = AssemblyAITranscriber(api_key=os.getenv("ASSEMBLYAI_API_KEY"))
    assistant_manager = AssistantManager(openai_api_key=os.getenv("OPENAI_API_KEY"))
    eleven_labs_manager = ElevenLabsManager(api_key=os.getenv("ELEVENLABS_API_KEY"))
except ImportError as e:
    error_message = str(e)
    traceback_text = traceback.format_exc()
    sys.stderr.write(f"{error_message}\n{traceback_text}")
    if 'log' in globals():
        log('error', f"Import error encountered.\nError message: {error_message}\nTraceback: {traceback_text}")
vision_module = VisionModule(openai_api_key=os.getenv("OPENAI_API_KEY"))

# State variables
is_recording = False
picture_mode = False
last_thread_id = None
last_interaction_time = None

def handle_detected_words(words):
    global is_recording, picture_mode, last_thread_id, last_interaction_time
    detected_phrase = ' '.join(words).lower().strip()
    log('info', f"Detected phrase: {detected_phrase}")

    if "computer" in detected_phrase and not is_recording:
        start_recording()
        is_recording = True
        log('info', f"Recording started due to detection of the keyword 'computer'.")
    elif "snapshot" in detected_phrase and is_recording:
        picture_mode = True
        log('info', f"Picture mode activated due to detection of the keyword 'snapshot'.")
    elif "reply" in detected_phrase and is_recording:
        stop_recording()
        is_recording = False
        log('info', f"Recording stopped and processing started due to detection of the keyword 'reply'.")
        process_recording()

def process_recording():
    global picture_mode, last_thread_id, last_interaction_time
    log('info', "Processing recorded audio...")
    transcription = assemblyai_transcriber.transcribe_audio_file("recorded_audio.wav")
    log('info', f"Transcription result: '{transcription}'")

    if picture_mode:
        vision_module.capture_image_async()
        description = vision_module.describe_captured_image(transcription=transcription)
        # If there's a recent thread, send the description to it
        if last_thread_id:
            assistant_manager.add_message_to_thread(last_thread_id, description)
            log('info', f"Description sent to the most recent thread: {last_thread_id}")
        eleven_labs_manager.play_text(description)
        picture_mode = False
    else:
        interact_with_assistant(transcription)


def interact_with_assistant(transcription):
    global last_thread_id, last_interaction_time
    log('info', f"Initiating interaction with assistant with transcription: {transcription}")
    if not last_thread_id or time.time() - last_interaction_time > 90:
        last_thread_id = assistant_manager.create_thread()
    log('info', f"Using thread ID: {last_thread_id} for the current interaction")

    last_interaction_time = time.time()

    message_id = assistant_manager.add_message_to_thread(last_thread_id, transcription)
    log('info', f"Message added to the thread with ID: {message_id}")
    # Initiate a run on the thread for the assistant to process the message
    run_id = assistant_manager.run_assistant(last_thread_id, assistant_id="asst_3D8tACoidstqhbw5JE2Et2st", instructions=transcription)
    log('info', f"Assistant run initiated with run ID: {run_id}")

    # Check if the run is completed and retrieve the processed response
    if assistant_manager.check_run_status(last_thread_id, run_id):
        response = assistant_manager.retrieve_most_recent_message(last_thread_id)
        # Assuming response contains a complex structure, extract the actual value
        # This is a placeholder; you will need to adjust the extraction logic based on your actual data structure
        processed_response = response.content[0].text.value
        eleven_labs_manager.play_text(processed_response)
        log('info', f'Played back the assistants response: {processed_response}')
    else:
        log('info', "Assistant processing failed or timed out.")



def initialize():
    log('info', "System initializing...")
    set_message_handler(handle_detected_words)
    setup_keyword_detection()

if __name__ == "__main__":
    initialize()
    while True:
        time.sleep(1)
