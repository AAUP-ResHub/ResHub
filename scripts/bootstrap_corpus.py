#!/usr/bin/env python
"""
Bootstrap Corpus Script

This script loads papers from a CSV file or a directory of PDFs and indexes them
in the vector database. It's designed to seed a new ResHub instance with initial content.

Usage:
    python bootstrap_corpus.py --seed seeds/seed_papers.csv

Arguments:
    --seed: Path to CSV file or directory containing papers (default: seeds/seed_papers.csv)
"""

import os
import sys
import csv
import argparse
import logging
from pathlib import Path
import shutil
import time

# Add the app directory to the Python path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.chatbot.pdf_processor import PDFProcessor
from app.chatbot.vector_store import VectorStore
from app.chatbot.models import IndexedDocument
from app.models import User
from app.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bootstrap_corpus.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create Flask app with configuration
app = create_app(config_class=Config)


class CorpusBootstrapper:
    """Bootstrap the corpus by loading papers from a CSV file or directory."""
    
    def __init__(self, seed_path):
        """Initialize the bootstrapper with the source path."""
        self.seed_path = seed_path
        
        # Initialize components
        with app.app_context():
            self.pdf_store = app.config.get('PDF_STORAGE_PATH') or 'storage/pdfs'
            os.makedirs(self.pdf_store, exist_ok=True)
            
            self.pdf_processor = PDFProcessor()
            self.vector_store = VectorStore()
        
        # Stats
        self.stats = {
            'total_papers': 0,
            'indexed_papers': 0,
            'failed_papers': 0,
            'existing_papers': 0,
            'total_chunks': 0,
            'start_time': None,
            'end_time': None
        }
    
    def load_from_csv(self, csv_path):
        """Load papers from a CSV file."""
        papers = []
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                papers = list(reader)
                
            logger.info(f"Loaded {len(papers)} papers from {csv_path}")
            return papers
        except Exception as e:
            logger.error(f"Error loading papers from CSV: {str(e)}")
            return []
    
    def load_from_directory(self, dir_path):
        """Load papers from a directory of PDFs."""
        papers = []
        try:
            for pdf_file in Path(dir_path).glob('*.pdf'):
                # Extract basic metadata from filename
                name = pdf_file.stem
                papers.append({
                    'id': f"local-{name}",
                    'title': name.replace('_', ' ').title(),
                    'pdf_path': str(pdf_file),
                    'authors': '',
                    'year': '',
                    'abstract': ''
                })
                
            logger.info(f"Found {len(papers)} PDF papers in {dir_path}")
            return papers
        except Exception as e:
            logger.error(f"Error loading papers from directory: {str(e)}")
            return []
    
    def process_paper(self, paper):
        """Process and index a single paper."""
        with app.app_context():
            try:
                # Check if paper already exists in index
                existing = IndexedDocument.query.filter_by(source_id=paper['id']).first()
                if existing:
                    logger.info(f"Paper already indexed: {paper['title']} ({paper['id']})")
                    self.stats['existing_papers'] += 1
                    return False
                
                # Handle PDF content - either from URL, local path or embedded content
                pdf_path = None
                if 'pdf_path' in paper and os.path.exists(paper['pdf_path']):
                    # Local PDF file
                    dest_path = os.path.join(self.pdf_store, f"{paper['id']}.pdf")
                    shutil.copy(paper['pdf_path'], dest_path)
                    pdf_path = dest_path
                elif 'pdf_url' in paper and paper['pdf_url']:
                    # For demo seed data, we can't download from example.org
                    # In a real scenario, we'd use requests to download the PDF
                    # For now, create a simple PDF with the abstract
                    from reportlab.pdfgen import canvas
                    from reportlab.lib.pagesizes import letter
                    
                    temp_pdf_path = os.path.join(self.pdf_store, f"{paper['id']}.pdf")
                    c = canvas.Canvas(temp_pdf_path, pagesize=letter)
                    c.drawString(72, 800, paper['title'])
                    c.drawString(72, 780, f"Authors: {paper['authors']}")
                    c.drawString(72, 760, f"Year: {paper['year']}")
                    
                    # Write abstract with wrapping
                    y_position = 740
                    abstract_lines = [paper['abstract'][i:i+80] for i in range(0, len(paper['abstract']), 80)]
                    for line in abstract_lines:
                        c.drawString(72, y_position, line)
                        y_position -= 15
                        
                    c.save()
                    pdf_path = temp_pdf_path
                    logger.info(f"Created demo PDF for {paper['id']}")
                
                if not pdf_path:
                    logger.error(f"No PDF available for paper: {paper['title']} ({paper['id']})")
                    self.stats['failed_papers'] += 1
                    return False
                
                # Process the PDF
                try:
                    chunks = self.pdf_processor.process_pdf(pdf_path)
                    self.stats['total_chunks'] += len(chunks)
                except Exception as e:
                    logger.error(f"Error processing PDF: {str(e)}")
                    self.stats['failed_papers'] += 1
                    return False
                
                # Create document record
                # Find or create admin user 
                admin = User.query.filter_by(username='admin').first()
                if not admin:
                    from werkzeug.security import generate_password_hash
                    admin = User(username='admin', email='admin@example.com',
                                password_hash=generate_password_hash('admin'))
                    db.session.add(admin)
                    db.session.commit()
                    logger.info("Created admin user for document attribution")
                
                document = IndexedDocument(
                    title=paper['title'],
                    authors=paper['authors'],
                    year=paper.get('year', ''),
                    source_id=paper['id'],
                    source="seed",
                    file_path=pdf_path,
                    abstract=paper.get('abstract', ''),
                    document_id=f"seed-{paper['id']}"
                )
                
                db.session.add(document)
                db.session.commit()
                
                # Index chunks in vector store
                for i, chunk in enumerate(chunks):
                    # Add document context to each chunk
                    chunk_with_context = {
                        'text': chunk,
                        'document_id': document.id,
                        'chunk_id': i,
                        'metadata': {
                            'title': paper['title'],
                            'authors': paper['authors'],
                            'year': paper.get('year', '')
                        }
                    }
                    
                    self.vector_store.add_chunk(chunk_with_context)
                
                logger.info(f"Indexed paper: {paper['title']} with {len(chunks)} chunks")
                self.stats['indexed_papers'] += 1
                return True
                
            except Exception as e:
                logger.error(f"Error indexing paper {paper.get('title', 'Unknown')}: {str(e)}")
                self.stats['failed_papers'] += 1
                return False
    
    def run(self):
        """Run the bootstrapping process."""
        self.stats['start_time'] = time.time()
        
        # Determine source type and load papers
        papers = []
        if os.path.isfile(self.seed_path) and self.seed_path.endswith('.csv'):
            papers = self.load_from_csv(self.seed_path)
        elif os.path.isdir(self.seed_path):
            papers = self.load_from_directory(self.seed_path)
        else:
            logger.error(f"Invalid seed path: {self.seed_path}")
            return self.stats
        
        self.stats['total_papers'] = len(papers)
        
        # Process each paper
        for i, paper in enumerate(papers):
            logger.info(f"Processing paper {i+1}/{len(papers)}: {paper.get('title', 'Unknown')}")
            self.process_paper(paper)
        
        self.stats['end_time'] = time.time()
        duration = self.stats['end_time'] - self.stats['start_time']
        
        # Print summary
        logger.info(f"""
        ========== Bootstrap Summary ==========
        Seed Source: {self.seed_path}
        Total Papers: {self.stats['total_papers']}
        Successfully Indexed: {self.stats['indexed_papers']}
        Already Existing: {self.stats['existing_papers']}
        Failed: {self.stats['failed_papers']}
        Total Chunks: {self.stats['total_chunks']}
        Duration: {duration:.2f} seconds
        ======================================
        """)
        
        return self.stats


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Bootstrap the corpus with papers.")
    parser.add_argument(
        "--seed", 
        default="seeds/seed_papers.csv",
        help="Path to CSV file or directory containing papers (default: seeds/seed_papers.csv)"
    )
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    bootstrapper = CorpusBootstrapper(args.seed)
    bootstrapper.run()
