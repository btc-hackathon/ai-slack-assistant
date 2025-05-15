import os

from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from .functions import query_llm

# Set Slack API credentials
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
SLACK_BOT_USER_ID = os.environ["SLACK_BOT_USER_ID"]

# Initialize the Slack app
app = App(token=SLACK_BOT_TOKEN)

# Initialize the Flask app
# Flask is a web application framework written in Python
flask_app = Flask(__name__)
handler = SlackRequestHandler(app)


def get_bot_user_id():
    """
    Get the bot user ID using the Slack API.

    Returns:
        str: The bot user ID, or None if an error occurs.
    """
    try:
        # Initialize the Slack client with your bot token
        slack_client = WebClient(token=SLACK_BOT_TOKEN) # Use the constant
        response = slack_client.auth_test()
        return response["user_id"]
    except SlackApiError as e:
        print(f"Error fetching bot user ID: {e}")
        return None


@app.event("app_mention")
def handle_mentions(body, say):
    """
    Event listener for mentions in Slack.
    When the bot is mentioned, this function processes the text and sends a response.

    Args:
        body (dict): The event data received from Slack.
        say (callable): A function for sending a response to the channel.
    """
    event = body["event"]
    channel_id = event["channel"]
    # Get thread_ts; fallback to message ts if not in a thread
    thread_ts = event.get("thread_ts", event["ts"])

    # Fetch all messages from the thread
    thread_messages = get_thread_messages(channel_id, thread_ts)

    if not thread_messages:
        say(text="Sorry, I couldn't retrieve the thread messages.", thread_ts=thread_ts)
        return

    # Combine the messages into a single string
    slack_thread_content = []
    bot_mention_string = f"<@{SLACK_BOT_USER_ID}>"
    for msg in thread_messages:
        user = msg.get("user", "Unknown User")
        text = msg.get("text", "")
        # Remove bot mention and strip whitespace
        cleaned_text = text.replace(bot_mention_string, "").strip()
        if cleaned_text: # Only add if there's actual content after stripping mention
            slack_thread_content.append(f"{user}: {cleaned_text}")

    full_thread_text = "\n".join(slack_thread_content)

    # Pass the entire thread to the query_llm function
    if full_thread_text:
        response_text = query_llm(full_thread_text)
    else:
        response_text = "It looks like there's no text in this thread for me to process after removing mentions."

    # Send the response back to Slack
    say(text=response_text, thread_ts=thread_ts)


def get_thread_messages(channel_id, thread_ts):
    """
    Retrieves the full Slack thread messages.

    Args:
        channel_id (str): The ID of the Slack channel.
        thread_ts (str): The timestamp of the original thread message.

    Returns:
        list: A list of message dictionaries from the thread, or an empty list on error.
    """
    try:
        # Initialize the Slack client with your bot token
        slack_client = WebClient(token=SLACK_BOT_TOKEN) # Use the constant
        # Call the conversations.replies API method to get thread replies
        response = slack_client.conversations_replies(
            channel=channel_id,
            ts=thread_ts  # The timestamp of the thread's parent message
        )
        # Extract the messages from the response
        messages = response.get("messages", [])
        return messages
    except SlackApiError as e:
        print(f"Error reading thread: {e.response.get('error', str(e))}")
        return []


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """
    Route for handling Slack events.
    This function passes the incoming HTTP request to the SlackRequestHandler for processing.

    Returns:
        Response: The result of handling the request.
    """
    return handler.handle(request)