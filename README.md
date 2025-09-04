# Talk to Documents

A web application that allows users to interact with and process documents using AI-powered tools. The application features document redaction capabilities with database persistence and AI-based document analysis.

## Use Cases

- **Legal Document Processing**: Redact sensitive information from legal documents while maintaining consistency
- **GDPR Compliance**: Anonymize personal data in documents with reversible redaction
- **Document Intelligence**: Extract insights and summaries from lengthy documents
- **Data Privacy**: Process documents while protecting sensitive information
- **Research & Analysis**: Interactive Q&A with documents for research purposes

## Features

- **Document Upload & Processing**: Support for text files and PDF documents
- **AI-Powered Analysis**: 
  - Document summarization using OpenAI GPT models and Google Gemini
  - Interactive Q&A with documents
  - Multiple AI model support (GPT-4, GPT-4.5, Gemini 2.5, etc.)
- **PDF Processing**: Extract and analyze text from PDF documents using PyMuPDF
- **Advanced Redaction System**:
  - Intelligent entity detection and redaction
  - Custom entity redaction with selection
  - Persistent redaction tracking in SQLite database
  - Reversible anonymization/de-anonymization
- **Database Capabilities**:
  - SQLite database for storing redaction mappings
  - Persistent storage of redacted entities
  - Maintain consistency across document versions
  - Support for bulk redaction operations
- **Interactive Web Interface**: Modern React-based UI with Material Design

## Tech Stack

### Backend
- **FastAPI** - Python web framework
- **PyMuPDF** - PDF processing
- **OpenAI API** - AI document analysis
- **Google Gemini AI** - Alternative AI processing
- **SQLite** - Database for redaction records

### Frontend
- **React** - JavaScript framework
- **Material-UI** - Component library
- **Axios** - HTTP client

## Prerequisites

- Python 3.9+
- Node.js and npm
- Anaconda/Miniconda (for Python environment management)

## Installation

### Backend Setup

1. Create a conda environment:
```bash
conda create -n redactor-backend python=3.9
conda activate redactor-backend
```

2. Navigate to the backend directory:
```bash
cd backend/
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend/
```

2. Install Node dependencies:
```bash
npm install
```

## Running the Application

### Option 1: Use the provided startup script

```bash
./start_talk_to_documents.sh
```

This script will:
- Activate the conda environment for the backend
- Start the FastAPI backend server on port 8000
- Start the React frontend development server on port 3000

### Option 2: Manual startup

#### Backend
```bash
cd backend/
conda activate redactor-backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend (in a new terminal)
```bash
cd frontend/
npm start
```

## Database Features

The application includes a robust SQLite database system for managing document redactions:

### Redaction Database (`redactions.db`)
- **Entity Mapping**: Stores original text to redacted placeholder mappings
- **Persistent Storage**: Maintains redaction history across sessions
- **Batch Operations**: Supports bulk redaction and de-anonymization
- **Consistency**: Ensures same entities are redacted consistently throughout documents

### Key Database Operations
- `store_redaction()`: Save entity-redaction pairs to database
- `apply_stored_redactions()`: Apply saved redactions to new documents
- `deanonymize_using_db()`: Reverse redactions using stored mappings
- `clean_text()`: Remove artifacts and clean document text

## API Documentation

Once the backend is running, you can access the FastAPI documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Key API Endpoints
- `POST /upload`: Upload and process documents (PDF, TXT)
- `POST /redact`: Apply redactions to text with entity detection
- `POST /summarize`: Generate AI-powered document summaries
- `POST /followup`: Interactive Q&A with documents
- `POST /deanonymize`: Reverse redactions using database mappings
- `POST /api/configure-keys`: Configure API keys
- `GET /api/check-keys`: Check API key configuration status

## Project Structure

```
Talk to documents/
├── backend/
│   ├── main.py          # FastAPI application entry point
│   ├── redactor.py      # Document redaction logic & database operations
│   ├── utils.py         # Utility functions & entity detection
│   ├── requirements.txt # Python dependencies
│   ├── redactions.db    # SQLite database (auto-created)
│   └── api_keys.pkl     # Encrypted API keys storage (git-ignored)
├── frontend/
│   ├── src/
│   │   ├── App.js       # Main React component
│   │   ├── RedactorApp.js # Redactor interface
│   │   └── index.js     # React entry point
│   ├── public/
│   │   └── index.html
│   ├── package.json     # Node.js dependencies
│   └── package-lock.json
├── start_talk_to_documents.sh # Startup script
└── Talk to documents.app/     # macOS Automator application

```

## API Key Configuration

The application uses a secure API key management system:

1. **First-time Setup**: On first launch, you'll be prompted to configure API keys
2. **Access Settings**: Click the settings icon (⚙️) in the top-right corner
3. **Add Your Keys**: 
   - **OpenAI API Key**: Get from [OpenAI Platform](https://platform.openai.com/api-keys)
   - **Google Gemini API Key**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
4. **Secure Storage**: Keys are stored locally in `api_keys.pkl` (never committed to git)

Note: At least one API key (OpenAI or Gemini) is required for AI features to work.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues or questions, please open an issue in the GitHub repository.