"""
Chat interface module for interacting with the knowledge base using a local LLM
"""

import os
from typing import List, Optional
from rich.console import Console
from rich.markdown import Markdown
import sys
from contextlib import redirect_stderr
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.chains import ConversationalRetrievalChain
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_community.llms import LlamaCpp
from langchain.memory import ConversationBufferMemory
from huggingface_hub import hf_hub_download
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.schema import BaseChatMessageHistory
from src.knowledge_base import KnowledgeBase
from langchain_core.messages import HumanMessage, AIMessage

class ChatInterface:
    """Interface for chatting with the knowledge base using a local LLM."""

    def __init__(self, knowledge_base: KnowledgeBase, model_path: Optional[str] = None, debug: bool = False):
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
        self.llm = self._load_llm()
        self.current_source_docs = []  # Track current source documents
        self.message_history = ChatMessageHistory()
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
        model_filename = "mistral-7b-instruct-v0.2.Q8_0.gguf"

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

        callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])        # Load the model with appropriate settings for a machine with 32GB RAM

        # Create a null device to discard stderr output temporarily
        with open(os.devnull, 'w') as null_stderr:
            with redirect_stderr(null_stderr):
                llm = LlamaCpp(
                    model_path=self.model_path,
                    temperature=0.1,
                    max_tokens=2048,
                    n_ctx=32768,
                    top_p=0.95,
                    callback_manager=callback_manager,
                    verbose=self.debug,  # Only show performance metrics in debug mode
                    n_gpu_layers=-1,  # Use all possible layers on GPU
                    n_batch=512,  # Batch size for efficiency
                    f16_kv=True,  # Use half-precision for key/value cache
                    seed=42,  # Fixed seed for reproducibility
                    use_mlock=True,  # Lock memory to prevent swapping
                    n_threads=8  # Adjust based on your CPU cores
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

        # Create a custom prompt template that instructs the model to answer directly
        qa_template = """You are a helpful PDF Knowledge Assistant that provides 100% accurate information from documents.

Context information is below.
---------------------
{context}
---------------------

Given the context information and not prior knowledge, answer the question directly and concisely.
IMPORTANT: Do not rephrase the question in your answer. Do not start your answer with a question.
Just provide the information the user is looking for.

Question: {question}
Answer: """

        qa_prompt = PromptTemplate(
            template=qa_template,
            input_variables=["context", "question"]
        )        # Create the chain using LCEL (LangChain Expression Language)
        # Create a chain that also preserves source documents
        def format_docs(docs):
            # Keep track of source documents and return formatted context
            self.current_source_docs = docs
            return "\n\n".join(doc.page_content for doc in docs)

        chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | qa_prompt
            | self.llm
            | StrOutputParser()
        )

        return chain

    def start_interactive_chat(self):
        """Start an interactive chat session with the user."""
        if not self.chain:
            self.console.print("[red]Error: Knowledge base not initialized. Please process PDFs first.[/red]")
            return

        self.console.print("\n\n[bold green]PDF Knowledge Assistant[/bold green]")
        self.console.print("Chat with your documents! Type 'exit' or 'quit' to end the session.\n")

        chat_history = []
        while True:
            query = input("\n[You]: ")

            if query.lower() in ["exit", "quit", "q"]:
                self.console.print("[yellow]Exiting chat session. Goodbye![/yellow]")
                break

            if not query.strip():
                continue
            try:
                self.console.print("\n[AI]: ", end="")
                # Invoke chain with the query
                result = self.chain.invoke(query)

                # Display sources after response
                if self.current_source_docs:
                    sources = set()
                    for doc in self.current_source_docs:
                        if "source" in doc.metadata:
                            sources.add(doc.metadata["source"])
                    if sources:
                        self.console.print("\n[dim]Sources: " + ", ".join(sources) + "[/dim]")

                # Update chat history for next iteration
                chat_history.append(HumanMessage(content=query))
                chat_history.append(AIMessage(content=result))

            except Exception as e:
                self.console.print(f"\n[red]Error during conversation: {e}[/red]")
                continue

    def get_response(self, query: str) -> tuple[str, list[str]]:
        """
        Get a response for a single query.

        Args:
            query: The user's question

        Returns:
            Tuple of (response text, list of sources)
        """
        if not self.chain:
            raise RuntimeError("Knowledge base not initialized. Please process PDFs first.")

        result = self.chain.invoke(query)

        # Get sources from the current docs
        sources = []
        if self.current_source_docs:
            for doc in self.current_source_docs:
                if "source" in doc.metadata:
                    sources.append(doc.metadata["source"])

        return result, list(set(sources))
