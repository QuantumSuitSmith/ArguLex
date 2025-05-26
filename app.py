import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify, session, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from chatbot.professional_chatbot import ProfessionalChatbot
from chatbot.general_chatbot import GeneralChatbot
from chatbot.chat_manager import ChatManager
import PyPDF2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key')

# Initialize chatbots and chat manager
professional_bot = ProfessionalChatbot()
general_bot = GeneralChatbot()
chat_manager = ChatManager()

# Configure upload folder
UPLOAD_FOLDER = 'temp'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Authentication decorator
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.before_request
def before_request():
    """Initialize session if not exists."""
    if 'session_id' not in session:
        session_id = chat_manager.create_session(session.get('user_id', 'anonymous'))
        session['session_id'] = session_id
        logger.info(f"Created new session: {session_id}")

@app.after_request
def after_request(response):
    """Update session last active timestamp."""
    if 'session_id' in session:
        chat_manager.get_session(session['session_id'])
    return response

# Auth Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = chat_manager.authenticate_user(email, password)
        if user:
            session['user_id'] = str(user['_id'])
            flash('Successfully logged in!', 'success')
            return redirect(url_for('selection'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        if chat_manager.create_user(email, password, name):
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Email already exists.', 'error')
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    """End the current session and redirect to intro page."""
    try:
        if 'session_id' in session:
            chat_manager.end_session(session['session_id'])
        session.clear()
        flash('Successfully logged out!', 'success')
    except Exception as e:
        logger.error(f"Error in logout: {str(e)}")
        flash('Error during logout.', 'error')
    return redirect(url_for('index'))

# Main Routes
@app.route('/')
def index():
    """Render the intro page."""
    return render_template('intro.html')

@app.route('/about')
def about():
    """Render the about page."""
    return render_template('about.html')

@app.route('/selection')
@login_required
def selection():
    """Render the chatbot selection page."""
    return render_template('selection.html')

@app.route('/professional')
@login_required
def professional():
    """Render the professional chatbot interface."""
    return render_template('professional_chat.html')

@app.route('/general')
@login_required
def general():
    """Render the general chatbot interface."""
    return render_template('chat.html')

@app.route('/profile')
@login_required
def profile():
    """Render the user profile page."""
    try:
        # Get user data
        user = chat_manager.get_user(session['user_id'])
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('index'))

        # Get user's chat history
        chat_history = chat_manager.get_user_chat_history(session['user_id'])
        
        # Calculate total chats
        total_chats = len(chat_history) if chat_history else 0
        
        # Add additional user data
        user['chat_history'] = chat_history
        user['total_chats'] = total_chats
        
        return render_template('profile.html', user=user)
    except Exception as e:
        logger.error(f"Error in profile: {str(e)}")
        flash('Error loading profile', 'error')
        return redirect(url_for('index'))

# Chat routes
@app.route('/chat', methods=['GET', 'POST'])
def chat():
    """Handle chat interactions."""
    if request.method == 'POST':
        try:
            data = request.get_json()
            message = data.get('message', '')
            
            # Get session_id from session if not in request
            session_id = session.get('session_id')
            if not session_id:
                session_id = chat_manager.create_session(session.get('user_id', 'anonymous'))
                session['session_id'] = session_id
            
            if not message:
                return jsonify({'error': 'No message provided'}), 400
                
            # Get response from appropriate chatbot
            response = chat_manager.get_response(message)
            
            # Save the chat interaction
            success = chat_manager.save_chat(session_id, message, response)
            if not success:
                logger.error(f"Failed to save chat for session {session_id}")
            
            return jsonify({
                'response': response,
                'session_id': session_id
            })
            
        except Exception as e:
            logger.error(f"Error in chat: {str(e)}")
            return jsonify({'error': 'Could not get response. Please try again.'}), 500
            
    return render_template('chat.html')

@app.route('/professional-chat', methods=['GET', 'POST'])
def professional_chat():
    """Handle professional chat interactions."""
    if request.method == 'POST':
        try:
            data = request.get_json()
            message = data.get('message', '')
            session_id = data.get('session_id')
            query_type = data.get('type', 'legal')  # Default to legal queries
            
            if not message:
                return jsonify({'error': 'No message provided'}), 400
                
            # Get response based on query type
            if query_type == 'document':
                # Use document-specific response if a document is loaded
                if chat_manager.current_pdf_text:
                    response = chat_manager.professional_bot.query_pdf_after_report(message, chat_manager.current_pdf_text)
                else:
                    response = "Please upload a document first to ask questions about it."
            else:
                # Use general legal knowledge base
                response = chat_manager.professional_bot.get_response(message)
            
            # Save the chat interaction
            if session_id:
                chat_manager.save_chat(session_id, message, response, {'type': query_type})
            
            return jsonify({
                'response': response,
                'session_id': session_id
            })
            
        except Exception as e:
            logger.error(f"Error in professional chat: {str(e)}")
            return jsonify({'error': 'Could not get response. Please try again.'}), 500
            
    return render_template('professional_chat.html')

@app.route('/general-chat', methods=['GET', 'POST'])
def general_chat():
    """Handle general chat interactions."""
    if request.method == 'POST':
        try:
            data = request.get_json()
            message = data.get('message', '')
            session_id = data.get('session_id')
            
            if not message:
                return jsonify({'error': 'No message provided'}), 400
                
            # Get response from general chatbot
            response = chat_manager.general_bot.get_response(message)
            
            # Save the chat interaction
            if session_id:
                chat_manager.save_chat(session_id, message, response)
            
            return jsonify({
                'response': response,
                'session_id': session_id
            })
            
        except Exception as e:
            logger.error(f"Error in general chat: {str(e)}")
            return jsonify({'error': 'Could not get response. Please try again.'}), 500
            
    return render_template('general_chat.html')

# API Routes
@app.route('/api/upload', methods=['POST'])
def upload_document():
    """Handle document upload."""
    try:
        if 'document' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['document']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are allowed'}), 400

        # Get session_id from session
        session_id = session.get('session_id')
        if not session_id:
            session_id = chat_manager.create_session(session.get('user_id', 'anonymous'))
            session['session_id'] = session_id

        # Read the PDF file
        pdf_text = ""
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                pdf_text += page.extract_text() + "\n"
        except Exception as e:
            logger.error(f"Error reading PDF: {str(e)}")
            return jsonify({'error': 'Error reading PDF file'}), 400

        # Store the PDF text in the chat manager
        chat_manager.current_pdf_text = pdf_text
        
        # Save document to MongoDB
        metadata = {
            'filename': file.filename,
            'upload_date': datetime.utcnow(),
            'page_count': len(pdf_reader.pages)
        }
        
        success = chat_manager.save_document(session_id, file.filename, pdf_text, metadata)
        if not success:
            logger.error(f"Failed to save document {file.filename} for session {session_id}")
            return jsonify({'error': 'Failed to save document'}), 500
        
        # Generate initial analysis
        try:
            analysis = chat_manager.professional_bot.analyze_pdf(pdf_text)
            return jsonify({
                'success': True,
                'message': 'Document uploaded and analyzed successfully',
                'analysis': analysis,
                'session_id': session_id
            })
        except Exception as e:
            logger.error(f"Error analyzing PDF: {str(e)}")
            return jsonify({'error': 'Error analyzing document'}), 500

    except Exception as e:
        logger.error(f"Error in upload_document: {str(e)}")
        return jsonify({'error': 'Error processing document'}), 500

@app.route('/api/history', methods=['GET'])
@login_required
def get_history():
    """Get chat history for the current session."""
    try:
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({'error': 'No active session'}), 400

        # Get chat history
        chat_history = chat_manager.get_chat_history(session_id)
        
        # Get document history if available
        document_history = []
        if chat_manager.current_pdf_text:
            document_history = chat_manager.get_document_history(session_id)

        return jsonify({
            'success': True,
            'chat_history': chat_history,
            'document_history': document_history
        })
    except Exception as e:
        logger.error(f"Error getting history: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/save-history', methods=['POST'])
@login_required
def save_history():
    """Save chat history for the current session."""
    try:
        data = request.get_json()
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({'error': 'No active session'}), 400

        # Save chat history
        chat_manager.save_chat_history(session_id, data.get('history', []))
        
        # Save document history if available
        if data.get('document_history'):
            chat_manager.save_document_history(session_id, data.get('document_history'))

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error saving history: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.teardown_appcontext
def cleanup(exception=None):
    """Clean up resources."""
    try:
        chat_manager.cleanup_old_sessions()
    except Exception as e:
        logger.error(f"Error in cleanup: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True) 