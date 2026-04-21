import uuid
import logging
import asyncio
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from backend.resume_analyze_agent.agent import root_agent

load_dotenv()

logger = logging.getLogger(__name__)

# Create a session service to store state
session_service = InMemorySessionService()
logger.debug(f"Session service created: {session_service}")


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
    
    logger.info("=== CALL_AGENT START ===")
    logger.debug(f"User ID: {user_id}")
    logger.debug(f"Prompt length: {len(prompt)}")
    logger.debug(f"User context: {user_context}")
    
    APP_NAME = "GoFindAJob"
    SESSION_ID = str(uuid.uuid4())
    
    logger.debug(f"App name: {APP_NAME}")
    logger.debug(f"Session ID: {SESSION_ID}")
    logger.debug(f"Session service type: {type(session_service)}")
    
    # Create a new session with user context
    logger.info("Creating session...")
    try:
        # create_session is async, so we need to run it in an event loop
        async def create_session_async():
            return await session_service.create_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=SESSION_ID,
                state=user_context,
            )
        
        # Use asyncio.run to properly await the async function
        stateful_session = asyncio.run(create_session_async())
        logger.debug(f"Session created result type: {type(stateful_session)}")
        logger.debug(f"Session created result: {stateful_session}")
        logger.info("Session created successfully")
    except Exception as e:
        logger.error(f"Error creating session: {e}", exc_info=True)
        raise
    
    # Create runner with the agent
    logger.info("Creating runner...")
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    logger.debug(f"Runner created: {runner}")
    
    # Create message and send to agent
    new_message = types.Content(
        role="user", parts=[types.Part(text=prompt)]
    )
    logger.info(f"Running agent with session {SESSION_ID}...")
    
    # Run agent and get final response
    response_text = ""
    event_count = 0
    try:
        for event in runner.run(
            user_id=user_id,
            session_id=SESSION_ID,
            new_message=new_message,
        ):
            event_count += 1
            logger.debug(f"Event {event_count}: {type(event)} - {event}")
            if event.is_final_response():
                logger.debug(f"Got final response event")
                if event.content and event.content.parts:
                    response_text = event.content.parts[0].text
                    logger.info(f"Agent response: {response_text[:100]}...")
                    return response_text
        logger.warning(f"No final response received after {event_count} events")
    except Exception as e:
        logger.error(f"Error running agent: {e}", exc_info=True)
        raise
    
    logger.info("=== CALL_AGENT END ===")
    return response_text
