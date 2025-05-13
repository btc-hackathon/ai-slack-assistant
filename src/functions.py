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

    client.toolgroups.register(
        toolgroup_id="mcp::linkedin",
        provider_id="model-context-protocol",
        mcp_endpoint=McpEndpoint(uri="http://localhost:3004/sse"),
    )

    client.toolgroups.register(
        toolgroup_id="mcp::workday",
        provider_id="model-context-protocol",
        mcp_endpoint=McpEndpoint(uri="http://localhost:3005/sse"),
    )

    instruction = """You are an intelligent assistant working with Slack threads that may include prior discussions 
    and context."""

    return Agent(
        client,
        model=model,
        instructions=instruction,
        enable_session_persistence=False,
        tool_config=ToolConfig(
            tool_choice="auto",
        ),
        tools=["mcp::jira_helper", "mcp::linkedin", "mcp::workday"]
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
    client = LlamaStackClient(
        base_url=f"http://localhost:8321",
    )

    models = client.models.list()

    model_id = next(m for m in models if m.model_type == "llm").identifier

    agent = create_agent(client, model_id)

    user_prompts = [
        f"""        
        Given Slack threads may include prior discussions and context. 
        Your job is to understand the user’s intent from the latest message.
        and If a tool call is needed, execute it immediately and wait for the result.
        Do not ask for confirmation before or after the tool call.
        Explain your actions in natural language.
        
        Slack Thread: {slack_thread}
        """
    ]

    session_id = agent.create_session("slack-bot-session")

    response = handle_responses(agent, session_id, user_prompts)

    return response
