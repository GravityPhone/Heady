import openai
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
    def __init__(self, client, thread_id=None, assistant_id=None):
        self.client = client
        self.thread_id = thread_id
        self.assistant_id = assistant_id
        self.event_handler = None  # Initialize event_handler attribute

    def set_event_handler(self, event_handler):
        self.event_handler = event_handler

    def create_thread(self):
        try:
            thread = self.client.beta.threads.create()
            self.thread_id = thread.id  # Update the thread_id attribute
            return thread.id
        except Exception as e:
            print(f"Failed to create a thread: {e}")
            return None

    def handle_streaming_interaction(self, instructions: str):
        if not self.thread_id or not self.assistant_id:
            print("Thread ID or Assistant ID is not set.")
            return

        event_handler = self.event_handler if self.event_handler else EventHandler()  # Use set event handler if available

        with self.client.beta.threads.runs.create_and_stream(
            thread_id=self.thread_id,
            assistant_id=self.assistant_id,
            instructions=instructions,
        ) as stream:
            for event in stream:
                print("Event received:", event)  # Debug print to confirm events are received
                # Now, instead of passing, you handle each event with your event handler
                if isinstance(event, ThreadMessageDelta):
                    event_handler.on_text_delta(event.data.delta, None)  # Adjusted to include 'None' for the missing 'snapshot' argument and correctly access delta
                elif isinstance(event, ThreadRunRequiresAction):
                    event_handler.on_tool_call_created(event.tool_call)
                elif isinstance(event, ThreadRunCompleted):
                    print("\nInteraction completed.")
                    break  # Exit the loop once the interaction is complete
                elif isinstance(event, ThreadRunFailed):
                    print("\nInteraction failed.")
                    break  # Exit the loop if the interaction fails
                # Add more event types as needed based on your application's requirements
