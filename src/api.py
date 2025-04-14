"""
API module for the PDF Knowledge Assistant
"""

import os
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from src.pdf_processor import PDFProcessor
from src.knowledge_base import KnowledgeBase
from src.chat_interface import ChatInterface

# Initialize FastAPI app
app = FastAPI(title="PDF Knowledge Assistant API")

# Mount static files
static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize knowledge base
kb = KnowledgeBase()
chat_interface = None

# Request and response models
class QueryRequest(BaseModel):
    query: str

class ProcessPDFRequest(BaseModel):
    force_rebuild: bool = False

class QueryResponse(BaseModel):
    answer: str
    sources: List[str] = []

class StatusResponse(BaseModel):
    status: str
    message: str

# Background processing task
def process_pdfs_task(force_rebuild: bool = False):
    pdf_dir = "data/pdfs"
    processor = PDFProcessor()

    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir, exist_ok=True)

    if not any(os.path.join(pdf_dir, f) for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')):
        return {"status": "error", "message": "No PDFs found in the data/pdfs directory"}

    documents = processor.process_directory(pdf_dir)
    kb.add_documents(documents, force_rebuild=force_rebuild)
    return {"status": "success", "message": f"Processed {len(documents)} documents"}

# Load the LLM on startup if knowledge base exists
@app.on_event("startup")
async def startup_event():
    global chat_interface
    if kb.check_knowledge_base_exists():
        chat_interface = ChatInterface(kb)

# API endpoints
@app.post("/process-pdfs", response_model=StatusResponse)
async def process_pdfs(request: ProcessPDFRequest, background_tasks: BackgroundTasks):
    """
    Process PDFs in the data/pdfs directory
    """
    # Check if PDFs exist
    pdf_dir = "data/pdfs"
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir, exist_ok=True)
        return {"status": "warning", "message": "PDF directory created. Please add PDFs to data/pdfs and try again."}

    if not any(f.lower().endswith('.pdf') for f in os.listdir(pdf_dir)):
        return {"status": "error", "message": "No PDFs found in the data/pdfs directory"}

    # Add the task to background processing
    background_tasks.add_task(process_pdfs_task, request.force_rebuild)

    return {
        "status": "processing",
        "message": "PDF processing started in the background. This may take some time."
    }

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Query the knowledge base with a question
    """
    global chat_interface

    # Check if knowledge base exists
    if not kb.check_knowledge_base_exists():
        raise HTTPException(
            status_code=400,
            detail="Knowledge base not initialized. Please process PDFs first using the /process-pdfs endpoint."
        )

    # Initialize chat interface if not already done
    if chat_interface is None:
        chat_interface = ChatInterface(kb)

    try:
        # Use the conversation chain to get a response
        result = chat_interface.chain({"question": request.query})

        # Extract sources
        source_docs = result.get("source_documents", [])
        sources = set()
        for doc in source_docs:
            if "source" in doc.metadata:
                sources.add(doc.metadata["source"])

        # Return the response
        return {
            "answer": result["answer"],
            "sources": list(sources)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.get("/status", response_model=StatusResponse)
async def status():
    """
    Get the status of the knowledge base
    """
    if kb.check_knowledge_base_exists():
        return {"status": "ready", "message": "Knowledge base is initialized and ready for queries"}
    else:
        return {"status": "not_ready", "message": "Knowledge base is not initialized. Please process PDFs first."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
