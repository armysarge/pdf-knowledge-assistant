"""
Enhanced chat interface module with true streaming support
"""

import os
import asyncio
from typing import List, Optional, AsyncIterator, Generator, Tuple
from rich.console import Console
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.llms import LlamaCpp
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from huggingface_hub import hf_hub_download
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from contextlib import redirect_stderr

# Custom streaming callback handler that yields tokens
class StreamingCallbackHandler(StreamingStdOutCallbackHandler):
    def __init__(self):
        super().__init__()
        self.tokens = []
        self.queue = asyncio.Queue()

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        # Don't print to stdout
        self.tokens.append(token)
        # Add token to the queue for async consumption
        self.queue.put_nowait(token)

    def on_llm_end(self, *args, **kwargs) -> None:
        # Signal that LLM generation is complete
        self.queue.put_nowait(None)

    async def get_tokens(self) -> AsyncIterator[str]:
        # Yield tokens as they become available
        while True:
            token = await self.queue.get()
            if token is None:  # End signal
                break
            yield token


class ChatInterface:
    """Enhanced interface for chatting with the knowledge base using a local LLM with streaming support."""

    def __init__(self, knowledge_base, model_path: Optional[str] = None, debug: bool = False):
        """
        Initialize the chat interface with a knowledge base and optional model path.

        Args:
            knowledge_base: The knowledge base to query
            model_path: Optional path to local LLM model (downloads model if not provided)
            debug: Whether to show debug information like performance metrics
        """
        self.knowledge_base = knowledge_base
        self.console = Console()
        self.debug = debug
        self.model_path = self._get_model_path(model_path)
        self.callback_handler = StreamingStdOutCallbackHandler()
        self.llm = self._load_llm()
        self.streaming_llm = None  # Will be initialized on demand
        self.current_source_docs = []  # Track current source documents
        self.message_history = ChatMessageHistory()
        # Create prompt template
        self.qa_template = """You are a helpful PDF Knowledge Assistant that provides accurate information from documents.

Here is the relevant information:
---------------------
{context}
---------------------

Answer the question using only the information provided above. Do not:
- Start with "Based on..." or reference the context
- Rephrase the question
- Start with a question

Question: {question}
Answer: """

        self.qa_prompt = PromptTemplate(
            template=self.qa_template,
            input_variables=["context", "question"]
        )

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
        model_filename = "mistral-7b-instruct-v0.2.Q4_K_M.gguf"

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

        # Create a standard callback manager
        callback_manager = CallbackManager([self.callback_handler])

        # Create a null device to discard stderr output temporarily
        with open(os.devnull, 'w') as null_stderr:
            with redirect_stderr(null_stderr):
                llm = LlamaCpp(
                    model_path=self.model_path,
                    temperature=0.1,
                    max_tokens=2048,
                    n_ctx=32768,  # Reduced context size to prevent memory issues
                    top_p=0.95,
                    callback_manager=callback_manager,
                    verbose=self.debug,  # Only show performance metrics in debug mode
                    n_gpu_layers=-1,  # CPU-only mode to ensure compatibility
                    n_batch=512,  # Batch size for efficiency
                    f16_kv=True,  # Use half-precision for key/value cache
                    seed=42  # Fixed seed for reproducibility
                    # Removed potentially problematic parameters
                )

        self.console.print("[green]LLM model loaded successfully![/green]")
        return llm

    def start_interactive_chat(self):
        """Start an interactive chat session with the user."""
        self.console.print("\n\n[bold green]PDF Knowledge Assistant[/bold green]")
        self.console.print("Chat with your documents! Type 'exit' or 'quit' to end the session.\n")

        # Check if knowledge base exists
        if not self.knowledge_base.check_knowledge_base_exists():
            self.console.print("[red]Error: Knowledge base not initialized. Please process PDFs first.[/red]")
            return

        while True:
            query = input("\n[You]: ")

            if query.lower() in ["exit", "quit", "q"]:
                self.console.print("[yellow]Exiting chat session. Goodbye![/yellow]")
                break

            if not query.strip():
                continue

            try:
                self.console.print("\n[AI]: ", end="")

                # Get response using the get_response method
                result, sources = self.get_response(query)
                self.console.print(result)

                # Display sources after response
                if sources:
                    self.console.print("\n[dim]Sources: " + ", ".join(sources) + "[/dim]")

                # Add to message history
                self.message_history.add_user_message(query)
                self.message_history.add_ai_message(result)

            except Exception as e:
                self.console.print(f"\n[red]Error during conversation: {e}[/red]")
                continue

    def _load_streaming_llm(self):
        """
        Load a separate LLM instance configured for streaming.

        Returns:
            Loaded LLM instance with streaming callbacks
        """
        # Create a streaming callback handler
        streaming_handler = StreamingCallbackHandler()
        callback_manager = CallbackManager([streaming_handler])

        # Create a null device to discard stderr output temporarily
        with open(os.devnull, 'w') as null_stderr:
            with redirect_stderr(null_stderr):                streaming_llm = LlamaCpp(
                    model_path=self.model_path,
                    temperature=0.1,
                    max_tokens=2048,
                    n_ctx=4096,  # Reduced context size
                    top_p=0.95,
                    callback_manager=callback_manager,
                    verbose=False,  # Disable verbose output for streaming
                    n_gpu_layers=0,  # CPU-only mode for compatibility
                    n_batch=512,
                    f16_kv=True,
                    seed=42,
                    streaming=True  # Enable streaming!
                )

        return streaming_llm, streaming_handler

    def get_response(self, query: str) -> tuple[str, list[str]]:
        """
        Get a response for a single query.

        Args:
            query: The user's question

        Returns:
            Tuple of (response text, list of sources)
        """
        if not self.knowledge_base.check_knowledge_base_exists():
            raise RuntimeError("Knowledge base not initialized. Please process PDFs first.")

        # Retrieve documents from knowledge base
        docs = self.knowledge_base.vector_store.similarity_search(query, k=4)
        self.current_source_docs = docs

        # Format context from documents
        context = "\n\n".join(doc.page_content for doc in docs)

        # Format prompt with context and question
        prompt = self.qa_prompt.format(context=context, question=query)

        # Get response from LLM
        result = self.llm.invoke(prompt)

        # Get sources from the current docs
        sources = []
        if self.current_source_docs:
            for doc in self.current_source_docs:
                if "source" in doc.metadata:
                    sources.append(doc.metadata["source"])

        return result, list(set(sources))

    async def get_streaming_response(self, query: str) -> AsyncIterator[Tuple[str, list[str]]]:
        """
        Get a streaming response for a query.

        Args:
            query: The user's question

        Yields:
            Tuples of (token, list of sources)
        """
        if not self.knowledge_base.check_knowledge_base_exists():
            raise RuntimeError("Knowledge base not initialized. Please process PDFs first.")

        # Initialize streaming LLM on first use
        if not self.streaming_llm:
            self.streaming_llm, self.streaming_handler = self._load_streaming_llm()

        # Retrieve documents from knowledge base
        docs = self.knowledge_base.vector_store.similarity_search(query, k=4)
        self.current_source_docs = docs

        # Format context from documents
        context = "\n\n".join(doc.page_content for doc in docs)

        # Format prompt with context and question
        prompt = self.qa_prompt.format(context=context, question=query)

        # Start generating response (will push to the streaming handler)
        # We don't need to await this as it will push tokens to the handler
        asyncio.create_task(
            asyncio.to_thread(self.streaming_llm.invoke, prompt)
        )

        # Get sources from the docs
        sources = []
        if self.current_source_docs:
            for doc in self.current_source_docs:
                if "source" in doc.metadata:
                    sources.append(doc.metadata["source"])
        unique_sources = list(set(sources))

        # Stream tokens as they're generated
        async for token in self.streaming_handler.get_tokens():
            yield token, unique_sources