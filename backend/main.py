from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os
import shutil
import json
import asyncio
import sys
from typing import List, Dict, Any, Optional
import fitz # PyMuPDF
import pickle
from pathlib import Path

# Actual imports for your redaction and entity logic
from redactor import redact_text, unredact_text, clean_text, apply_stored_redactions, deanonymize_using_db
from utils import find_entities

app = FastAPI()

# Allow CORS for frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RedactRequest(BaseModel):
    text: str
    entities: dict
    custom_entities: list = []  # For manual selection redaction

class SummarizeRequest(BaseModel):
    text: str
    model: str = None  # Optional model name from AVAILABLE_MODELS

class DeanonymizeRequest(BaseModel):
    text: str

# New model for follow-up requests
class FollowUpRequest(BaseModel):
    history: List[Dict[str, str]]  # List of {"role": "user"/"assistant", "content": ...}
    question: str
    model: str = "gpt-4o" # Default model if not specified

class ProcessTextRequest(BaseModel):
    text: str

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Save uploaded file temporarily
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    extracted_text = ""
    try:
        if file.filename.lower().endswith('.pdf'):
            doc = fitz.open(temp_path)
            for page in doc:
                extracted_text += page.get_text()
            doc.close()
            extracted_text = clean_text(extracted_text) # Apply cleaning to PDF text
        elif file.filename.lower().endswith('.txt'):
            with open(temp_path, 'r', encoding='utf-8') as f:
                extracted_text = clean_text(f.read())
        else:
            return JSONResponse(status_code=400, content={"error": "Unsupported file type. Please upload a .txt or .pdf file."})

        # Apply stored redactions BEFORE sending back to frontend
        processed_text = apply_stored_redactions(extracted_text)

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        # Ensure temp file is removed even if apply_stored_redactions fails
        if os.path.exists(temp_path):
             os.remove(temp_path)
    return {"filename": file.filename, "text": processed_text}

@app.post("/process-text")
async def process_text_input(data: ProcessTextRequest):
    try:
        # Basic cleaning and then apply stored redactions
        cleaned = clean_text(data.text)
        processed_text = apply_stored_redactions(cleaned)
        return {"text": processed_text}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/entities")
async def extract_entities(data: SummarizeRequest):
    try:
        entities = find_entities(data.text, language='en')
        # Convert sets to lists for JSON serialization
        entities = {k: list(v) for k, v in entities.items()}
        return {"entities": entities}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/redact")
async def redact(data: RedactRequest):
    try:
        print("=== DEBUG: custom_entities ===")
        for ce in data.custom_entities:
            print("Selected:", repr(ce))
        print("=== DEBUG: text excerpt ===")
        print(repr(data.text[:1000]))  # print first 1000 chars for context
        # Merge selected entities and custom_entities into a single redaction target
        merged_entities = dict(data.entities)
        if data.custom_entities:
            # Add a special label for manual selections
            merged_entities.setdefault('MANUAL', [])
            merged_entities['MANUAL'].extend(data.custom_entities)
        # Redact entities in text
        redacted, redaction_map = redact_text(data.text, merged_entities)
        # TODO: Store redaction_map in DB
        return {"redacted_text": redacted, "redaction_map": redaction_map}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

import openai
import google.generativeai as genai

AVAILABLE_MODELS = {
    "GPT-4o": "gpt-4o",
    "GPT-4.1 Mini (2025-04-14)": "gpt-4.1-mini-2025-04-14",
    "GPT-4.5 Preview": "gpt-4.5-preview-2025-02-27",
    "GPT-4.1 (2025-04-14)": "gpt-4.1-2025-04-14",
    "GPT-4.1 Nano (2025-04-14)": "gpt-4.1-nano-2025-04-14",
    "Gemini 2.5 Pro": "gemini-2.5-pro",
    "Gemini 2.5 Flash": "gemini-2.5-flash"
}

# API Key Storage
API_KEYS_FILE = Path("api_keys.pkl")

# Initialize API keys storage
def load_api_keys():
    """Load API keys from persistent storage"""
    if API_KEYS_FILE.exists():
        try:
            with open(API_KEYS_FILE, 'rb') as f:
                return pickle.load(f)
        except:
            return {}
    return {}

def save_api_keys(keys):
    """Save API keys to persistent storage"""
    with open(API_KEYS_FILE, 'wb') as f:
        pickle.dump(keys, f)

# Load API keys on startup
api_keys_store = load_api_keys()

class APIKeysRequest(BaseModel):
    openai_key: Optional[str] = None
    gemini_key: Optional[str] = None

class APIKeysResponse(BaseModel):
    openai_configured: bool
    gemini_configured: bool

@app.post("/summarize")
async def summarize(data: SummarizeRequest):
    api_key = api_keys_store.get('openai_key')
    # It's good practice to ensure API keys are present, especially if switching between providers
    # For Gemini, the key is configured globally or per client instance typically.

    model_key = data.model or "GPT-4o" # Default to GPT-4o if not specified
    model_id = AVAILABLE_MODELS.get(model_key, model_key)

    prompt = f"""
    You are an AI assistant specialized in summarizing documents and text content.
    Your primary goal is to extract **all critical information** from the content while providing a clear, comprehensive summary.
    
    **CORE TASK:** Analyze and summarize the following document content clearly, concisely, and **completely**.
    
    **DOCUMENT CONTENT:**
    {data.text}
    
    **ANALYSIS INSTRUCTIONS:**
    1. Read through the **entire document** carefully to understand the main themes and key information.
    2. Identify the most important concepts, facts, conclusions, and insights.
    3. Focus on substantive content and ignore formatting artifacts, headers, footers, or irrelevant metadata.
    4. Capture the document's purpose, main arguments, and key findings.
    5. Note any conclusions, recommendations, or action items mentioned.
    
    **REQUIRED SUMMARY OUTPUT:**
    Provide a comprehensive summary structured as follows:
    
    1.  **TLDR:** A single sentence that captures the main point or purpose of the document.
    2.  **Key Information & Main Points:** Bullet points covering the most important topics, concepts, data points, arguments, or findings discussed in the document.
    3.  **Supporting Details:** Mention important supporting information, examples, or context that helps understand the main points. If none are significant, state "None".
    4.  **Conclusions & Recommendations:** List any conclusions drawn, recommendations made, or solutions proposed in the document. If none, state "None".
    5.  **Action Items & Next Steps:** List any specific actions, next steps, or deadlines mentioned in the document. If none, state "None".
    """
    try:
        summary = ""
        if "gpt" in model_id.lower():
            if not api_key:
                return JSONResponse(status_code=500, content={"error": "OpenAI API key not set in backend/main.py."})
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=512,
                temperature=0.2
            )
            summary = response.choices[0].message.content.strip()
        elif "gemini" in model_id.lower():
            gemini_api_key = api_keys_store.get('gemini_key')
            if not gemini_api_key:
                return JSONResponse(status_code=500, content={"error": "Gemini API key not set or is a placeholder in backend/main.py."})
            genai.configure(api_key=gemini_api_key) # Ensure configured
            gemini_model = genai.GenerativeModel(model_id)
            response = await gemini_model.generate_content_async(prompt) # Use async for FastAPI
            summary = response.text
        else:
            return JSONResponse(status_code=400, content={"error": f"Unsupported model: {model_id}"})
        
        return {"summary": summary, "model": model_id}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# Streaming endpoint for summarization
@app.post("/summarize-stream")
async def summarize_stream(data: SummarizeRequest):
    async def generate():
        try:
            openai_api_key = api_keys_store.get('openai_key')
            model_key = data.model or "GPT-4o"
            model_id = AVAILABLE_MODELS.get(model_key, model_key)
            prompt = f"""
            You are an AI assistant specialized in summarizing documents and text content.
            Your primary goal is to extract **all critical information** from the content while providing a clear, comprehensive summary.
            
            **CORE TASK:** Analyze and summarize the following document content clearly, concisely, and **completely**.
            
            **DOCUMENT CONTENT:**
            {data.text}
            
            **ANALYSIS INSTRUCTIONS:**
            1. Read through the **entire document** carefully to understand the main themes and key information.
            2. Identify the most important concepts, facts, conclusions, and insights.
            3. Focus on substantive content and ignore formatting artifacts, headers, footers, or irrelevant metadata.
            4. Capture the document's purpose, main arguments, and key findings.
            5. Note any conclusions, recommendations, or action items mentioned.
            
            **REQUIRED SUMMARY OUTPUT:**
            Provide a comprehensive summary structured as follows:
            
            1.  **TLDR:** A single sentence that captures the main point or purpose of the document.
            2.  **Key Information & Main Points:** Bullet points covering the most important topics, concepts, data points, arguments, or findings discussed in the document.
            3.  **Supporting Details:** Mention important supporting information, examples, or context that helps understand the main points. If none are significant, state "None".
            4.  **Conclusions & Recommendations:** List any conclusions drawn, recommendations made, or solutions proposed in the document. If none, state "None".
            5.  **Action Items & Next Steps:** List any specific actions, next steps, or deadlines mentioned in the document. If none, state "None".
            """
            
            if "gpt" in model_id.lower():
                if not openai_api_key:
                    yield f"data: {json.dumps({'error': 'OpenAI API key not provided'})}\n\n"
                    return
                    
                client = openai.OpenAI(api_key=openai_api_key)
                stream = client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2048,
                    temperature=0.2,
                    stream=True
                )
                
                full_response = ""
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield f"data: {json.dumps({'chunk': content})}\n\n"
                        
                yield f"data: {json.dumps({'done': True, 'summary': full_response, 'model': model_id})}\n\n"
                
            elif "gemini" in model_id.lower():
                # Send immediate "thinking" indicator
                yield f"data: {json.dumps({'status': 'thinking', 'message': 'AI is processing your request...'})}\n\n"
                sys.stdout.flush()
                
                gemini_api_key = api_keys_store.get('gemini_key')
            if not gemini_api_key:
                    yield f"data: {json.dumps({'error': 'Gemini API key not provided'})}\n\n"
                    return
                
                gemini_api_key = api_keys_store.get('gemini_key')
                genai.configure(api_key=gemini_api_key)
                
                try:
                    # Use simple original configuration without custom settings
                    gemini_model = genai.GenerativeModel(model_id)
                    
                    # Send another status update
                    yield f"data: {json.dumps({'status': 'generating', 'message': 'Generating response...'})}\n\n"
                    sys.stdout.flush()
                    
                    # Gemini supports streaming!
                    response = gemini_model.generate_content(prompt, stream=True)
                    full_response = ""
                    chunk_count = 0
                    
                    for chunk in response:
                        chunk_count += 1
                        try:
                            if chunk.text:
                                full_response += chunk.text
                                yield f"data: {json.dumps({'chunk': chunk.text})}\n\n"
                                sys.stdout.flush()
                                await asyncio.sleep(0)
                            else:
                                continue
                        except ValueError as e:
                            # Handle safety filter blocks and other chunk access errors
                            if "finish_reason" in str(e):
                                print(f"[GEMINI] Chunk #{chunk_count} blocked by safety filter: {e}")
                                continue
                            else:
                                print(f"[GEMINI] Error accessing chunk #{chunk_count}: {e}")
                                raise e
                    
                    yield f"data: {json.dumps({'done': True, 'summary': full_response, 'model': model_id})}\n\n"
                    
                except Exception as gemini_error:
                    print(f"[GEMINI] ERROR during content generation: {type(gemini_error).__name__}: {str(gemini_error)}")
                    yield f"data: {json.dumps({'error': f'Gemini API error: {str(gemini_error)}'})}\n\n"
                    return
                
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    response = StreamingResponse(generate(), media_type="text/event-stream")
    # Add headers to prevent buffering and ensure immediate streaming
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
    return response

# New endpoint for follow-up questions
@app.post("/followup")
async def followup(data: FollowUpRequest):
    openai_api_key = api_keys_store.get('openai_key')

    # Get the actual model name
    model_id = AVAILABLE_MODELS.get(data.model, data.model) # Use data.model which contains the friendly name from frontend

    try:
        assistant_response = ""
        if "gpt" in model_id.lower():
            if not openai_api_key:
                return JSONResponse(status_code=500, content={"error": "OpenAI API key not set in backend/main.py."})
            client = openai.OpenAI(api_key=openai_api_key)
            # Add the new user question to the history for GPT
            messages = data.history + [{"role": "user", "content": data.question}]
            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                max_tokens=4096,
                temperature=0.2
            )
            assistant_response = response.choices[0].message.content.strip()
        elif "gemini" in model_id.lower():
            gemini_api_key = api_keys_store.get('gemini_key')
            if not gemini_api_key:
                return JSONResponse(status_code=500, content={"error": "Gemini API key not set or is a placeholder in backend/main.py."})
            gemini_api_key = api_keys_store.get('gemini_key')
            genai.configure(api_key=gemini_api_key)
            gemini_model = genai.GenerativeModel(model_id)
            
            # Construct prompt for Gemini from history
            # Gemini's `generate_content` often takes a flat string or specific Content parts.
            # For chat-like interactions, you might use `start_chat` and `send_message` if using the ChatSession.
            # Here, we'll adapt the OpenAI history to a flat string for `generate_content`.
            chat_prompt_parts = []
            if data.history:
                for message in data.history:
                    if message['role'] == 'user':
                        chat_prompt_parts.append(f"User: {message['content']}")
                    elif message['role'] == 'assistant':
                        chat_prompt_parts.append(f"Assistant: {message['content']}")
            chat_prompt_parts.append(f"User: {data.question}")
            full_prompt = "\n".join(chat_prompt_parts)

            response = await gemini_model.generate_content_async(full_prompt) # Use async
            assistant_response = response.text
        else:
            return JSONResponse(status_code=400, content={"error": f"Unsupported model: {model_id}"})

        return {"answer": assistant_response, "model": model_id}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# Streaming endpoint for follow-up questions
@app.post("/followup-stream")
async def followup_stream(data: FollowUpRequest):
    async def generate():
        try:
            openai_api_key = api_keys_store.get('openai_key')
            model_key = data.model or "GPT-4o"
            model_id = AVAILABLE_MODELS.get(model_key, model_key)
            
            if "gpt" in model_id.lower():
                if not openai_api_key:
                    yield f"data: {json.dumps({'error': 'OpenAI API key not provided'})}\n\n"
                    return
                    
                client = openai.OpenAI(api_key=openai_api_key)
                
                # Build messages from history
                messages = []
                if data.history:
                    for message in data.history:
                        messages.append({"role": message['role'], "content": message['content']})
                messages.append({"role": "user", "content": data.question})
                
                stream = client.chat.completions.create(
                    model=model_id,
                    messages=messages,
                    max_tokens=4096,
                    temperature=0.2,
                    stream=True
                )
                
                full_response = ""
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield f"data: {json.dumps({'chunk': content})}\n\n"
                        
                yield f"data: {json.dumps({'done': True, 'answer': full_response, 'model': model_id})}\n\n"
                
            elif "gemini" in model_id.lower():
                # Send immediate "thinking" indicator
                yield f"data: {json.dumps({'status': 'thinking', 'message': 'AI is analyzing your question...'})}\n\n"
                sys.stdout.flush()
                
                gemini_api_key = api_keys_store.get('gemini_key')
            if not gemini_api_key:
                    yield f"data: {json.dumps({'error': 'Gemini API key not provided'})}\n\n"
                    return
                
                gemini_api_key = api_keys_store.get('gemini_key')
                genai.configure(api_key=gemini_api_key)
                
                try:
                    # Use simple original configuration without custom settings
                    gemini_model = genai.GenerativeModel(model_id)
                    
                    # Construct prompt from history
                    chat_prompt_parts = []
                    if data.history:
                        for message in data.history:
                            if message['role'] == 'user':
                                chat_prompt_parts.append(f"User: {message['content']}")
                            elif message['role'] == 'assistant':
                                chat_prompt_parts.append(f"Assistant: {message['content']}")
                    chat_prompt_parts.append(f"User: {data.question}")
                    full_prompt = "\n".join(chat_prompt_parts)
                    
                    # Send another status update
                    yield f"data: {json.dumps({'status': 'generating', 'message': 'Generating answer...'})}\n\n"
                    sys.stdout.flush()
                    
                    # Use streaming for Gemini
                    response = gemini_model.generate_content(full_prompt, stream=True)
                    full_response = ""
                    chunk_count = 0
                    
                    for chunk in response:
                        chunk_count += 1
                        try:
                            if chunk.text:
                                full_response += chunk.text
                                yield f"data: {json.dumps({'chunk': chunk.text})}\n\n"
                                sys.stdout.flush()
                                await asyncio.sleep(0)
                            else:
                                continue
                        except ValueError as e:
                            # Handle safety filter blocks and other chunk access errors
                            if "finish_reason" in str(e):
                                print(f"[GEMINI FOLLOWUP-STREAM] Chunk #{chunk_count} blocked by safety filter: {e}")
                                continue
                            else:
                                print(f"[GEMINI FOLLOWUP-STREAM] Error accessing chunk #{chunk_count}: {e}")
                                raise e
                    
                    yield f"data: {json.dumps({'done': True, 'answer': full_response, 'model': model_id})}\n\n"
                    
                except Exception as gemini_error:
                    print(f"[GEMINI FOLLOWUP-STREAM] ERROR during content generation: {type(gemini_error).__name__}: {str(gemini_error)}")
                    yield f"data: {json.dumps({'error': f'Gemini API error: {str(gemini_error)}'})}\n\n"
                    return
                
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    response = StreamingResponse(generate(), media_type="text/event-stream")
    # Add headers to prevent buffering and ensure immediate streaming
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
    return response

@app.post("/deanonymize")
async def deanonymize(data: DeanonymizeRequest):
    try:
        # Use the new function that queries the DB directly
        deanonymized = deanonymize_using_db(data.text)
        return {"text": deanonymized}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# API Key Management Endpoints
@app.post("/api/configure-keys")
async def configure_api_keys(data: APIKeysRequest):
    """Configure API keys for OpenAI and Gemini"""
    global api_keys_store
    
    if data.openai_key:
        api_keys_store['openai_key'] = data.openai_key
    if data.gemini_key:
        api_keys_store['gemini_key'] = data.gemini_key
    
    # Save to persistent storage
    save_api_keys(api_keys_store)
    
    return APIKeysResponse(
        openai_configured=bool(api_keys_store.get('openai_key')),
        gemini_configured=bool(api_keys_store.get('gemini_key'))
    )

@app.get("/api/check-keys")
async def check_api_keys():
    """Check if API keys are configured"""
    return APIKeysResponse(
        openai_configured=bool(api_keys_store.get('openai_key')),
        gemini_configured=bool(api_keys_store.get('gemini_key'))
    )

@app.delete("/api/clear-keys")
async def clear_api_keys():
    """Clear all API keys"""
    global api_keys_store
    api_keys_store = {}
    save_api_keys(api_keys_store)
    
    # Remove the file if it exists
    if API_KEYS_FILE.exists():
        API_KEYS_FILE.unlink()
    
    return {"message": "API keys cleared successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
