from dotenv import find_dotenv, load_dotenv
from llama_stack_client import Agent, LlamaStackClient
from llama_stack_client.types.shared_params.agent_config import ToolConfig
from llama_stack_client.types.toolgroup_register_params import McpEndpoint

load_dotenv(find_dotenv())


def create_agent(client: LlamaStackClient, model: str) -> Agent:
    """Creates and returns an agent with the given client and model."""

    client.toolgroups.register(
        toolgroup_id="mcp::jira_helper",
        provider_id="model-context-protocol",
        mcp_endpoint=McpEndpoint(uri="http://localhost:8000/sse"),
    )

    instruction = """
    You are Jarvis, an AI assistant integrated into Slack. You help users interact with Jira through natural conversation.

    You receive full Slack threads, which may include prior discussions, context, and references to Jira tickets. Your job is to:
    1. Analyze the thread for the Jira ticket being discussed (e.g., ticket ID like "PROJ-123").
    2. Understand the user’s intent from the latest message.
    3. **Immediately take action by calling the appropriate tool with the required parameters. Do not ask for confirmation before acting.**

    Guidelines:
    - Only call tools when you’re sufficiently confident in both the Jira ticket and the user’s intent.
    - If information is clearly missing or ambiguous, ask a clarifying question.
    - Your tone should be helpful, concise, and aligned with Slack's informal style.

    Only respond in natural language when appropriate. If a tool call is needed, execute it directly without waiting for confirmation.
    """

    return Agent(
        client,
        model=model,
        instructions=instruction,
        enable_session_persistence=False,
        tool_config=ToolConfig(
            tool_choice="required",
            tool_prompt_format="python_list",
        ),
        tools=["mcp::jira_helper"]
    )


def handle_responses(agent: Agent, session_id: str, user_prompts: list[str]) -> str:
    """Handles the responses from the agent for the given user prompts and returns the combined response string."""
    responses = []

    for prompt in user_prompts:
        response = agent.create_turn(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            session_id=session_id,
            stream=False,
        )

        responses.append(response.output_message.content)

    return "\n".join(responses)


def query_llm(slack_thread):
    client = LlamaStackClient(base_url="http://localhost:8321")

    models = client.models.list()

    model_id = next(m for m in models if m.model_type == "llm").identifier

    agent = create_agent(client, model_id)
    user_prompts = [
        f"Only respond in natural language when appropriate. If a tool call is needed, execute it directly without "
        f"waiting for confirmation. Slack thread:\n{slack_thread}\n\nUser's input:"
    ]

    session_id = agent.create_session("Jira-session")

    response = handle_responses(agent, session_id, user_prompts)

    return response
