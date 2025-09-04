# Talk to Documents

A web application that allows users to interact with and process documents using AI-powered tools. The application features document redaction capabilities and AI-based document analysis.

## Features

- Document upload and processing
- AI-powered document analysis using OpenAI and Google Gemini
- PDF processing capabilities
- Document redaction functionality
- Web-based user interface

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

## API Documentation

Once the backend is running, you can access the FastAPI documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
Talk to documents/
├── backend/
│   ├── main.py          # FastAPI application entry point
│   ├── redactor.py      # Document redaction logic
│   ├── utils.py         # Utility functions
│   ├── requirements.txt # Python dependencies
│   └── redactions.db    # SQLite database
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

## Environment Variables

To use the AI features, you'll need to set up API keys:

- **OpenAI API Key**: Set as environment variable `OPENAI_API_KEY`
- **Google Gemini API Key**: Configure as needed in the application

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