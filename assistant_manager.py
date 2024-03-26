import openai
import time
import threading
import requests
import json
import logging
from state_manager import StateManager
from openai.lib.streaming import AssistantEventHandler
from openai.types.beta import Assistant, Thread
from openai.types.beta.threads import Run, RequiredActionFunctionToolCall
from openai.types.beta.assistant_stream_event import (
    ThreadRunRequiresAction, ThreadMessageDelta, ThreadRunCompleted,
    ThreadRunFailed, ThreadRunCancelling, ThreadRunCancelled, ThreadRunExpired, ThreadRunStepFailed,
    ThreadRunStepCancelled)

class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()

    def on_tool_call_created(self, tool_call_data):
        print("\nassistant > Processing tool call\n", flush=True)
        tool_call = tool_call_data.submit_tool_outputs.tool_calls[0]
        arguments = json.loads(tool_call.function.arguments)
        message = arguments['message']
        self.pending_tool_calls[tool_call.id] = message

    def on_run_completed(self, run_id, thread_id, assistant_id):
        for tool_call_id, message in self.pending_tool_calls.items():
            self.handle_tool_call_completion(message, tool_call_id, run_id, thread_id, assistant_id)
        self.pending_tool_calls.clear()

    def handle_tool_call_completion(self, message, tool_call_id, run_id, thread_id, assistant_id):
        try:
            self.send_text_via_zapier(message, tool_call_id, run_id)
        except Exception as e:
            logging.error(f"Exception occurred while sending text via Zapier.", exc_info=True)
            self.submit_tool_output(tool_call_id, run_id, "Failed to send text message.")

    def send_text_via_zapier(self, message, tool_call_id, run_id):
        webhook_url = "https://hooks.zapier.com/hooks/catch/82343/19816978ac224264aa3eec6c8c911e10/"
        payload = {"text": message}
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 200:
            logging.info("Text sent successfully via Zapier.")
            self.submit_tool_output(tool_call_id, run_id, "Text message sent successfully.")
        else:
            logging.error(f"Failed to send text via Zapier. Status code: {response.status_code}, Response: {response.text}")
            self.submit_tool_output(tool_call_id, run_id, "Failed to send text message.")

    def submit_tool_output(self, tool_call_id, run_id, output):
        self.client.beta.threads.runs.submit_tool_outputs(
            run_id=run_id,
            tool_outputs=[
                {
                    "tool_call_id": tool_call_id,
                    "output": output
                }
            ]
        )

class ThreadManager:
    def __init__(self, client):
        self.client = client
        self.thread_id = None
        self.interaction_in_progress = False
        self.reset_timer = None

    def create_thread(self):
        if self.thread_id is not None and not self.interaction_in_progress:
            print(f"Using existing thread: {self.thread_id}")
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

        if self.interaction_in_progress:
            print("Previous interaction still in progress. Please wait.")
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
        if not self.thread_id or not self.interaction_in_progress:
            self.create_thread()
        self.add_message_to_thread(content)
        StateManager.last_interaction_time = time.time()  # Update the time with each interaction
        self.interaction_in_progress = True
        self.reset_last_interaction_time()

    def reset_thread(self):
        print("Resetting thread.")
        self.thread_id = None
        self.interaction_in_progress = False

    def reset_last_interaction_time(self):
        # This method resets the last interaction time and calls reset_thread after 90 seconds
        def reset():
            StateManager.last_interaction_time = None
            self.reset_thread()  # Reset the thread once the timer completes
            print("Last interaction time reset and thread reset")
        
        # Cancel existing timer if it exists and is still running
        if self.reset_timer is not None and self.reset_timer.is_alive():
            self.reset_timer.cancel()
        
        # Create and start a new timer
        self.reset_timer = threading.Timer(90, reset)
        self.reset_timer.start()

    def end_of_interaction(self):
        # Call this method at the end of an interaction to reset the timer
        self.reset_last_interaction_time()

class StreamingManager:
    def __init__(self, thread_manager, eleven_labs_manager, assistant_id=None):
        self.thread_manager = thread_manager
        self.eleven_labs_manager = eleven_labs_manager
        self.assistant_id = assistant_id
        self.event_handler = None

    def set_event_handler(self, event_handler):
        if not self.event_handler:
            self.event_handler = event_handler
        else:
            print("Event handler is already set.")

    def ensure_event_handler_initialized(self):
        if not self.event_handler:
            print("Initializing event handler now.")
            self.event_handler = EventHandler()
        else:
            print("Event handler is already initialized.")

    def handle_streaming_interaction(self, content):
        self.ensure_event_handler_initialized()

        if not self.thread_manager.thread_id or not self.assistant_id:
            print("Thread ID or Assistant ID is not set.")
            return

        event_handler = self.event_handler if self.event_handler else EventHandler()
        self.thread_manager.add_message_to_thread(content)

        with openai.beta.threads.runs.create_and_stream(
            thread_id=self.thread_manager.thread_id,
            assistant_id=self.assistant_id,
        ) as stream:
            for event in stream:
                print("Event received:", event)
                if isinstance(event, ThreadRunRequiresAction):
                    self.event_handler.on_tool_call_created(event.data.required_action)
                elif isinstance(event, ThreadMessageDelta):
                    # No action needed for ThreadMessageDelta in this context
                    pass
                elif isinstance(event, ThreadRunCompleted):
                    print("\nInteraction completed.")
                    self.thread_manager.interaction_in_progress = False
                    self.thread_manager.end_of_interaction()
                    self.event_handler.on_run_completed(event.data.id, self.thread_manager.thread_id, self.assistant_id)
                    break
                elif isinstance(event, ThreadRunFailed):
                    print("\nInteraction failed.")
                    self.thread_manager.interaction_in_progress = False
                    self.thread_manager.end_of_interaction()
                    break  # Exit the loop if the interaction fails
                # Add more event types as needed based on your application's requirements
