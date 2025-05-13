import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bolt import App
from dotenv import find_dotenv, load_dotenv
from flask import Flask, request
from functions import query_llm

# Load environment variables from .env file
load_dotenv(find_dotenv())

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
        str: The bot user ID.
    """
    try:
        # Initialize the Slack client with your bot token
        slack_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
        response = slack_client.auth_test()
        return response["user_id"]
    except SlackApiError as e:
        print(f"Error: {e}")


def my_function(text):
    """
    Custom function to process the text and return a response.
    In this example, the function converts the input text to uppercase.

    Args:
        text (str): The input text to process.

    Returns:
        str: The processed text.
    """
    response = text.upper()
    return response


@app.event("app_mention")
def handle_mentions(body, say):
    """
    Event listener for mentions in Slack.
    When the bot is mentioned, this function processes the text and sends a response.

    Args:
        body (dict): The event data received from Slack.
        say (callable): A function for sending a response to the channel.
    """
    # text = body["event"]["text"]
    # mention = f"<@{SLACK_BOT_USER_ID}>"
    # text = text.replace(mention, "").strip()
    # response = query_llm(text)

    channel_id = body["event"]["channel"]
    thread_ts = body["event"].get("thread_ts",
                                  body["event"]["ts"])  # Get thread_ts, fallback to message ts if not in a thread
    # Fetch all messages from the thread
    thread_messages = get_thread_messages(channel_id, thread_ts)

    # Combine the messages into a single string (you can customize this format as needed)
    slack_thread = ""
    for msg in thread_messages:
        user = msg.get('user', 'Unknown User')
        text = msg.get('text', '')
        mention = f"<@{SLACK_BOT_USER_ID}>"
        cleaned_text = text.replace(mention, "").strip()
        slack_thread += f"{user}: {cleaned_text}\n"

    # Pass the entire thread to the query_llm function
    response = query_llm(slack_thread)

    # Send the response back to Slack (either in the thread or the channel)
    say(text=response, thread_ts=thread_ts)


def get_thread_messages(channel_id, thread_ts):
    """
    Retrieves the full Slack thread messages.

    Args:
        channel_id (str): The ID of the Slack channel.
        thread_ts (str): The timestamp of the original thread message.

    Returns:
        list: A list of message dictionaries from the thread.
    """
    try:
        # Initialize the Slack client with your bot token
        slack_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
        # Call the conversations.replies API method to get thread replies
        response = slack_client.conversations_replies(
            channel=channel_id,
            ts=thread_ts  # The timestamp of the thread's parent message
        )

        # Extract the messages from the response
        messages = response['messages']
        return messages

    except SlackApiError as e:
        print(f"Error reading thread: {e.response['error']}")
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


# Run the Flask app
if __name__ == "__main__":
    flask_app.run()
