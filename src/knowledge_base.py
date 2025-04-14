"""
Knowledge Base module for storing and retrieving document embeddings
"""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

class KnowledgeBase:
    """Manages the vector database for document retrieval."""

    def __init__(self, embeddings_dir: str = "data/embeddings"):
        """
        Initialize the knowledge base with a path to the embeddings directory.

        Args:
            embeddings_dir: Directory to store embeddings
        """
        self.embeddings_dir = embeddings_dir
        self.embedding_model = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            cache_folder="data/embeddings/models"
        )
        self.vector_store = None

        # Try to load existing vector store
        self._load_vector_store()

    def _load_vector_store(self) -> bool:
        """
        Load the vector store from disk if it exists.

        Returns:
            Boolean indicating if the vector store was loaded
        """
        index_path = os.path.join(self.embeddings_dir, "faiss_index")
        if os.path.exists(index_path):
            try:
                self.vector_store = FAISS.load_local(
                    index_path,
                    self.embedding_model,
                    allow_dangerous_deserialization=True
                )
                return True
            except Exception as e:
                print(f"Error loading vector store from {index_path}: {e}")
                self.vector_store = None
                return False
        print(f"No vector store found at {index_path}")
        return False

    def check_knowledge_base_exists(self) -> bool:
        """
        Check if the knowledge base exists.

        Returns:
            Boolean indicating if the knowledge base exists
        """
        exists = self.vector_store is not None
        print(f"Knowledge base exists: {exists}")
        print(f"Vector store: {self.vector_store}")
        return exists

    def add_documents(self, documents: List[Dict[str, Any]], force_rebuild: bool = False) -> None:
        """
        Add documents to the knowledge base and save to disk.

        Args:
            documents: List of document chunks to add
            force_rebuild: Whether to rebuild the knowledge base from scratch
        """
        # If force rebuild is set or no existing vector store, create a new one
        if force_rebuild or self.vector_store is None:
            self.vector_store = FAISS.from_documents(documents, self.embedding_model)
        else:
            # Add documents to existing vector store
            self.vector_store.add_documents(documents)

        # Save to disk
        index_path = os.path.join(self.embeddings_dir, "faiss_index")
        os.makedirs(index_path, exist_ok=True)
        self.vector_store.save_local(index_path)

    def query(self, question: str, top_k: int = 4) -> List[str]:
        """
        Query the knowledge base to retrieve the most relevant document chunks.

        Args:
            question: The user question
            top_k: Number of relevant chunks to retrieve

        Returns:
            List of document chunks as strings
        """
        if self.vector_store is None:
            return []

        docs = self.vector_store.similarity_search(question, k=top_k)
        return [doc.page_content for doc in docs]
