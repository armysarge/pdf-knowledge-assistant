"""
API module for the PDF Knowledge Assistant
"""

import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio

from src.pdf_processor import PDFProcessor
from src.knowledge_base import KnowledgeBase
from src.chat_interface import ChatInterface

# Initialize FastAPI app
app = FastAPI(title="PDF Knowledge Assistant API")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    """Serve the main HTML page"""
    return FileResponse("static/index.html")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize knowledge base and chat interface
kb = KnowledgeBase()
chat_interface = None

def initialize_chat_interface():
    """Initialize the chat interface if knowledge base exists"""
    global chat_interface
    if kb.check_knowledge_base_exists():
        chat_interface = ChatInterface(kb)
        return True
    return False

# Try to initialize chat interface
initialize_chat_interface()

# Request and response models
class QueryRequest(BaseModel):
    message: str

class ProcessPDFRequest(BaseModel):
    force_rebuild: bool = False

async def stream_chat_response(message: str):
    """Generate streaming response from chat interface"""
    try:
        answer, sources = chat_interface.get_response(message)

        # Stream the response word by word
        for word in answer.split():
            yield f"data: {word} \n\n"
            await asyncio.sleep(0.05)  # Add small delay between words

        # Send sources as the final message
        if sources:
            yield f"data: \n\nSources: {', '.join(sources)}\n\n"

        yield "data: [DONE]\n\n"
    except Exception as e:
        error_msg = str(e)
        yield f"data: Error: {error_msg}\n\n"
        yield "data: [DONE]\n\n"

@app.post("/api/chat-stream")
async def chat_stream(query: QueryRequest):
    """Stream a response from the chat interface"""
    if not chat_interface or not kb.check_knowledge_base_exists():
        return StreamingResponse(
            iter([f"data: Knowledge base not initialized. Please process PDFs first by adding PDFs to the data/pdfs directory and calling the /process-pdfs endpoint.\n\ndata: [DONE]\n\n"]),
            media_type="text/event-stream"
        )

    return StreamingResponse(
        stream_chat_response(query.message),
        media_type="text/event-stream"
    )

@app.get("/status")
async def get_status():
    """Check if the knowledge base is ready"""
    is_ready = kb.check_knowledge_base_exists()
    return {
        "status": "ready" if is_ready else "not_ready",
        "message": "Knowledge base is ready for queries" if is_ready else "Please process PDFs first"
    }

@app.post("/process-pdfs")
async def process_pdfs(request: ProcessPDFRequest, background_tasks: BackgroundTasks):
    """Process PDFs in the background"""
    global chat_interface
    processor = PDFProcessor()
    pdf_dir = "data/pdfs"

    # Create PDF directory if it doesn't exist
    os.makedirs(pdf_dir, exist_ok=True)

    if not any(Path(pdf_dir).glob('*.pdf')):
        raise HTTPException(
            status_code=400,
            detail=f"No PDFs found in {pdf_dir}. Please add PDFs to this directory."
        )

    # Process PDFs and build knowledge base
    documents = processor.process_directory(pdf_dir)
    kb.add_documents(documents, force_rebuild=request.force_rebuild)

    # Initialize chat interface after processing
    chat_interface = ChatInterface(kb)

    # Verify initialization was successful
    if not chat_interface or not kb.check_knowledge_base_exists():
        raise HTTPException(
            status_code=500,
            detail="Failed to initialize chat interface after processing PDFs."
        )

    return {"status": "success", "message": f"Processed {len(documents)} documents"}
