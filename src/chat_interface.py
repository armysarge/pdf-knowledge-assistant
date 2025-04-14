"""
Chat interface module for interacting with the knowledge base using a local LLM
"""

import os
from typing import List, Optional
from rich.console import Console
from rich.markdown import Markdown
import sys

from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.chains import ConversationalRetrievalChain
from langchain.llms import LlamaCpp
from langchain.memory import ConversationBufferMemory
from huggingface_hub import hf_hub_download

from src.knowledge_base import KnowledgeBase

class ChatInterface:
    """Interface for chatting with the knowledge base using a local LLM."""

    def __init__(self, knowledge_base: KnowledgeBase, model_path: Optional[str] = None):
        """
        Initialize the chat interface with a knowledge base and optional model path.

        Args:
            knowledge_base: The knowledge base to query
            model_path: Optional path to local LLM model (downloads model if not provided)
        """
        self.knowledge_base = knowledge_base
        self.console = Console()

        self.model_path = self._get_model_path(model_path)
        self.llm = self._load_llm()

        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )

        self.chain = self._create_conversation_chain()

    def _get_model_path(self, model_path: Optional[str]) -> str:
        """
        Get the path to the LLM model, downloading it if needed.

        Args:
            model_path: Optional path to local model

        Returns:
            Path to the model file
        """
        if model_path and os.path.exists(model_path):
            return model_path

        # Default model if none provided
        model_name = "TheBloke/Mistral-7B-Instruct-v0.2-GGUF"
        model_filename = "mistral-7b-instruct-v0.2.Q8_K_M.gguf"

        # Path to save the model
        models_dir = os.path.join("data", "models")
        os.makedirs(models_dir, exist_ok=True)
        local_model_path = os.path.join(models_dir, model_filename)

        # Download the model if it doesn't exist
        if not os.path.exists(local_model_path):
            self.console.print(f"[yellow]Model not found locally. Downloading {model_name}...[/yellow]")
            local_model_path = hf_hub_download(
                repo_id=model_name,
                filename=model_filename,
                repo_type="model",
                cache_dir=models_dir
            )
            self.console.print("[green]Model downloaded successfully![/green]")

        return local_model_path

    def _load_llm(self):
        """
        Load the local LLM model.

        Returns:
            Loaded LLM instance
        """
        self.console.print("[yellow]Loading LLM model... This may take a minute...[/yellow]")

        callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])

        # Load the model with appropriate settings for a machine with 32GB RAM
        llm = LlamaCpp(
            model_path=self.model_path,
            temperature=0.1,
            max_tokens=2048,
            n_ctx=4096,
            top_p=0.95,
            callback_manager=callback_manager,
            verbose=False,
            n_gpu_layers=33,  # Use GPU if available
            n_batch=512,  # Adjust batch size for efficiency
            f16_kv=True  # Use half-precision for key/value cache
        )

        self.console.print("[green]LLM model loaded successfully![/green]")
        return llm

    def _create_conversation_chain(self):
        """
        Create a conversational chain with the LLM and knowledge base.

        Returns:
            ConversationalRetrievalChain instance
        """
        if not self.knowledge_base.check_knowledge_base_exists():
            return None

        retriever = self.knowledge_base.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 4}
        )

        chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=retriever,
            memory=self.memory,
            return_source_documents=True,
            verbose=False
        )

        return chain

    def start_interactive_chat(self):
        """Start an interactive chat session with the user."""
        if not self.chain:
            self.console.print("[red]Error: Knowledge base not initialized. Please process PDFs first.[/red]")
            return

        self.console.print("[bold green]PDF Knowledge Assistant[/bold green]")
        self.console.print("Chat with your documents! Type 'exit' or 'quit' to end the session.\n")

        while True:
            query = input("\n[You]: ")

            if query.lower() in ["exit", "quit", "q"]:
                self.console.print("[yellow]Exiting chat session. Goodbye![/yellow]")
                break

            if not query.strip():
                continue

            try:
                self.console.print("\n[AI]: ", end="")
                result = self.chain({"question": query})

                # Print sources after response
                source_docs = result.get("source_documents", [])
                if source_docs:
                    sources = set()
                    for doc in source_docs:
                        if "source" in doc.metadata:
                            sources.add(doc.metadata["source"])

                    if sources:
                        self.console.print("\n\n[dim]Sources: " + ", ".join(sources) + "[/dim]")

            except Exception as e:
                self.console.print(f"\n[red]Error during conversation: {e}[/red]")
                continue
