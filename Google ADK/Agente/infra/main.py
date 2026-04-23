import asyncio

from MB3_Agent.utils import call_agent_async
from MB3_Agent.agent import app

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

session_service = InMemorySessionService()

async def main_async(user_input: str):

    APP_NAME = app.name
    USER_ID = "cliente_urbo"

    existing_sessions = await session_service.list_sessions(app_name=APP_NAME, user_id=USER_ID)

    if existing_sessions and len(existing_sessions.sessions) > 0:
        SESSION_ID = existing_sessions.sessions[-1].id
        print("Usamos la sesión más reciente: ", SESSION_ID, "\n\n")
    else:
        new_session = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID)
        SESSION_ID = new_session.id
        print("Creamos una nueva sesión: ", SESSION_ID, "\n\n")

    runner = Runner(app=app, session_service=session_service)

    response = await call_agent_async(runner, USER_ID, SESSION_ID, user_input)
    return response

if __name__ == "__main__":
    response = asyncio.run(main_async("Hola!"))
    print(response)