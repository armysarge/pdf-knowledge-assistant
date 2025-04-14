"""
PDF Processor module for extracting and processing text from PDF documents
"""

import os
from pathlib import Path
from typing import List, Dict, Any
from tqdm import tqdm

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

class PDFProcessor:
    """Handles the loading and processing of PDF documents."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the PDF processor with configurable chunk parameters.

        Args:
            chunk_size: The size of text chunks in characters
            chunk_overlap: The overlap between chunks in characters
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )

    def process_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Process a single PDF file and return a list of document chunks.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of document chunks with text and metadata
        """
        try:
            loader = PyPDFLoader(pdf_path)
            documents = loader.load()

            # Add source filename to metadata
            for doc in documents:
                doc.metadata["source"] = os.path.basename(pdf_path)

            # Split documents into chunks
            split_docs = self.text_splitter.split_documents(documents)

            return split_docs

        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
            return []

    def process_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """
        Process all PDF files in a directory.

        Args:
            directory_path: Path to directory containing PDFs

        Returns:
            List of all document chunks from all PDFs
        """
        pdf_files = list(Path(directory_path).glob("*.pdf"))
        all_documents = []

        for pdf_file in tqdm(pdf_files, desc="Processing PDFs"):
            documents = self.process_pdf(str(pdf_file))
            all_documents.extend(documents)

        return all_documents
