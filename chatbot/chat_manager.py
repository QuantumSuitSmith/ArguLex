import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
from flask import session
from .professional_chatbot import ProfessionalChatbot
from .general_chatbot import GeneralChatbot
import random
import string
from werkzeug.security import check_password_hash, generate_password_hash

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chat_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ChatManager:
    def __init__(self):
        """Initialize ChatManager with MongoDB connection."""
        try:
            # Connect to MongoDB
            mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
            logger.info(f"Connecting to MongoDB at: {mongo_uri}")
            self.client = MongoClient(mongo_uri)
            self.db = self.client['argulex']  # Changed database name to argulex
            self.chats = self.db['chats']
            self.documents = self.db['documents']
            self.sessions = self.db['sessions']
            self.users = self.db['users']
            
            # Test the connection
            self.client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
            
            # Initialize chatbots
            self.general_bot = GeneralChatbot()
            self.professional_bot = ProfessionalChatbot()
            
            # Initialize context variables
            self.current_pdf_text = None
            self.current_report = None
            self.current_report_path = None
            
            # Drop existing unique index on user_id if it exists
            try:
                self.sessions.drop_index('user_id_1')
            except Exception as e:
                logger.warning(f"Could not drop existing index: {str(e)}")
            
            # Create indexes
            self.chats.create_index([('session_id', 1), ('timestamp', -1)])
            self.documents.create_index([('session_id', 1), ('filename', 1)])
            self.sessions.create_index([('session_id', 1)], unique=True)
            self.sessions.create_index([('user_id', 1)])
            self.users.create_index([('email', 1)], unique=True)
            
            logger.info("ChatManager initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing ChatManager: {str(e)}")
            raise

    def create_session(self, user_id: str) -> str:
        """Create a new session for a user."""
        try:
            # Ensure user_id is not None
            if not user_id:
                user_id = 'anonymous'
            
            # Create a unique session ID using timestamp and random string
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            session_id = f"{timestamp}_{random_str}"
            
            session = {
                'session_id': session_id,
                'user_id': user_id,
                'created_at': datetime.utcnow(),
                'last_active': datetime.utcnow(),
                'is_active': True
            }
            
            # Insert the session document
            result = self.sessions.insert_one(session)
            
            logger.info(f"Created new session {session_id} for user {user_id}")
            return session_id
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            raise

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session information."""
        try:
            session = self.sessions.find_one({'session_id': session_id})
            if session:
                # Update last active timestamp
                self.sessions.update_one(
                    {'session_id': session_id},
                    {'$set': {'last_active': datetime.utcnow()}}
                )
            return session
        except Exception as e:
            logger.error(f"Error getting session: {str(e)}")
            return None

    def end_session(self, session_id: str) -> bool:
        """End a session."""
        try:
            result = self.sessions.update_one(
                {'session_id': session_id},
                {'$set': {'is_active': False, 'ended_at': datetime.utcnow()}}
            )
            success = result.modified_count > 0
            if success:
                logger.info(f"Ended session {session_id}")
            return success
        except Exception as e:
            logger.error(f"Error ending session: {str(e)}")
            return False

    def save_chat(self, session_id: str, message: str, response: str, context: Optional[Dict] = None) -> bool:
        """Save a chat interaction."""
        try:
            chat = {
                'session_id': session_id,
                'message': message,
                'response': response,
                'context': context or {},
                'timestamp': datetime.utcnow()
            }
            result = self.chats.insert_one(chat)
            
            # Update session history
            session = self.sessions.find_one({'session_id': session_id})
            if session:
                history = session.get('chat_history', [])
                history.append(chat)
                self.sessions.update_one(
                    {'session_id': session_id},
                    {'$set': {'chat_history': history}}
                )
            
            success = result.inserted_id is not None
            if success:
                logger.info(f"Saved chat for session {session_id}")
            return success
        except Exception as e:
            logger.error(f"Error saving chat: {str(e)}")
            return False

    def get_chat_history(self, session_id: str) -> List[Dict]:
        """Get chat history for a session."""
        try:
            session = self.sessions.find_one({'session_id': session_id})
            return session.get('chat_history', []) if session else []
        except Exception as e:
            logger.error(f"Error getting chat history: {str(e)}")
            return []

    def save_document(self, session_id: str, filename: str, content: str, metadata: Optional[Dict] = None) -> bool:
        """Save a document and its metadata."""
        try:
            document = {
                'session_id': session_id,
                'filename': filename,
                'content': content,
                'metadata': metadata or {},
                'created_at': datetime.utcnow()
            }
            result = self.documents.insert_one(document)
            success = result.inserted_id is not None
            if success:
                logger.info(f"Saved document {filename} for session {session_id}")
            return success
        except Exception as e:
            logger.error(f"Error saving document: {str(e)}")
            return False

    def get_document(self, session_id: str, filename: str) -> Optional[Dict]:
        """Get a document and its metadata."""
        try:
            document = self.documents.find_one({
                'session_id': session_id,
                'filename': filename
            })
            if document:
                document['_id'] = str(document['_id'])
            return document
        except Exception as e:
            logger.error(f"Error getting document: {str(e)}")
            return None

    def cleanup_old_sessions(self, days: int = 7) -> int:
        """Clean up old sessions and their associated data."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Find old sessions
            old_sessions = self.sessions.find({
                'last_active': {'$lt': cutoff_date},
                'is_active': True
            })
            
            count = 0
            for session in old_sessions:
                session_id = session['_id']
                
                # Delete associated chats
                self.chats.delete_many({'session_id': session_id})
                
                # Delete associated documents
                self.documents.delete_many({'session_id': session_id})
                
                # Mark session as inactive
                self.sessions.update_one(
                    {'_id': session_id},
                    {'$set': {'is_active': False, 'ended_at': datetime.utcnow()}}
                )
                
                count += 1
            
            logger.info(f"Cleaned up {count} old sessions")
            return count
        except Exception as e:
            logger.error(f"Error cleaning up old sessions: {str(e)}")
            return 0

    def close(self):
        """Close MongoDB connection."""
        try:
            self.client.close()
            logger.info("MongoDB connection closed")
        except Exception as e:
            logger.error(f"Error closing MongoDB connection: {str(e)}")

    def handle_upload(self, file):
        """Handle document upload and analysis"""
        try:
            if not file or not file.filename:
                return "❌ No file uploaded", None, None

            if not file.filename.lower().endswith('.pdf'):
                return "❌ Only PDF files are supported", None, None

            # Generate report using professional chatbot
            report, report_path, full_text = self.professional_bot.handle_upload(file)
            
            # Check for errors in report generation
            if report.startswith("❌ Error"):
                return report, None, None
            
            # Store the results
            self.current_pdf_text = full_text
            self.current_report = report
            self.current_report_path = report_path
            
            return report, "success", full_text

        except Exception as e:
            print(f"Error in handle_upload: {str(e)}")
            return f"❌ Error processing document: {str(e)}", None, None

    def get_response(self, message):
        """Get a response from the appropriate chatbot"""
        try:
            # If we have a PDF loaded, use the professional chatbot
            if self.current_pdf_text:
                response = self.professional_bot.query_pdf_after_report(message, self.current_pdf_text)
                return response

            # Otherwise use the general chatbot
            response = self.general_bot.get_response(message)
            return response

        except Exception as e:
            print(f"Error in get_response: {str(e)}")
            return f"❌ Error: {str(e)}"

    def clear_context(self):
        """Clear the current context"""
        self.current_pdf_text = None
        self.current_report = None
        self.current_report_path = None
        if self.current_report_path and os.path.exists(self.current_report_path):
            try:
                os.remove(self.current_report_path)
            except:
                pass

    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate a user with email and password."""
        try:
            user = self.users.find_one({'email': email})
            if user and check_password_hash(user['password'], password):
                return user
            return None
        except Exception as e:
            logger.error(f"Error authenticating user: {str(e)}")
            return None

    def create_user(self, email: str, password: str, name: str) -> bool:
        """Create a new user."""
        try:
            # Check if user already exists
            if self.users.find_one({'email': email}):
                return False
            
            # Create new user
            user = {
                'email': email,
                'password': generate_password_hash(password),
                'name': name,
                'created_at': datetime.utcnow()
            }
            
            result = self.users.insert_one(user)
            return result.inserted_id is not None
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return False

    def get_user(self, user_id: str) -> Dict:
        """Get user data with additional information."""
        try:
            user = self.users.find_one({'_id': ObjectId(user_id)})
            if not user:
                return None
                
            # Convert ObjectId to string
            user['_id'] = str(user['_id'])
            
            # Add created_at if not present
            if 'created_at' not in user:
                user['created_at'] = datetime.utcnow()
            
            # Get chat history
            user['chat_history'] = self.get_user_chat_history(user_id)
            
            # Calculate total chats
            user['total_chats'] = len(user['chat_history'])
            
            return user
        except Exception as e:
            logger.error(f"Error getting user: {str(e)}")
            return None

    def save_chat_history(self, session_id: str, history: List[Dict]) -> bool:
        """Save chat history for a session."""
        try:
            # Update existing history or create new
            self.sessions.update_one(
                {'session_id': session_id},
                {'$set': {'chat_history': history}}
            )
            logger.info(f"Saved chat history for session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving chat history: {str(e)}")
            return False

    def save_document_history(self, session_id: str, document_history: List[Dict]) -> bool:
        """Save document analysis history for a session."""
        try:
            # Update existing history or create new
            self.sessions.update_one(
                {'session_id': session_id},
                {'$set': {'document_history': document_history}}
            )
            logger.info(f"Saved document history for session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving document history: {str(e)}")
            return False

    def get_document_history(self, session_id: str) -> List[Dict]:
        """Get document analysis history for a session."""
        try:
            session = self.sessions.find_one({'session_id': session_id})
            return session.get('document_history', []) if session else []
        except Exception as e:
            logger.error(f"Error getting document history: {str(e)}")
            return [] 