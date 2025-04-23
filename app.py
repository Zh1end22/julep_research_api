from flask import Flask, request, jsonify
from julep import Julep
from dotenv import load_dotenv
import os
import time
import logging

# -------------------------------
# Environment Setup
# -------------------------------

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv("JULEP_API_KEY")
ENVIRONMENT = os.getenv("JULEP_ENVIRONMENT", "production")

if not API_KEY:
    raise EnvironmentError("Missing JULEP_API_KEY in .env file.")

# Initialize logging
logging.basicConfig(level=logging.INFO)

# -------------------------------
# Julep Client & Agent Setup
# -------------------------------

try:
    client = Julep(api_key=API_KEY, environment=ENVIRONMENT)

    # Create the agent
    agent = client.agents.create(
        name="Research Assistant",
        model="claude-3.5-haiku",
        about="An AI assistant that performs topic research in requested formats."
    )
    AGENT_ID = agent.id
    logging.info(f"[INFO] Agent created with ID: {AGENT_ID}")

except Exception as e:
    logging.error(f"[ERROR] Failed to initialize Julep client or create agent: {e}")
    raise RuntimeError("Failed to initialize Julep. Check your API key and internet connection.") from e

# -------------------------------
# Flask App Setup
# -------------------------------

app = Flask(__name__)

@app.route("/research", methods=["POST"])
def research():
    try:
        # Input validation
        data = request.get_json(force=True)
        topic = data.get("topic")
        format_type = data.get("format")

        if not topic or not format_type:
            return jsonify({"error": "Missing 'topic' or 'format' in request body."}), 400

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

        # Wait until task is done
        while (result := client.executions.get(execution.id)).status not in ['succeeded', 'failed']:
            logging.info(f"[INFO] Waiting for execution (ID: {execution.id}) - Status: {result.status}")
            time.sleep(1)

        # Return the output or error
        if result.status == "succeeded":
            message = result.output["choices"][0]["message"]["content"]
            return jsonify({"result": message}), 200
        else:
            logging.error(f"[ERROR] Execution failed: {result.error}")
            return jsonify({"error": "Task failed", "details": result.error}), 500

    except KeyError as e:
        return jsonify({"error": f"Missing key in response: {str(e)}"}), 500
    except Exception as e:
        logging.exception("[ERROR] Unexpected error occurred during /research")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

# -------------------------------
# Start the App
# -------------------------------

if __name__ == "__main__":
    app.run(debug=True)
