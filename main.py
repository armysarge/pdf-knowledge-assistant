#!/usr/bin/env python3
"""
PDF Knowledge Assistant - Main Application

This application processes PDFs and allows users to query information from them
using a local LLM.
"""

import typer
from typing import Optional, List
from pathlib import Path
import os

from src.pdf_processor import PDFProcessor
from src.knowledge_base import KnowledgeBase
from src.chat_interface import ChatInterface

app = typer.Typer()

@app.command()
def process_pdfs(
    pdf_dir: str = typer.Option("data/pdfs", help="Directory containing PDFs to process"),
    force_rebuild: bool = typer.Option(False, help="Force rebuild of knowledge base even if embeddings exist")
):
    """Process PDFs and build a knowledge base for querying"""
    processor = PDFProcessor()
    kb = KnowledgeBase()

    pdf_dir_path = Path(pdf_dir)
    if not pdf_dir_path.exists():
        typer.echo(f"Creating PDF directory at {pdf_dir}")
        pdf_dir_path.mkdir(parents=True, exist_ok=True)

    if not any(pdf_dir_path.glob('*.pdf')):
        typer.echo(f"No PDFs found in {pdf_dir}. Please add PDFs to this directory.")
        return

    typer.echo(f"Processing PDFs from {pdf_dir}...")
    documents = processor.process_directory(pdf_dir)
    typer.echo(f"Processed {len(documents)} documents")

    typer.echo("Building knowledge base...")
    kb.add_documents(documents, force_rebuild=force_rebuild)
    typer.echo("Knowledge base built successfully!")

@app.command()
def chat(
    model_path: Optional[str] = typer.Option(
        None,
        help="Path to local LLM model (will download from Hugging Face if not provided)"
    )
):
    """Start an interactive chat session with the knowledge base"""
    kb = KnowledgeBase()

    # Check if knowledge base exists
    if not kb.check_knowledge_base_exists():
        typer.echo("Knowledge base not found. Please process PDFs first using 'process-pdfs' command.")
        return

    chat_interface = ChatInterface(kb, model_path)
    chat_interface.start_interactive_chat()

@app.command()
def api_server(
    host: str = typer.Option("0.0.0.0", help="Host address to bind the API server"),
    port: int = typer.Option(8000, help="Port to bind the API server"),
    reload: bool = typer.Option(False, help="Enable auto-reload for development")
):
    """Start the REST API server"""
    import uvicorn
    typer.echo(f"Starting API server at http://{host}:{port}")
    typer.echo("Press CTRL+C to stop the server")
    uvicorn.run("src.api:app", host=host, port=port, reload=reload)

@app.callback()
def callback():
    """
    PDF Knowledge Assistant - Process PDFs and chat with a local AI about them
    """
    # Ensure directories exist
    os.makedirs("data/pdfs", exist_ok=True)
    os.makedirs("data/embeddings", exist_ok=True)

if __name__ == "__main__":
    app()
