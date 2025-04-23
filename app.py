import os
import json
import logging
import time
from flask import Flask, request, jsonify
from julep import Julep
from dotenv import load_dotenv

# -------------------------------
# Environment Setup
# -------------------------------

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv("JULEP_API_KEY")
ENVIRONMENT = os.getenv("JULEP_ENVIRONMENT", "production")

if not API_KEY:
    raise EnvironmentError("Missing JULEP_API_KEY in environment variables.")

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------
# Julep Client & Agent Setup with Persistence
# -------------------------------

AGENT_FILE = "/tmp/agent_id.json"  # Use /tmp for Railway persistence across restarts

def load_agent_id():
    """Load the agent ID from a file if it exists."""
    try:
        if os.path.exists(AGENT_FILE):
            with open(AGENT_FILE, "r") as f:
                data = json.load(f)
                return data.get("agent_id")
    except Exception as e:
        logger.error(f"Failed to load agent ID from {AGENT_FILE}: {e}")
    return None

def save_agent_id(agent_id):
    """Save the agent ID to a file."""
    try:
        with open(AGENT_FILE, "w") as f:
            json.dump({"agent_id": agent_id}, f)
        logger.info(f"Saved agent ID to {AGENT_FILE}: {agent_id}")
    except Exception as e:
        logger.error(f"Failed to save agent ID to {AGENT_FILE}: {e}")
        raise

# Initialize Julep client and agent
try:
    client = Julep(api_key=API_KEY, environment=ENVIRONMENT)
    AGENT_ID = load_agent_id()

    if not AGENT_ID:
        # Create a new agent if none exists
        agent = client.agents.create(
            name="Research Assistant",
            model="claude-3.5-haiku",
            about="An AI assistant that performs topic research in requested formats."
        )
        AGENT_ID = agent.id
        save_agent_id(AGENT_ID)
        logger.info(f"Agent created with ID: {AGENT_ID}")
    else:
        logger.info(f"Using existing agent ID: {AGENT_ID}")

except Exception as e:
    logger.error(f"Failed to initialize Julep client or create agent: {e}")
    raise RuntimeError("Failed to initialize Julep. Check your API key and internet connection.") from e

# -------------------------------
# Flask App Setup
# -------------------------------

app = Flask(__name__)

@app.route("/research", methods=["POST"])
def research():
    """Handle research requests using the Julep agent."""
    try:
        # Input validation
        data = request.get_json(force=True)
        topic = data.get("topic")
        format_type = data.get("format")

        if not topic or not format_type:
            logger.warning("Missing 'topic' or 'format' in request body")
            return jsonify({"error": "Missing 'topic' or 'format' in request body."}), 400

        logger.info(f"Received research request - Topic: {topic}, Format: {format_type}")

        # Define task
        task_definition = {
            "name": "Research Task",
            "description": "Fetches topic info in a specific format.",
            "main": [
                {
                    "prompt": [
                        {"role": "system", "content": "You are a helpful research assistant."},
                        {"role": "user", "content": f"Please research '{topic}' and respond in '{format_type}' format."}
                    ]
                }
            ]
        }

        # Create and run the task
        task = client.tasks.create(agent_id=AGENT_ID, **task_definition)
        execution = client.executions.create(
            task_id=task.id,
            input={"topic": topic, "format": format_type}
        )

        # Poll until task is done (with timeout to avoid hanging)
        timeout = 60  # 60 seconds timeout
        start_time = time.time()
        while (result := client.executions.get(execution.id)).status not in ['succeeded', 'failed']:
            if time.time() - start_time > timeout:
                logger.error(f"Execution timeout for ID: {execution.id}")
                return jsonify({"error": "Task execution timed out"}), 504
            logger.info(f"Waiting for execution (ID: {execution.id}) - Status: {result.status}")
            time.sleep(1)

        # Return the output or error
        if result.status == "succeeded":
            message = result.output["choices"][0]["message"]["content"]
            logger.info(f"Execution succeeded for ID: {execution.id}")
            return jsonify({"result": message}), 200
        else:
            logger.error(f"Execution failed for ID: {execution.id}: {result.error}")
            return jsonify({"error": "Task failed", "details": result.error}), 500

    except KeyError as e:
        logger.error(f"Missing key in response: {e}")
        return jsonify({"error": f"Missing key in response: {str(e)}"}), 500
    except Exception as e:
        logger.exception("Unexpected error occurred during /research")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

# No app.run() block - Gunicorn will handle running the app in production
