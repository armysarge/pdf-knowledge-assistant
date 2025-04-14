#!/usr/bin/env python3
"""
Sample script to demonstrate the PDF Knowledge Assistant API usage
"""

import requests
import time
import sys
import json
from rich.console import Console
from rich.markdown import Markdown

def main():
    # Configure API endpoint
    base_url = "http://localhost:8000"
    console = Console()

    # Check API status
    console.print("[yellow]Checking API status...[/yellow]")
    try:
        response = requests.get(f"{base_url}/status")
        status_data = response.json()
        console.print(f"[green]API Status: {status_data['status']}[/green]")
        console.print(f"[green]Message: {status_data['message']}[/green]")
    except Exception as e:
        console.print(f"[red]Error: Could not connect to API. Make sure the API server is running.[/red]")
        console.print(f"[red]Exception: {e}[/red]")
        sys.exit(1)

    # Process PDFs (if needed)
    if status_data['status'] != "ready":
        console.print("\n[yellow]Knowledge base is not ready. Triggering PDF processing...[/yellow]")
        try:
            response = requests.post(
                f"{base_url}/process-pdfs",
                json={"force_rebuild": False}
            )
            process_data = response.json()
            console.print(f"[green]Processing status: {process_data['status']}[/green]")
            console.print(f"[green]Message: {process_data['message']}[/green]")

            # If processing started, wait for it to complete
            if process_data['status'] == "processing":
                console.print("\n[yellow]Waiting for processing to complete. This may take some time...[/yellow]")
                time.sleep(5)  # Wait a bit before checking status again

                # Check status repeatedly until ready
                while True:
                    response = requests.get(f"{base_url}/status")
                    status_data = response.json()
                    if status_data['status'] == "ready":
                        console.print("[green]Knowledge base is now ready![/green]")
                        break
                    else:
                        console.print("[yellow]Still processing...[/yellow]")
                        time.sleep(5)  # Check every 5 seconds
        except Exception as e:
            console.print(f"[red]Error processing PDFs: {e}[/red]")
            sys.exit(1)

    # Query the knowledge base
    console.print("\n[bold]Let's ask some questions about the PDFs:[/bold]")

    # Sample questions to demonstrate the API
    questions = [
        "What are the main topics covered in the PDFs?",
        "Can you summarize the key points from the documents?"
    ]

    for question in questions:
        console.print(f"\n[bold blue]Question: {question}[/bold blue]")
        try:
            response = requests.post(
                f"{base_url}/query",
                json={"query": question}
            )
            result = response.json()

            # Display the answer
            console.print("\n[bold green]Answer:[/bold green]")
            console.print(Markdown(result['answer']))

            # Display sources
            if result['sources']:
                console.print("\n[dim]Sources:[/dim]")
                for source in result['sources']:
                    console.print(f"[dim]- {source}[/dim]")
        except Exception as e:
            console.print(f"[red]Error querying API: {e}[/red]")

    # Interactive query mode
    console.print("\n[bold green]Enter your own questions (or type 'exit' to quit):[/bold green]")
    while True:
        query = input("\nYour question: ")
        if query.lower() in ["exit", "quit", "q"]:
            break

        if not query.strip():
            continue

        try:
            response = requests.post(
                f"{base_url}/query",
                json={"query": query}
            )
            result = response.json()

            # Display the answer
            console.print("\n[bold green]Answer:[/bold green]")
            console.print(Markdown(result['answer']))

            # Display sources
            if result['sources']:
                console.print("\n[dim]Sources:[/dim]")
                for source in result['sources']:
                    console.print(f"[dim]- {source}[/dim]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    main()
