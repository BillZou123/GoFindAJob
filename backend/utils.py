import uuid
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from backend.resume_analyze_agent.agent import root_agent

load_dotenv()

# Create a session service to store state
session_service = InMemorySessionService()


def call_agent(user_id: str, prompt: str, user_context: dict = None) -> str:
    """
    Call the root agent with the given prompt and user context.
    
    Args:
        user_id: Unique identifier for the user
        prompt: The prompt/message to send to the agent
        user_context: Optional dictionary with user context (name, preferences, etc.)
    
    Returns:
        str: The agent's final response text
    """
    if user_context is None:
        user_context = {}
    
    APP_NAME = "GoFindAJob"
    SESSION_ID = str(uuid.uuid4())
    
    # Create a new session with user context
    stateful_session = session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=SESSION_ID,
        state=user_context,
    )
    
    # Create runner with the agent
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    
    # Create message and send to agent
    new_message = types.Content(
        role="user", parts=[types.Part(text=prompt)]
    )
    
    # Run agent and get final response
    for event in runner.run(
        user_id=user_id,
        session_id=SESSION_ID,
        new_message=new_message,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                return event.content.parts[0].text
    
    return ""
