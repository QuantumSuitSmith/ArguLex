# ArguLex - Legal Assistant

A professional web-based legal assistant that combines general legal knowledge with advanced PDF document analysis capabilities. The system provides a modern, user-friendly interface with dark mode support and secure authentication.

## Features

### 1. Web Interface
- **Modern UI/UX**
  - Responsive design for all devices
  - Dark mode support
  - Smooth animations
  - User-friendly forms

- **Authentication System**
  - Secure user registration
  - Login functionality
  - Session management
  - Protected routes

### 2. PDF Document Analysis
- **Case Report Generation**
  - Extracts case name, date, and judges
  - Generates comprehensive case summary
  - Identifies key conclusions
  - Creates downloadable reports

- **Document Querying**
  - Answers specific questions about uploaded documents
  - Provides context-aware responses
  - Quotes relevant sections from the document
  - Maintains accuracy and relevance

### 3. Chatbot System
- **Professional Chatbot**
  - Specialized in legal document analysis
  - Handles complex legal queries
  - Provides detailed explanations
  - Maintains professional tone

- **General Chatbot**
  - Answers general legal questions
  - Provides legal information and guidance
  - Maintains professional tone
  - Suggests professional consultation when needed

- **Conversation Management**
  - Maintains chat history
  - Provides well-structured responses
  - Handles multiple topics
  - Professional formatting

## Technical Details

### Dependencies
```python
# Core Dependencies
flask>=2.0.0
openai>=1.0.0
langchain>=0.1.0
PyMuPDF (fitz)>=1.22.0
sentence-transformers>=2.2.0
nltk>=3.8.1
faiss-cpu>=1.7.4
pandas>=2.0.0
numpy>=1.24.0
python-dotenv>=1.0.0
pymongo>=4.0.0
```

### Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd [repository-name]
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
# Create a .env file with:
OPENAI_API_KEY=your_api_key_here
FLASK_SECRET_KEY=your_secret_key_here
MONGODB_URI=your_mongodb_uri_here
```

4. Run the application:
```bash
python app.py
```

### Deployment

The application can be deployed on multiple platforms:

1. **Render**
   - Uses `render.yaml` for configuration
   - Automatic deployments from Git
   - Environment variables management

2. **Heroku**
   - Uses `Procfile` for configuration
   - Easy deployment with Git push
   - Add-on support for MongoDB

### Usage

1. **Web Interface**
   - Visit `http://localhost:5000` in your browser
   - Create an account or log in
   - Choose between Professional or General chatbot
   - Start chatting or upload documents

2. **PDF Document Analysis**
   - Upload a PDF document
   - Get automatic analysis and summary
   - Ask specific questions about the document
   - Download comprehensive reports

3. **Chatbot Interaction**
   - Ask general legal questions
   - Get professional responses
   - Maintain conversation history
   - Switch between chatbots as needed

## Project Structure

```
ArguLex/
├── app.py                      # Main Flask application
├── config.py                   # Configuration settings
├── requirements.txt            # Python dependencies
├── render.yaml                 # Render deployment configuration
├── Procfile                    # Heroku deployment configuration
├── .gitignore                  # Git ignore rules
├── professional_chatbot.log    # Professional chatbot logs
├── app.log                    # Application logs
├── chat_manager.log           # Chat manager logs
│
├── templates/                  # HTML templates
│   ├── base.html              # Base template with common elements
│   ├── login.html             # Login page
│   ├── signup.html            # Registration page
│   ├── signin.html            # Sign in page
│   ├── intro.html             # Introduction page
│   ├── selection.html         # Chatbot selection page
│   ├── chat.html              # General chat interface
│   ├── professional_chat.html # Professional chat interface
│   ├── general_chat.html      # General chat interface
│   ├── document_chat.html     # Document analysis interface
│   └── about.html             # About page
│
├── chatbot/                    # Chatbot implementation
│   ├── __init__.py            # Package initialization
│   ├── chat_manager.py        # Chat management system
│   ├── professional_chatbot.py # Professional chatbot
│   ├── general_chatbot.py     # General chatbot
│   ├── chatbot_manager.py     # Chatbot management
│   └── chatbot.py             # Base chatbot implementation
│
├── static/                     # Static assets
│   ├── css/                   # Stylesheets
│   ├── js/                    # JavaScript files
│   └── images/                # Image assets
│
├── data/                       # Data storage directory
├── temp/                       # Temporary files directory
├── venv/                       # Python virtual environment
└── __pycache__/               # Python bytecode cache
```

## Key Components

### Web Application
- Flask-based web server
- MongoDB for data storage
- Session management
- Route protection
- Logging system

### Chatbot System
- Professional and General chatbots
- Document analysis capabilities
- Chat history management
- User session handling
- PDF processing and analysis

### User Interface
- Bootstrap-based responsive design
- Dark mode support
- Form validation
- Interactive elements
- Real-time chat interface

### Data Management
- MongoDB integration
- Session persistence
- Document storage
- Chat history tracking
- User data management

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for GPT models
- Flask for web framework
- Bootstrap for UI components
- MongoDB for data storage
- Render and Heroku for deployment support

## Support

For support, please open an issue in the repository or contact the maintainers. 