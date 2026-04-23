from google.genai.types import Content, Part
from google.adk.events import Event
from google.adk.runners import Runner

def process_agent_response(event: Event) -> str | None:

    final_response = None
    if event.is_final_response():
        if (
            event.content and
            event.content.parts and
            hasattr(event.content.parts[0], "text") and
            event.content.parts[0].text
        ):
            final_response = event.content.parts[0].text
    return final_response

async def call_agent_async(
    runner: Runner,
    user_id: str,
    session_id: str,
    query: str
) -> str | None:
    
    content = Content(role="user", parts=[Part(text=query)])
    final_response = None
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
        response = process_agent_response(event)
        if response is not None:
            final_response = response

    return final_response