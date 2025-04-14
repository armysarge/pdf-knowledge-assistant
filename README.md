[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Donate-brightgreen?logo=buymeacoffee)](https://www.buymeacoffee.com/armysarge)

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![GitHub issues](https://img.shields.io/github/issues/armysarge/pdf-knowledge-assistant)](https://github.com/armysarge/pdf-knowledge-assistant/issues)

# PDF Knowledge Assistant

A Python application that processes PDFs to train a local AI, enabling conversational Q&A about the documents. This tool allows you to upload PDF documents and chat with a local LLM that can answer questions based solely on the content of those documents.

## Features

- **PDF Processing**: Extract and process text from PDF documents
- **Local LLM**: Uses a free, high-quality open source LLM that runs on your local machine
- **RAG System**: Implements Retrieval Augmented Generation to provide accurate answers
- **Vector Database**: Stores document embeddings locally for fast retrieval
- **Interactive Chat**: Simple command-line interface to ask questions about your documents
- **REST API**: Access the knowledge assistant through a web API for integration with other applications

## Requirements

- Python 3.8 or higher
- 32GB RAM (recommended) for optimal LLM performance
- Sufficient disk space for the LLM model (~15GB)

## Installation

1. Clone the repository or navigate to the project directory:

```powershell
cd "https://github.com/armysarge/pdf-knowledge-assistant"
```

2. Create a Python virtual environment:

```powershell
python -m venv venv
```

3. Activate the virtual environment:

```powershell
.\venv\Scripts\Activate
```

4. Install the required dependencies:

```powershell
pip install -r requirements.txt
```

## Usage

### Adding PDF Documents

Place your PDF files in the `data/pdfs` directory:

```powershell
# Create the directory if it doesn't exist
mkdir -p "data/pdfs"

# Copy your PDFs to this directory
# For example:
# copy "C:\path\to\your\document.pdf" "data\pdfs\"
```

### Processing PDFs

Process all PDFs in the `data/pdfs` directory to build your knowledge base:

```powershell
python main.py process-pdfs
```

You can also force a rebuild of your knowledge base:

```powershell
python main.py process-pdfs --force-rebuild
```

### Chatting with Your Documents

Start an interactive chat session to ask questions about your documents:

```powershell
python main.py chat
```

The first time you run this command, it will automatically download a Mistral 7B model (approximately 4GB) from Hugging Face.

During the chat session:
- Type your questions about the content of your PDFs
- The AI will respond based solely on information contained in your PDFs
- Sources will be cited for each response
- Type 'exit' or 'quit' to end the session

### Using the REST API

Start the API server:

```powershell
python main.py api-server
```

The API will be available at `http://localhost:8000` with the following endpoints:

- `GET /status` - Check if the knowledge base is ready
- `POST /process-pdfs` - Process PDFs in the background
- `POST /query` - Ask a question about your documents

#### Example API Usage

```python
import requests

# Query the API
response = requests.post(
    "http://localhost:8000/query",
    json={"query": "What are the key points in the document?"}
)

result = response.json()
print(f"Answer: {result['answer']}")
print(f"Sources: {', '.join(result['sources'])}")
```

You can also use the included test script to interact with the API:

```powershell
python api_test.py
```

## How It Works

1. **PDF Processing**: The application uses `PyPDFLoader` to extract text from your PDFs and splits the text into manageable chunks.

2. **Embedding Creation**: The text chunks are converted into vector embeddings using `HuggingFaceEmbeddings` and stored in a FAISS vector database.

3. **Query Processing**: When you ask a question, the application:
   - Converts your question into a vector embedding
   - Retrieves the most similar document chunks from the vector database
   - Sends your question and the relevant document chunks to the local LLM
   - Returns the LLM's response along with source citations

4. **Local LLM**: The application uses `LlamaCpp` to run the Mistral 7B Instruct model locally on your machine, with optimizations for systems with 32GB RAM.