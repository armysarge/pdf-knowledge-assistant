"""
API module for the PDF Knowledge Assistant with true streaming support
"""

import os
import asyncio
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from src.pdf_processor import PDFProcessor
from src.knowledge_base import KnowledgeBase
from src.chat_interface import ChatInterface  # Import the updated ChatInterface

# Request models
class QueryRequest(BaseModel):
    message: str

class ProcessPDFRequest(BaseModel):
    force_rebuild: bool = False

# Initialize FastAPI app
app = FastAPI(title="PDF Knowledge Assistant API")

# Global variables
kb = None
chat_interface = None

@app.on_event("startup")
async def startup_event():
    """Initialize knowledge base and chat interface on startup"""
    global kb, chat_interface
    print("Starting PDF Knowledge Assistant API...")
    kb = KnowledgeBase()
    if kb.check_knowledge_base_exists():
        print("Knowledge base found, initializing chat interface...")
        chat_interface = ChatInterface(kb)
        print(f"Chat interface initialized: {chat_interface is not None}")
    else:
        print("No knowledge base found, waiting for /process-pdfs call")

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

async def stream_chat_response(message: str):
    """Generate true streaming response from chat interface"""
    try:
        # Track sources during streaming
        collected_sources = []

        # Use the new streaming response method
        async for token, sources in chat_interface.get_streaming_response(message):
            # Send each token as it's generated
            yield f"data: {token}\n\n"
            # Remember the sources
            if sources and not collected_sources:
                collected_sources = sources
            # Small delay to prevent overwhelming the client
            await asyncio.sleep(0.01)

        # Send sources in a standardized format as the last message before DONE
        if collected_sources:
            yield f"data: SOURCES:{', '.join(collected_sources)}\n\n"

        # Signal that the stream is complete
        yield "data: [DONE]\n\n"
    except Exception as e:
        error_msg = str(e)
        yield f"data: Error: {error_msg}\n\n"
        yield "data: [DONE]\n\n"

@app.post("/api/chat-stream")
async def chat_stream(query: QueryRequest):
    """Stream a response from the chat interface"""
    return await handle_chat_stream(query.message)

@app.get("/api/chat-stream")
async def chat_stream_get(message: str):
    """Stream a response from the chat interface (GET endpoint)"""
    return await handle_chat_stream(message)

async def handle_chat_stream(message: str):
    """Common handler for both POST and GET endpoints"""
    try:
        if not chat_interface:
            return StreamingResponse(
                iter([
                    "data: Knowledge base not initialized. Please process PDFs first by adding PDFs to the data/pdfs directory and calling the /process-pdfs endpoint.\n\n",
                    "data: [DONE]\n\n"
                ]),
                media_type="text/event-stream"
            )

        if not kb.check_knowledge_base_exists():
            return StreamingResponse(
                iter([
                    "data: Knowledge base not found. Please add PDFs to the data/pdfs directory and call the /process-pdfs endpoint.\n\n",
                    "data: [DONE]\n\n"
                ]),
                media_type="text/event-stream"
            )
        return StreamingResponse(
            stream_chat_response(message),
            media_type="text/event-stream"
        )
    except Exception as e:
        return StreamingResponse(
            iter([
                f"data: {str(e)}\n\n",
                "data: [DONE]\n\n"
            ]),
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

# Add a test streaming endpoint
@app.get("/test-stream")
async def test_stream():
    """Test SSE streaming with a simple counter"""
    async def generate():
        for i in range(20):
            yield f"data: Testing streaming message {i}\n\n"
            await asyncio.sleep(0.5)
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")