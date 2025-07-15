#!/usr/bin/env python
"""
Temporary script to ingest CORE papers
"""

import os
import sys
import time
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.config import Config
from app.chatbot.api_fetchers import CoreFetcher
from app.chatbot.pdf_processor import PDFProcessor
from app.chatbot.vector_store import VectorStore

# Create Flask app and context
app = create_app(config_class=Config)

def main():
    with app.app_context():
        print("Initializing components...")
        fetcher = CoreFetcher()
        pdf_processor = PDFProcessor()
        vector_store = VectorStore()
        
        # Fetch papers
        print("Searching for papers on: Transformer models healthcare")
        papers = fetcher.search('Transformer models healthcare', max_results=10)
        print(f"Found {len(papers)} papers from CORE API")
        
        # Process each paper
        for i, paper in enumerate(papers):
            if paper.get('pdf_url'):
                print(f"Processing paper {i+1}/{len(papers)}: {paper.get('title', 'Unknown Title')}")
                try:
                    chunks = pdf_processor.process_from_url(paper['pdf_url'])
                    for chunk in chunks:
                        chunk_with_context = {
                            'text': chunk,
                            'metadata': {
                                'document_id': paper['id'],
                                'title': paper['title'],
                                'authors': paper['authors'],
                                'year': paper.get('year', '')
                            }
                        }
                        vector_store.add_chunk(chunk_with_context)
                    print(f"Successfully indexed with {len(chunks)} chunks")
                    time.sleep(2)  # Rate limiting
                except Exception as e:
                    print(f"Error processing paper: {str(e)}")
            else:
                print(f"No PDF URL available for: {paper.get('title', 'Unknown Title')}")


if __name__ == "__main__":
    main()
