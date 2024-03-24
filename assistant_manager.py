import openai
import time
from openai.lib.streaming import AssistantEventHandler
from openai.types.beta import Assistant, Thread
from openai.types.beta.threads import Run, RequiredActionFunctionToolCall
from openai.types.beta.assistant_stream_event import (
    ThreadRunRequiresAction, ThreadMessageDelta, ThreadRunCompleted,
    ThreadRunFailed, ThreadRunCancelling, ThreadRunCancelled, ThreadRunExpired, ThreadRunStepFailed,
    ThreadRunStepCancelled)

class EventHandler(AssistantEventHandler):
    
    def on_text_created(self, text: str) -> None:
        print(f"\nassistant > ", end="", flush=True)

    def on_text_delta(self, delta, snapshot):
        # Access the delta attribute correctly
        if 'content' in delta:
            for content_change in delta['content']:
                if content_change['type'] == 'text':
                    print(content_change['text']['value'], end="", flush=True)
                    if 'annotations' in content_change['text']:
                        print("Annotations:", content_change['text']['annotations'])

    def on_tool_call_created(self, tool_call: RequiredActionFunctionToolCall):
        print(f"\nassistant > {tool_call.type}\n", flush=True)

    def on_tool_call_delta(self, delta: RequiredActionFunctionToolCall, snapshot: RequiredActionFunctionToolCall):
        if delta.type == 'code_interpreter':
            if delta.code_interpreter.input:
                print(delta.code_interpreter.input, end="", flush=True)
            if delta.code_interpreter.outputs:
                print(f"\n\noutput >", flush=True)
                for output in delta.code_interpreter.outputs:
                    if output.type == "logs":
                        print(f"\n{output.logs}", flush=True)



class AssistantManager:
    def __init__(self, client, eleven_labs_manager, assistant_id=None):
        self.client = client
        self.eleven_labs_manager = eleven_labs_manager
        self.assistant_id = assistant_id
        self.event_handler = None
        self.thread_id = None
        self.last_interaction_time = None
        self.interaction_in_progress = False

    def set_event_handler(self, event_handler):
        self.event_handler = event_handler

    def create_thread(self):
        if self.thread_id is not None:
            print(f"Thread already exists: {self.thread_id}")
            return self.thread_id

        try:
            thread = self.client.beta.threads.create()
            self.thread_id = thread.id
            print(f"New thread created: {self.thread_id}")
            return self.thread_id
        except Exception as e:
            print(f"Failed to create a thread: {e}")
            return None

    def add_message_to_thread(self, content):
        if not self.thread_id:
            print("No thread ID set. Cannot add message.")
            return

        try:
            message = self.client.beta.threads.messages.create(
                thread_id=self.thread_id,
                role="user",
                content=content
            )
            print(f"Message added to thread: {self.thread_id}")
        except Exception as e:
            print(f"Failed to add message to thread: {e}")

    def handle_interaction(self, content):
        if self.should_create_new_thread():
            self.create_thread()

        self.add_message_to_thread(content)
        self.last_interaction_time = time.time()
        self.interaction_in_progress = True

    def should_create_new_thread(self):
        # Create a new thread if there's no existing thread or if the last interaction was too long ago
        if self.thread_id is None or time.time() - self.last_interaction_time > 90:
            return True
        # Avoid creating a new thread if the previous interaction is still in progress
        if self.interaction_in_progress:
            return False
        return True

    def handle_streaming_interaction(self):
        if not self.thread_id or not self.assistant_id:
            print("Thread ID or Assistant ID is not set.")
            return

        event_handler = self.event_handler if self.event_handler else EventHandler()

        with self.client.beta.threads.runs.create_and_stream(
            thread_id=self.thread_id,
            assistant_id=self.assistant_id,
        ) as stream:
            for event in stream:
                print("Event received:", event)  # Debug print to confirm events are received
                # Handle the message content for events with a 'data' attribute containing a message
                if hasattr(event, 'data') and hasattr(event.data, 'content'):
                    for content_block in event.data.content:
                        if content_block.type == 'text':
                            message_text = content_block.text.value
                            print(f"Playing message: {message_text}")  # Print statement before playing
                            self.eleven_labs_manager.play_text(message_text)  # Play the text using ElevenLabsManager
                            print("Message played using ElevenLabsManager.")  # Print statement after playing
                            break  # Assuming you only want to print and play the first text block
                # Existing event handling logic
                if isinstance(event, ThreadMessageDelta):
                    event_handler.on_text_delta(event.data.delta, None)
                elif isinstance(event, ThreadRunRequiresAction):
                    event_handler.on_tool_call_created(event.tool_call)
                elif isinstance(event, ThreadRunCompleted):
                    print("\nInteraction completed.")
                    break  # Exit the loop once the interaction is complete
                elif isinstance(event, ThreadRunFailed):
                    print("\nInteraction failed.")
                    break  # Exit the loop if the interaction fails
                # Add more event types as needed based on your application's requirements



    # Additional methods as needed...
