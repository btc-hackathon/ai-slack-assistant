import os
from dotenv import find_dotenv, load_dotenv
from .app import flask_app

# Load environment variables from .env file
load_dotenv(find_dotenv())


def start_app():
    """Function to start the Flask application."""
    print("Starting AI Slack Assistant Flask app")
    port = int(os.environ.get("PORT", "8080"))
    flask_app.run(port=port)


if __name__ == "__main__":
    start_app()
