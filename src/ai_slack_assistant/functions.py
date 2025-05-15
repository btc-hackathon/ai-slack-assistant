"""
This module provides functions for interacting with the Llama Stack client,
including agent creation, response handling, and querying the LLM.
"""

from dotenv import find_dotenv, load_dotenv
from llama_stack_client import Agent, LlamaStackClient
from llama_stack_client.types.shared_params.agent_config import ToolConfig
from llama_stack_client.types.toolgroup_register_params import McpEndpoint

# Load environment variables from .env file if present
load_dotenv(find_dotenv())


def create_agent(client: LlamaStackClient, model: str) -> Agent:
    """
    Creates and configures an agent with the LlamaStackClient.

    Args:
        client: The LlamaStackClient instance.
        model: The model identifier to be used by the agent.

    Returns:
        An initialized Agent instance.
    """
    tool_endpoints = [
        {"id": "mcp::jira_helper", "uri": "http://localhost:8000/sse"},
        {"id": "mcp::linkedin", "uri": "http://localhost:3004/sse"},
        {"id": "mcp::workday", "uri": "http://localhost:3005/sse"},
    ]

    for tool in tool_endpoints:
        client.toolgroups.register(
            toolgroup_id=tool["id"],
            provider_id="model-context-protocol",
            mcp_endpoint=McpEndpoint(uri=tool["uri"]),
        )

    instruction = (
        "You are an intelligent assistant working with Slack threads that may include "
        "prior discussions and context."
    )

    agent_config = ToolConfig(tool_choice="auto")
    agent_tools = [tool["id"] for tool in tool_endpoints]

    return Agent(
        client,
        model=model,
        instructions=instruction,
        enable_session_persistence=False,
        tool_config=agent_config,
        tools=agent_tools,
    )


def handle_responses(agent: Agent, session_id: str, user_prompts: list[str]) -> str:
    """
    Sends prompts to the agent and collects its responses.

    Args:
        agent: The Agent instance to interact with.
        session_id: The session ID for the conversation.
        user_prompts: A list of user prompts (strings) to send to the agent.

    Returns:
        A single string combining all agent responses, separated by newlines.
    """
    responses_content = []

    for prompt in user_prompts:
        response = agent.create_turn(
            messages=[{"role": "user", "content": prompt}],
            session_id=session_id,
            stream=False,  # Assuming non-streaming for simplicity here
        )
        if response.output_message and response.output_message.content:
            responses_content.append(response.output_message.content)
        else:
            responses_content.append(
                "[Agent did not provide a content response for this turn]"
            )

    return "\n".join(responses_content)


def query_llm(slack_thread: str) -> str:
    """
    Queries the LLM with the given Slack thread content.

    Initializes a LlamaStackClient, selects a model, creates an agent,
    processes the Slack thread as a prompt, and returns the LLM's response.

    Args:
        slack_thread: A string containing the content of the Slack thread.

    Returns:
        The response string from the LLM.
    """
    client = LlamaStackClient(base_url="http://localhost:8321")

    try:
        models = client.models.list()
        if not models:
            return "Error: No models available from LlamaStackClient."
        # Ensure there's at least one LLM model
        llm_model = next((m for m in models if m.model_type == "llm"), None)
        if not llm_model:
            return "Error: No LLM type model found."
        model_id = llm_model.identifier
    except Exception as e:
        # Handle potential errors during client instantiation or model listing
        return f"Error initializing client or fetching models: {e}"

    agent = create_agent(client, model_id)

    prompt_text = f"""Given Slack threads may include prior discussions and context.
    Your job is to understand the user’s intent from the latest message.
    If a tool call is needed, execute it immediately and wait for the result.
    Do not ask for confirmation before or after the tool call.
    Explain your actions in natural language.
    
    Slack Thread:
    {slack_thread}
    """
    user_prompts = [prompt_text]

    try:
        session_id = agent.create_session(
            session_name="slack-bot-session"
        )  # Added session_name
        response = handle_responses(agent, session_id, user_prompts)
    except Exception as e:
        return f"Error during agent interaction: {e}"

    return response
