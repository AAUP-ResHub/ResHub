#!/usr/bin/env python
"""
Semantic Scholar Ingestion Script

This script implements a complete ingestion pipeline for Semantic Scholar papers:
- Configures and initializes Flask app context
- Sets up API client with proper authentication and rate limiting
- Allows configurable search parameters via command line arguments
- Processes papers in small batches with appropriate delays
- Adds extracted text chunks to the vector store
- Provides comprehensive logging and statistics reporting

Usage:
    python scripts/ingest_semantic_scholar.py --query "machine learning" --max-results 10 --year-filter "last 5 years" --batch-size 2 --delay 3
"""

import os
import sys
import time
import argparse
import logging
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add the app directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables from .env file (for API keys)
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"semantic_scholar_ingest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger(__name__)

# Import app and components after path setup
from app import create_app
from app.config import Config
from app.chatbot.api_fetchers import SemanticScholarFetcher
from app.chatbot.pdf_processor import PDFProcessor
from app.chatbot.vector_store import VectorStore

def parse_arguments():
    """Parse command line arguments for configuring the ingestion process"""
    parser = argparse.ArgumentParser(description="Semantic Scholar paper ingestion script")
    
    # Search parameters
    parser.add_argument("--query", type=str, required=True,
                        help="Search query for papers (required)")
    parser.add_argument("--max-results", type=int, default=10,
                        help="Maximum number of papers to fetch (default: 10)")
    parser.add_argument("--year-filter", type=str, default="last 3 years",
                        help="Year filter (e.g., 'last 5 years', '2020-2023', '2022')")
    parser.add_argument("--open-access-only", action="store_true", default=True,
                        help="Only fetch papers with open access PDFs (default: True)")
    parser.add_argument("--min-citation-count", type=int, default=None,
                        help="Minimum citation count for papers (default: None)")
    parser.add_argument("--venue", type=str, default=None,
                        help="Filter by publication venue (default: None)")
    parser.add_argument("--publication-types", type=str, default=None,
                        help="Comma-separated list of publication types (e.g., 'Journal,Conference')")
    
    # Processing parameters
    parser.add_argument("--batch-size", type=int, default=2,
                        help="Number of papers to process in each batch (default: 2)")
    parser.add_argument("--delay", type=float, default=3.0,
                        help="Delay in seconds between processing batches (default: 3.0)")
    parser.add_argument("--max-papers", type=int, default=None,
                        help="Maximum number of papers to process (default: all fetched papers)")
    
    # Output options
    parser.add_argument("--stats-file", type=str, default=None,
                        help="Output file for detailed statistics (JSON format)")
    parser.add_argument("--verbose", "-v", action="count", default=0,
                        help="Increase verbosity (can be used multiple times)")
    
    args = parser.parse_args()
    
    # Process comma-separated publication types if provided
    if args.publication_types:
        args.publication_types = [pt.strip() for pt in args.publication_types.split(',')]
    
    return args

def setup_logging_level(verbosity):
    """Configure logging level based on verbosity"""
    if verbosity >= 2:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    elif verbosity >= 1:
        logging.getLogger().setLevel(logging.INFO)
    else:
        logging.getLogger().setLevel(logging.WARNING)

def run_ingestion(args):
    """Run the full ingestion pipeline with the specified parameters"""
    start_time = time.time()
    
    # Create Flask app and context
    logger.info("Initializing Flask application...")
    app = create_app(config_class=Config)
    
    with app.app_context():
        logger.info("Initializing Semantic Scholar components...")
        
        # Initialize components
        fetcher = SemanticScholarFetcher()
        pdf_processor = PDFProcessor(store_path="app/static/uploads/pdf_store")
        vector_store = VectorStore()
        
        # Verify API key is available
        if not os.environ.get('SEMANTIC_SCHOLAR_API_KEY'):
            logger.error("SEMANTIC_SCHOLAR_API_KEY environment variable not set. Please add it to .env file.")
            return
        
        # Log search parameters
        logger.info(f"Searching for papers with query: '{args.query}'")
        logger.info(f"Search parameters: year_filter='{args.year_filter}', "
                  f"open_access_only={args.open_access_only}, "
                  f"min_citation_count={args.min_citation_count}, "
                  f"venue='{args.venue}', "
                  f"publication_types={args.publication_types}")
        
        # Search for papers
        papers, total_count, next_offset = fetcher.search(
            query=args.query,
            max_results=args.max_results,
            year_filter=args.year_filter,
            open_access_only=args.open_access_only,
            citation_count=args.min_citation_count,
            venue=args.venue,
            publication_types=args.publication_types
        )
        
        logger.info(f"Found {len(papers)} papers from Semantic Scholar (total matching: {total_count})")
        
        if not papers:
            logger.warning("No papers found. Please adjust your search parameters.")
            return
        
        # Display sample of found papers
        logger.info("Sample of found papers:")
        for i, paper in enumerate(papers[:3], 1):
            logger.info(f"  {i}. {paper.get('title')} ({paper.get('year')}) - {len(paper.get('authors', [])) or 'Unknown'} authors, citations: {paper.get('citation_count')}")
        
        # Process papers in batches
        logger.info(f"Processing papers in batches (batch size: {args.batch_size}, delay: {args.delay}s)...")
        stats = fetcher.process_papers(
            papers=papers,
            pdf_processor=pdf_processor,
            batch_size=args.batch_size,
            delay_seconds=args.delay,
            max_papers=args.max_papers
        )
        
        # Index chunks in vector store
        successful_papers = [p for p in stats["papers"] if p["success"]]
        
        logger.info(f"Adding {stats['chunks_generated']} chunks to vector store...")
        chunks_indexed = 0
        
        # Grab all PDFs that were successfully processed and add their chunks to vector store
        for pdf_file in pdf_processor.list_processed_pdfs():
            try:
                metadata = pdf_processor.get_metadata(pdf_file)
                
                # Only index PDFs from this ingestion session (based on source_id)
                if metadata.get('source') != 'semantic_scholar':
                    continue
                
                source_id = metadata.get('source_id')
                if not any(p.get('id') == source_id for p in successful_papers):
                    continue
                
                chunks = pdf_processor.get_chunks(pdf_file)
                if chunks:
                    for chunk in chunks:
                        chunk_with_metadata = {
                            'text': chunk,
                            'metadata': {
                                'document_id': metadata.get('source_id'),
                                'title': metadata.get('title', 'Unknown'),
                                'authors': metadata.get('authors', []),
                                'year': metadata.get('year', ''),
                                'source': 'semantic_scholar'
                            }
                        }
                        # Add chunk to vector store
                        vector_store.add_chunk(chunk_with_metadata)
                        chunks_indexed += 1
            except Exception as e:
                logger.error(f"Error indexing chunks from PDF: {str(e)}")
        
        # Calculate statistics
        elapsed_time = time.time() - start_time
        
        # Final statistics
        logger.info("=" * 50)
        logger.info("INGESTION COMPLETE - SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Query: '{args.query}'")
        logger.info(f"Papers found: {len(papers)} (total matching: {total_count})")
        logger.info(f"Papers processed: {stats['processed']}")
        logger.info(f"Successfully processed: {stats['success']} ({stats['success']/stats['processed']*100:.1f}% success rate)")
        logger.info(f"Failed to process: {stats['failed']}")
        logger.info(f"Papers without PDFs: {stats['no_pdf']}")
        logger.info(f"Chunks generated: {stats['chunks_generated']}")
        logger.info(f"Chunks indexed in vector store: {chunks_indexed}")
        logger.info(f"Total execution time: {elapsed_time:.2f} seconds")
        
        # Save detailed statistics to file if requested
        if args.stats_file:
            detailed_stats = {
                "query": args.query,
                "search_params": {
                    "year_filter": args.year_filter,
                    "open_access_only": args.open_access_only,
                    "min_citation_count": args.min_citation_count,
                    "venue": args.venue,
                    "publication_types": args.publication_types
                },
                "processing_params": {
                    "batch_size": args.batch_size,
                    "delay": args.delay,
                    "max_papers": args.max_papers
                },
                "results": {
                    "papers_found": len(papers),
                    "total_matching": total_count,
                    "papers_processed": stats["processed"],
                    "success_count": stats["success"],
                    "failed_count": stats["failed"],
                    "no_pdf_count": stats["no_pdf"],
                    "chunks_generated": stats["chunks_generated"],
                    "chunks_indexed": chunks_indexed,
                    "success_rate": stats["success"]/stats["processed"] if stats["processed"] > 0 else 0,
                    "elapsed_time": elapsed_time
                },
                "paper_details": stats["papers"],
                "timestamp": datetime.now().isoformat()
            }
            
            with open(args.stats_file, 'w') as f:
                json.dump(detailed_stats, f, indent=2)
                logger.info(f"Detailed statistics saved to: {args.stats_file}")

def main():
    """Main entry point for the script"""
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Configure logging based on verbosity
        setup_logging_level(args.verbose)
        
        # Run the ingestion pipeline
        run_ingestion(args)
        
    except KeyboardInterrupt:
        logger.warning("Ingestion interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"An error occurred during ingestion: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
