"""
Chat Interface for User Interaction with Language Model Backend

This script defines a chat interface that interacts with a language model backend (Flask API)
to process user messages, manage user memory, and ensure responses fit within character limits.
Part of this is a migration from what I have used to make an LLM powered discord bot.

Status:
Incomplete memory management and output parsing. Memory DB still neds work.


"""
import requests
from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Optional

# Define the database model using SQLAlchemy
Base = declarative_base()

class ChatHistory(Base):
    __tablename__ = 'chat_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)
    message = Column(String, nullable=False)
    response = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc))

class ChatInterface:
    _instance = None
    _lock = Lock()

    def __new__(cls, server_url="http://localhost:5000", db_url="sqlite:///chat_history.db"):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance.server_url = server_url
                    cls._instance.db_url = db_url

                    # Set up SQLAlchemy database connection
                    cls._instance.engine = create_engine(db_url, echo=True)
                    Base.metadata.create_all(cls._instance.engine)  # Create the table if it doesn't exist
                    SessionLocal = sessionmaker(bind=cls._instance.engine)
                    cls._instance.session: Session = SessionLocal()

        return cls._instance

    def _send_request(self, endpoint, method="POST", data=None):
        """Helper method to send HTTP requests to the Flask server"""
        url = f"{self.server_url}{endpoint}"
        
        if method == "POST":
            response = requests.post(url, json=data)
            response.raise_for_status()  # Raises an exception for 4xx/5xx responses
        else:  # Default to GET for retrieving history should we go that route
            response = requests.get(url, params=data)
        
        return response.json()

    def process_message(self, user_id, message):
        """Process incoming chat messages and store the history"""
        # Prepare payload for sending to Flask server (changes coming)
        data = {'text': message}
        
        # Send the message to the Flask server (get response)
        flask_response = self._send_request('/chat', method="POST", data=data)
        
        # Save the chat message and response to the database
        self._save_to_db(user_id, message, flask_response.get('response', 'No response'))

        return flask_response.get('response', 'No response')

    def _save_to_db(self, user_id, message, response):
        """Save a new chat message and response to the database"""
        new_entry = ChatHistory(user_id=user_id, message=message, response=response)
        self.session.add(new_entry)
        self.session.commit()

    def erase_history(self, user_id, older_than_minutes: int = 10):
        """Erase chat history for a user in minutes"""
        threshold_time = datetime.now(timezone.utc) - timedelta(minutes=older_than_minutes)
        self.session.query(ChatHistory).filter(
            ChatHistory.user_id == user_id,
            ChatHistory.timestamp < threshold_time
        ).delete()
        self.session.commit()

    def clear_all_history(self):
        """Clear the entire chat history for test script purposes. Or delete the .db file"""
        self.session.query(ChatHistory).delete()
        self.session.commit()

    def close(self):
        """Close the SQLAlchemy session when done"""
        self.session.close()



# This is my first attempt at a singleton! I hope its stable for what I need
chat_interface = ChatInterface(server_url="http://localhost:5000", db_url="sqlite:///chat_history.db")

