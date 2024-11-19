"""
Chat Interface for User Interaction with Language Model Backend

This script defines a chat interface that interacts with a language model backend (Flask API)
to process user messages, manage user memory, and ensure responses fit within character limits.
Part of this is a migration from what I have used to make an LLM powered discord bot.

Status:
Incomplete memory management and output parsing

Constants:
- MAX_DISCORD_LENGTH: The maximum allowed character length for messages (2000 characters).
- SUMMARY_PROMPT: The prompt used for summarizing responses that exceed the character limit.

"""
import logging
import requests
from datetime import datetime, timedelta
from langchain.memory import ConversationBufferMemory

# Constants
MAX_DISCORD_LENGTH = 2000
SUMMARY_PROMPT = "Please summarize the following text in the briefest way possible while retaining the key details."

# Memory storage for chat histories
# TODO: Migrate to a better storage solution
user_memory = {}

logging.basicConfig(level=logging.INFO) # tweak this as needed. 

class ChatInterface:
    def __init__(self, flask_url="http://localhost:5000/chat"):
        self.flask_url = flask_url

    def get_user_memory(self, user_id):
        """Retrieve or create memory for a user."""
        if user_id not in user_memory:
            # Initialize memory for the user using ConversationBufferMemory
            # if they are not present
            user_memory[user_id] = {
                "memory": ConversationBufferMemory(),
                "last_activity": datetime.now()
            }
        return user_memory[user_id]["memory"]

    def purge_inactive_users(self, hours_inactive=1):
        """Purges users who have been inactive for the specified number of hours."""
        now = datetime.now()
        for user_id in list(user_memory.keys()):
            if (now - user_memory[user_id]["last_activity"]) > timedelta(hours=hours_inactive):
                logging.info(f"Purging chat history for user: {user_id}")
                del user_memory[user_id]

    def process_message(self, user_id, message):
        logging.info(f"Processing message for user {user_id}: {message}")

        # Retrieve or create user memory
        memory = self.get_user_memory(user_id)
        
        # Add the current message to the memory buffer
        try:
            memory.save_context({"input": message}, {"output": message})
            logging.debug("Context successfully saved to memory.")
        except ValueError as e:
            logging.error(f"Error saving context: {e}")
            return "Failed to save context due to an input error."

        # Generate context from the memory
        try:
            context = memory.load_memory_variables({})["history"]
            logging.debug(f"Loaded context: {context}")
        except Exception as e:
            logging.error(f"Error loading memory variables: {e}")
            return "Failed to load memory variables."

        # Send the context to the LLM backend to generate a response
        response = self.get_response_from_llm(context)

        # Ensure the response fits within the Discord character limit
        final_reply = self.ensure_character_limit(response)
        logging.debug(f"Final reply after character limit check: {final_reply}")

        # Final safety check for length before sending to Discord
        if len(final_reply) > MAX_DISCORD_LENGTH:
            logging.warning("Response is still over the character limit even after summarization. Truncating response.")
            final_reply = final_reply[:MAX_DISCORD_LENGTH]

        # Update memory with the response
        try:
            memory.save_context({"input": final_reply}, {"output": final_reply})
            logging.debug("Reply successfully saved to memory.")
        except ValueError as e:
            logging.error(f"Error saving reply context: {e}")

        # Update last activity timestamp
        user_memory[user_id]["last_activity"] = datetime.now()

        return final_reply

    def get_response_from_llm(self, context):
        """Send context to the Flask API to get a response from the LLM."""
        payload = {"text": context}
        try:
            response = requests.post(self.flask_url, json=payload)
            response.raise_for_status()

            # Ensure the response is in JSON format
            response_data = response.json()
            if isinstance(response_data, dict):
                return response_data.get("response", "Could not process your request.")
            else:
                logging.error("Error: Response data is not a dictionary.")
                return "Invalid response format from LLM."
        except requests.RequestException as e:
            logging.error(f"Error communicating with backend: {e}")
            return "There was an error processing your request."

    def ensure_character_limit(self, reply):
        """Ensure the reply fits within the character limit, and summarize if needed."""
        if len(reply) > MAX_DISCORD_LENGTH:
            logging.info("Response exceeds max character limit, attempting to summarize.")
            summary_payload = {"text": SUMMARY_PROMPT + "\n" + reply}
            try:
                summary_response = requests.post(self.flask_url, json=summary_payload)
                summary_response.raise_for_status()
                summary_data = summary_response.json()
                if isinstance(summary_data, dict):
                    summary_reply = summary_data.get("response", "Could not summarize the request.")
                    logging.debug(f"Summary response: {summary_reply}")
                    return summary_reply if len(summary_reply) <= MAX_DISCORD_LENGTH else summary_reply[:MAX_DISCORD_LENGTH]
                else:
                    logging.error("Error: Summary response is not a dictionary.")
                    return reply[:MAX_DISCORD_LENGTH]
            except requests.RequestException as e:
                logging.error(f"Error summarizing response: {e}")
            return reply[:MAX_DISCORD_LENGTH]
        return reply

# Initialize the chat interface instance
chat_interface = ChatInterface()
