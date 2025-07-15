#!/usr/bin/env python
"""
Multi-Source Paper Ingestion Script

This script allows continuous ingestion of papers from multiple sources:
- Semantic Scholar
- CORE API
- ArXiv

Features:
- Can run indefinitely with configurable limits
- Respects API rate limits and quotas
- Processes papers in batches with appropriate delays
- Supports resuming from previous runs
- Rotates between different search queries and sources
- Comprehensive logging and statistics

Usage:
    python scripts/multi_source_ingest.py --sources semantic_scholar core arxiv --queries-file queries.txt --run-time 12h
"""

import os
import sys
import time
import json
import argparse
import logging
import signal
import random
from datetime import datetime, timedelta
from pathlib import Path
from threading import Event

# Add the app directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
log_filename = f"multi_source_ingest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_filename)
    ]
)
logger = logging.getLogger(__name__)

# Import app and components after path setup
from app import create_app
from app.config import Config
from app.chatbot.api_fetchers import (
    SemanticScholarFetcher, CoreFetcher, ArxivFetcher,
    semantic_scholar_quota_manager, core_quota_manager
)
from app.chatbot.pdf_processor import PDFProcessor
from app.chatbot.vector_store import VectorStore

# Signal handler for graceful shutdown
shutdown_event = Event()

def signal_handler(sig, frame):
    """Handle interrupt signals"""
    logger.info("Received interrupt signal. Finishing current batch and shutting down...")
    shutdown_event.set()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def parse_arguments():
    """Parse command line arguments for the ingestion process"""
    parser = argparse.ArgumentParser(description="Multi-source paper ingestion script")
    
    # Sources configuration
    parser.add_argument("--sources", nargs="+", 
                        choices=["semantic_scholar", "core", "arxiv"],
                        default=["semantic_scholar"],
                        help="API sources to use (can specify multiple)")
    
    # Query configuration
    parser.add_argument("--queries", nargs="+", type=str,
                        help="Search queries (can specify multiple)")
    parser.add_argument("--queries-file", type=str,
                        help="File containing search queries, one per line")
    
    # Time and quota configuration
    parser.add_argument("--run-time", type=str, default="1h",
                        help="Maximum run time in format: 30m, 2h, 1d (minutes, hours, days)")
    parser.add_argument("--max-papers", type=int, default=None,
                        help="Maximum number of papers to ingest across all sources")
    parser.add_argument("--quota-reserve", type=float, default=0.1,
                        help="Fraction of daily quota to reserve (0.1 = 10%%)")
    
    # Processing parameters
    parser.add_argument("--batch-size", type=int, default=2,
                        help="Papers to process in each batch (default: 2)")
    parser.add_argument("--min-delay", type=float, default=3.0,
                        help="Minimum delay between batches in seconds (default: 3.0)")
    parser.add_argument("--max-delay", type=float, default=10.0,
                        help="Maximum delay between batches in seconds (default: 10.0)")
    parser.add_argument("--year-filter", type=str, default="last 3 years",
                        help="Year filter (e.g., 'last 5 years', '2020-2023', '2022')")
    parser.add_argument("--min-citation-count", type=int, default=None,
                        help="Minimum citation count (for sources that support it)")
    
    # Output and tracking
    parser.add_argument("--stats-file", type=str, 
                        default=f"ingest_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        help="File to save statistics to")
    parser.add_argument("--state-file", type=str, 
                        default="ingest_state.json",
                        help="File to save state for resuming")
    parser.add_argument("--open-access-only", action="store_true", default=True,
                        help="Only ingest papers with open access PDFs (default: True)")
    parser.add_argument("--verbose", "-v", action="count", default=0,
                        help="Increase verbosity (can be used multiple times)")
    parser.add_argument("--debug", action="store_true", default=False,
                        help="Enable debug mode with additional logging")
    
    args = parser.parse_args()
    
    # Process run time
    args.run_seconds = parse_time_string(args.run_time)
    
    # Process queries
    if args.queries and not args.queries_file:
        # Use directly provided queries
        logger.info(f"Using {len(args.queries)} queries provided via --queries")
    elif not args.queries and not args.queries_file:
        # Default queries if none provided
        args.queries = ["artificial intelligence", "machine learning"]
        logger.info("Using default queries as none were provided")
    elif args.queries_file:
        try:
            with open(args.queries_file, 'r') as f:
                file_queries = [line.strip() for line in f if line.strip()]
                # If both are provided, prioritize command line arguments
                if args.queries:
                    logger.info(f"Using {len(args.queries)} queries from command line (ignoring queries file)")
                else:
                    args.queries = file_queries
                    logger.info(f"Loaded {len(args.queries)} queries from file: {args.queries_file}")
        except Exception as e:
            logger.error(f"Error reading queries file: {str(e)}")
            if not args.queries:
                args.queries = ["artificial intelligence", "machine learning"]
                logger.info("Using default queries as queries file could not be read")
    
    return args

def parse_time_string(time_str):
    """Convert a time string like '1h', '30m', '1d' to seconds"""
    if not time_str:
        return 3600  # Default 1 hour
    
    unit = time_str[-1].lower()
    try:
        value = int(time_str[:-1])
    except ValueError:
        logger.warning(f"Invalid time format: {time_str}, using default 1 hour")
        return 3600
    
    if unit == 'm':
        return value * 60
    elif unit == 'h':
        return value * 3600
    elif unit == 'd':
        return value * 86400
    else:
        logger.warning(f"Unknown time unit: {unit}, using default 1 hour")
        return 3600

def setup_logging_level(verbosity):
    """Configure logging level based on verbosity"""
    if verbosity >= 2:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    elif verbosity >= 1:
        logging.getLogger().setLevel(logging.INFO)
    else:
        logging.getLogger().setLevel(logging.WARNING)

def save_state(state, filename):
    """Save current state to a file for resuming later"""
    try:
        with open(filename, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save state: {str(e)}")

def load_state(filename):
    """Load state from a file"""
    if not os.path.exists(filename):
        return None
    
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load state: {str(e)}")
        return None

def process_papers(fetcher, papers, pdf_processor, vector_store, batch_size, min_delay, max_delay, source_name):
    """
    Process a batch of papers: download PDFs, extract chunks, and add to vector store.
    
    Args:
        fetcher: API fetcher instance
        papers: List of papers to process
        pdf_processor: PDF processor instance
        vector_store: Vector store instance
        batch_size: Number of papers to process in each batch
        min_delay: Minimum delay between API calls
        max_delay: Maximum delay between API calls
        source_name: Source name for logging
    
    Returns:
        Dict with statistics about the processing
    """
    logger.info(f"[INGESTION_DEBUG] Starting process_papers with {len(papers)} papers from {source_name}")
    logger.info(f"[INGESTION_DEBUG] Using vector store collection: {vector_store.collection_name}")
    # Define a safe add_chunk function that handles errors gracefully
    def safe_add_chunk(chunk_with_metadata):
        try:
            # Log detailed information about the chunk being added
            metadata = chunk_with_metadata.get('metadata', {})
            title = metadata.get('title', 'Unknown')
            source_id = metadata.get('source_id', 'Unknown')
            chunk_size = len(chunk_with_metadata.get('text', ''))
            logger.debug(f"[VECTOR_STORE] Adding chunk to vector store - Title: {title}, ID: {source_id}, Size: {chunk_size} chars")
            
            # Attempt to add to vector store
            point_id = vector_store.add_chunk(chunk_with_metadata)
            
            # Log successful addition with point_id
            logger.debug(f"[VECTOR_STORE] Successfully added chunk with point_id: {point_id}")
            return True
        except Exception as e:
            logger.error(f"[VECTOR_STORE_ERROR] Failed to add chunk to vector store: {str(e)}")
            # Add more detailed error information
            import traceback
            logger.debug(f"[VECTOR_STORE_ERROR] Error trace: {traceback.format_exc()}")
            return False
    
    stats = {
        "processed": 0,
        "success": 0,
        "failed": 0,
        "no_pdf": 0,
        "chunks_generated": 0,
        "chunks_indexed": 0,
        "vector_store_success": 0,     # New: papers successfully added to vector store
        "vector_store_failed": 0,      # New: papers that failed vector store addition
        "papers": []
    }
    
    logger.info(f"[INGESTION_STATUS] Starting batch processing for {source_name}")
    
    # Process papers in batches
    for i in range(0, len(papers), batch_size):
        if shutdown_event.is_set():
            logger.info("Shutdown requested, stopping paper processing")
            break
            
        batch = papers[i:i+batch_size]
        logger.info(f"Processing batch {i//batch_size+1}/{(len(papers)-1)//batch_size+1} ({len(batch)} papers)")
        
        for paper in batch:
            if shutdown_event.is_set():
                break
                
            stats["processed"] += 1
            paper_stats = {"title": paper.get("title", "Unknown"), "status": "processing"}
            
            # Get paper ID based on fetcher type
            paper_id = None
            if source_name == "core":
                if 'id' in paper:
                    paper_id = paper['id']
            elif source_name == "semantic_scholar":
                if 'paperId' in paper:
                    paper_id = paper['paperId']
            elif source_name == "arxiv":
                if 'id' in paper:
                    paper_id = paper['id'].split('/')[-1]
            
            if not paper_id:
                logger.warning(f"No ID found for paper: {paper.get('title', 'Unknown')}")
                paper_stats["status"] = "failed"
                paper_stats["error"] = "No paper ID found"
                stats["failed"] += 1
                stats["papers"].append(paper_stats)
                continue
            
            # Download PDF
            logger.info(f"Processing paper: {paper.get('title', paper_id)}")
            pdf_path, pdf_hash = fetcher.download_paper(paper_id)
            
            if not pdf_path:
                logger.warning(f"No PDF available for paper ID: {paper_id}")
                paper_stats["status"] = "no_pdf"
                stats["no_pdf"] += 1
                stats["papers"].append(paper_stats)
                continue
                
            # Split the PDF processing into separate try-except blocks
            # First, build metadata and extract chunks
            try:
                logger.info(f"[INGESTION_DEBUG] Starting PDF processing for paper: {paper_id}")
                
                # Get year from paper metadata
                year = paper.get("year")
                if isinstance(year, str) and year.isdigit():
                    year = int(year)
                    logger.debug(f"[INGESTION_DEBUG] Parsed year: {year} from {paper.get('year')}")
                
                # Build metadata dictionary
                metadata = {
                    "source_id": paper_id,
                    "title": paper.get("title", "Unknown"),
                    "authors": paper.get("authors", []),
                    "year": year,
                    "source": source_name,
                    "ingested_at": datetime.now().isoformat(),  # Track when it was ingested
                    "pdf_hash": pdf_hash  # Store the PDF hash for deduplication
                }
                
                logger.info(f"[INGESTION_DEBUG] Built metadata: {json.dumps({k: str(v) for k, v in metadata.items()})[:200]}...")
                
                # Process PDF and extract chunks
                logger.info(f"[INGESTION_DEBUG] Extracting chunks from PDF: {pdf_path}")
                chunks = pdf_processor.get_chunks(pdf_path)
                chunk_count = len(chunks) if chunks else 0
                stats["chunks_generated"] += chunk_count
                logger.info(f"[INGESTION_DEBUG] Extracted {chunk_count} chunks from paper: {paper.get('title', paper_id)}")
                
            except Exception as e:
                # Handle errors in PDF processing and chunk extraction
                import traceback
                error_trace = traceback.format_exc()
                logger.error(f"[PROCESSING_ERROR] Failed to process PDF: {str(e)}")
                logger.debug(f"[PROCESSING_ERROR] Error trace: {error_trace}")
                paper_stats["status"] = "processing_error"
                paper_stats["error"] = str(e)
                paper_stats["error_trace"] = error_trace[:500]  # Truncated trace for logging
                stats["failed"] += 1
                stats["papers"].append(paper_stats)
                continue  # Skip to the next paper
            
            # Second, add chunks to vector store if extraction was successful
            if chunks:
                # Track chunks successfully added to vector store for this paper
                chunks_indexed_for_paper = 0
                chunks_failed_for_paper = 0
                
                for i, chunk in enumerate(chunks):
                    chunk_with_metadata = {
                        'text': chunk,
                        'metadata': metadata,
                        'chunk_id': f"{paper_id}_{i}"  # Add unique chunk ID for better tracking
                    }
                    
                    # Log chunk details before adding
                    logger.debug(f"[INGESTION_DEBUG] Processing chunk {i+1}/{len(chunks)} for paper {paper_id}: {len(chunk)} chars")
                    
                    # Add chunk to vector store with error handling
                    if safe_add_chunk(chunk_with_metadata):
                        stats["chunks_indexed"] += 1
                        chunks_indexed_for_paper += 1
                    else:
                        chunks_failed_for_paper += 1
                        logger.warning(f"[VECTOR_STORE_WARNING] Failed to index chunk {i+1}/{len(chunks)} for paper {paper_id}")
                
                # Update paper statistics
                paper_stats["status"] = "success"
                paper_stats["chunks"] = len(chunks)
                paper_stats["chunks_indexed"] = chunks_indexed_for_paper
                paper_stats["chunks_failed"] = chunks_failed_for_paper
                
                # Track vector store success/failure for this paper
                if chunks_indexed_for_paper > 0:
                    stats["success"] += 1
                    stats["vector_store_success"] += 1
                    paper_stats["vector_store_status"] = "success"
                    logger.info(f"✓ [SUCCESS] Successfully added '{paper.get('title', '')}' to vector store with {chunks_indexed_for_paper}/{len(chunks)} chunks")
                else:
                    stats["failed"] += 1
                    stats["vector_store_failed"] += 1
                    paper_stats["vector_store_status"] = "failed"
                    logger.error(f"✗ [FAILURE] Failed to add any chunks for '{paper.get('title', '')}' to vector store")
            else:
                paper_stats["status"] = "no_chunks"
                paper_stats["error"] = "No text chunks extracted"
                stats["failed"] += 1
                logger.warning(f"✗ Failed to extract chunks from '{paper.get('title', '')}'")
            # Add paper stats to the list
            stats["papers"].append(paper_stats)
        
        # Delay between batches with random jitter to avoid API rate limiting
        if i + batch_size < len(papers) and not shutdown_event.is_set():
            delay = random.uniform(min_delay, max_delay)
            logger.info(f"Pausing for {delay:.2f} seconds before next batch...")
            time.sleep(delay)
    
    # Log detailed statistics at the end of processing
    logger.info("[INGESTION_STATS] " + "=" * 40)
    logger.info(f"[INGESTION_STATS] Completed processing {len(papers)} papers from {source_name}")
    logger.info(f"[INGESTION_STATS] Papers processed: {stats['processed']}")
    logger.info(f"[INGESTION_STATS] Successfully processed: {stats['success']}")
    logger.info(f"[INGESTION_STATS] Failed processing: {stats['failed']}")
    logger.info(f"[INGESTION_STATS] No PDF available: {stats['no_pdf']}")
    logger.info(f"[INGESTION_STATS] Chunks generated: {stats['chunks_generated']}")
    logger.info(f"[INGESTION_STATS] Chunks indexed in vector store: {stats['chunks_indexed']}")
    logger.info(f"[INGESTION_STATS] Success rate: {(stats['vector_store_success']/stats['processed'])*100:.1f}% of processed papers successfully added to vector store")
    logger.info(f"[INGESTION_STATS] Vector store success: {stats['vector_store_success']}/{stats['processed']} papers")
    logger.info("[INGESTION_STATS] " + "=" * 40)
    
    # Verify vector store status after batch processing
    try:
        collection_info = vector_store.get_collection()
        if collection_info:
            logger.info(f"[VECTOR_STORE_STATUS] Collection {vector_store.collection_name} contains {collection_info.get('vectors_count', 'unknown')} vectors")
    except Exception as ve:
        logger.error(f"[VECTOR_STORE_STATUS] Error checking vector store after processing: {str(ve)}")
    
    return stats

def run_ingestion(args):
    """Run the ingestion pipeline with the specified parameters"""
    # Initialize global statistics
    global_stats = {
        "start_time": datetime.now().isoformat(),
        "queries_processed": 0,
        "total_papers_processed": 0,
        "total_papers_successful": 0,
        "total_papers_failed": 0,
        "total_chunks_generated": 0,
        "total_chunks_indexed": 0,
        "sources": {},
        "queries": {}
    }
    
    # Load previous state if available
    prev_state = load_state(args.state_file)
    processed_combinations = set()
    if prev_state:
        processed_combinations = set(prev_state.get("processed_combinations", []))
    
    # Create Flask app with minimal configuration
    try:
        # Try with normal config first
        app = create_app(config_class=Config)
        logger.info("Created app with standard configuration")
    except Exception as e:
        logger.warning(f"Failed to create app with standard config: {str(e)}")
        # Fall back to a minimal configuration
        class MinimalConfig:
            SECRET_KEY = 'minimal-config'
            SQLALCHEMY_DATABASE_URI = None
            SQLALCHEMY_TRACK_MODIFICATIONS = False
        
        app = create_app(config_class=MinimalConfig)
        logger.info("Created app with minimal configuration")
    
    # Initialize components that don't need app context
    logger.info("Initializing components...")
    pdf_processor = PDFProcessor(store_dir="app/static/uploads/pdf_store")
    
    # Initialize fetchers outside app context since they mainly use HTTP requests
    fetchers = {}
    if "semantic_scholar" in args.sources:
        fetchers["semantic_scholar"] = SemanticScholarFetcher()
    if "core" in args.sources:
        fetchers["core"] = CoreFetcher()
    if "arxiv" in args.sources:
        fetchers["arxiv"] = ArxivFetcher()
    
    # Initialize quota managers
    quota_managers = {
        "semantic_scholar": semantic_scholar_quota_manager,
        "core": core_quota_manager,
        # No quota manager for ArXiv
    }
    
    # Initialize VectorStore - we'll set this inside the app context below
    vector_store = None
    
    # Create a persistent app context that will be used throughout the script
    # This ensures all database operations use the same connection
    app_ctx = app.app_context()
    app_ctx.push()  # Push the application context
    
    # Maximum number of retries for VectorStore initialization
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(1, max_retries + 1):
        try:
            # Initialize the VectorStore within the app context
            logger.info(f"Initializing VectorStore (attempt {attempt}/{max_retries})")
            vector_store = VectorStore()
            
            # Verify the VectorStore is actually operational
            if not hasattr(vector_store, '_check_qdrant_connection') or not vector_store._check_qdrant_connection():
                raise Exception("VectorStore initialized but connection check failed - Qdrant may not be fully ready")
                
            logger.info("Successfully initialized VectorStore within application context and verified connection")
            break  # Success, exit the retry loop
            
        except Exception as e:
            logger.error(f"VectorStore initialization attempt {attempt} failed: {str(e)}")
            
            if attempt < max_retries:
                logger.info(f"Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("All VectorStore initialization attempts failed")
                
                # Clean up the app context before exiting
                logger.info("Cleaning up application context")
                app_ctx.pop()
                logger.error("Cannot proceed without vector store. Exiting.")
                return
    
    # Calculate time limit
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=args.run_seconds)
    
    logger.info(f"Beginning multi-source ingestion until {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Using sources: {', '.join(args.sources)}")
    logger.info(f"Run time: {args.run_time} ({args.run_seconds} seconds)")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Delay between batches: {args.min_delay}-{args.max_delay} seconds")
        
    # Initialize source-specific stats
    for source in args.sources:
        global_stats["sources"][source] = {
                "papers_processed": 0,
                "papers_successful": 0,
                "papers_failed": 0,
                "papers_no_pdf": 0,
                "chunks_generated": 0,
                "chunks_indexed": 0,
                "api_calls": 0
            }
        
    papers_ingested = 0
    queries_processed = 0
        
    # Main ingestion loop
    try:
        # Rotate between queries and sources
        while datetime.now() < end_time and not shutdown_event.is_set():
            if args.max_papers and papers_ingested >= args.max_papers:
                logger.info(f"Reached maximum paper limit: {args.max_papers}")
                break
                
            # Pick a random query and source
            query = random.choice(args.queries)
            source = random.choice(args.sources)
            
            # Skip combinations we've already processed if we're not done with all combinations
            combination_key = f"{source}:{query}"
            if len(processed_combinations) < len(args.sources) * len(args.queries) and combination_key in processed_combinations:
                logger.debug(f"Skipping already processed combination: {combination_key}")
                continue
            
            # Check quota before proceeding
            if source in quota_managers:
                quota_manager = quota_managers[source]
                quota_info = quota_manager.get_quota_info()
                
                # Check if we're out of quota
                if quota_info["daily_limit"] > 0 and quota_info["usage"] >= quota_info["daily_limit"]:
                    logger.warning(f"Quota limit reached for {source}. Skipping.")
                    continue
                
                # Check if we're approaching quota limits
                if quota_info["daily_limit"] > 0 and quota_info["remaining"] < quota_info["daily_limit"] * args.quota_reserve:
                    logger.warning(f"Approaching quota limit for {source}. Remaining: {quota_info['remaining']}. Skipping.")
                    continue
            
            logger.info(f"Processing query '{query}' with source: {source}")
            fetcher = fetchers[source]
            
            # Execute the search
            try:
                if source == "semantic_scholar":
                    papers = fetcher.search(
                        query=query,
                        max_results=args.batch_size * 5,  # Get more than we need for this run
                        year_filter=args.year_filter,
                        open_access_only=args.open_access_only
                    )
                    total_count = len(papers)
                elif source == "core":
                    papers = fetcher.search(
                        query=query,
                        max_results=args.batch_size * 5,
                        year_filter=args.year_filter
                    )
                    total_count = len(papers)
                elif source == "arxiv":
                    papers = fetcher.search(
                        query=query,
                        max_results=args.batch_size * 5,
                        year_filter=args.year_filter
                    )
                    total_count = len(papers)
                else:
                    logger.error(f"Unknown source: {source}")
                    continue
                
                if not papers:
                    logger.warning(f"No papers found for query '{query}' with source {source}")
                    processed_combinations.add(combination_key)
                    continue
                
                logger.info(f"Found {len(papers)} papers for query '{query}' with source {source}")
                
                # Process the papers - we're already in an app context from initialization
                try:
                    # Process papers directly using the persistent app context
                    stats = process_papers(
                        fetcher=fetcher,
                        papers=papers,
                        pdf_processor=pdf_processor,
                        vector_store=vector_store,
                        batch_size=args.batch_size,
                        min_delay=args.min_delay,
                        max_delay=args.max_delay,
                        source_name=source
                    )
                except Exception as e:
                    logger.error(f"Error processing papers: {str(e)}")
                    # Provide empty stats on failure
                    stats = {
                        "processed": 0,
                        "success": 0,
                        "failed": len(papers),
                        "no_pdf": 0,
                        "chunks_generated": 0,
                        "chunks_indexed": 0,
                        "papers": []
                    }
                
                # Update global statistics
                global_stats["total_papers_processed"] += stats["processed"]
                global_stats["total_papers_successful"] += stats["success"]
                global_stats["total_papers_failed"] += stats["failed"]
                global_stats["total_chunks_generated"] += stats["chunks_generated"]
                global_stats["total_chunks_indexed"] += stats["chunks_indexed"]
                
                # Update source-specific statistics
                global_stats["sources"][source]["papers_processed"] += stats["processed"]
                global_stats["sources"][source]["papers_successful"] += stats["success"]
                global_stats["sources"][source]["papers_failed"] += stats["failed"]
                global_stats["sources"][source]["papers_no_pdf"] += stats["no_pdf"]
                global_stats["sources"][source]["chunks_generated"] += stats["chunks_generated"]
                global_stats["sources"][source]["chunks_indexed"] += stats["chunks_indexed"]
                global_stats["sources"][source]["api_calls"] += 1
                
                # Update query statistics
                if query not in global_stats["queries"]:
                    global_stats["queries"][query] = {
                        "papers_processed": 0,
                        "papers_successful": 0,
                        "papers_failed": 0
                    }
                global_stats["queries"][query]["papers_processed"] += stats["processed"]
                global_stats["queries"][query]["papers_successful"] += stats["success"]
                global_stats["queries"][query]["papers_failed"] += stats["failed"]
                
                papers_ingested += stats["processed"]
                queries_processed += 1
                global_stats["queries_processed"] = queries_processed
                
                # Mark this combination as processed
                processed_combinations.add(combination_key)
                
                # Periodically save state and statistics
                current_state = {
                    "last_update": datetime.now().isoformat(),
                    "processed_combinations": list(processed_combinations),
                    "papers_ingested": papers_ingested,
                    "queries_processed": queries_processed
                }
                save_state(current_state, args.state_file)
                
                # Update statistics file
                global_stats["end_time"] = datetime.now().isoformat()
                global_stats["duration_seconds"] = (datetime.now() - start_time).total_seconds()
                with open(args.stats_file, 'w') as f:
                    json.dump(global_stats, f, indent=2)
                
                # Add a longer delay between queries to avoid rate limiting
                if not shutdown_event.is_set() and datetime.now() < end_time:
                    between_query_delay = random.uniform(args.max_delay, args.max_delay * 2)
                    logger.info(f"Pausing for {between_query_delay:.2f} seconds before next query...")
                    time.sleep(between_query_delay)
            
            except Exception as e:
                logger.exception(f"Error processing query '{query}' with source {source}: {str(e)}")
                # Continue with the next iteration
        
    finally:
        # Final statistics
        global_stats["end_time"] = datetime.now().isoformat()
        global_stats["duration_seconds"] = (datetime.now() - start_time).total_seconds()
            
        # Save final statistics
        with open(args.stats_file, 'w') as f:
            json.dump(global_stats, f, indent=2)
            
        # Print summary
        logger.info("=" * 60)
        logger.info("INGESTION COMPLETE - SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total duration: {global_stats['duration_seconds']:.2f} seconds")
        logger.info(f"Queries processed: {global_stats['queries_processed']}")
        logger.info(f"Total papers processed: {global_stats['total_papers_processed']}")
        # Add zero check before division
        if global_stats['total_papers_processed'] > 0:
            success_rate = global_stats['total_papers_successful']/global_stats['total_papers_processed']*100
            logger.info(f"Successfully processed: {global_stats['total_papers_successful']} ({success_rate:.1f}% success rate)")
        else:
            logger.info(f"Successfully processed: {global_stats['total_papers_successful']} (0.0% success rate)")
        logger.info(f"Total chunks indexed: {global_stats['total_chunks_indexed']}")
            
        # Per source statistics
        logger.info("=" * 60)
        logger.info("PER SOURCE STATISTICS")
        logger.info("=" * 60)
        for source, stats in global_stats["sources"].items():
            if stats["papers_processed"] > 0:
                success_rate = stats["papers_successful"] / stats["papers_processed"] * 100
                logger.info(f"Source: {source}")
                logger.info(f"  Papers processed: {stats['papers_processed']}")
                logger.info(f"  Successfully processed: {stats['papers_successful']} ({success_rate:.1f}% success rate)")
                logger.info(f"  Chunks generated: {stats['chunks_generated']}")
                logger.info(f"  Chunks indexed: {stats['chunks_indexed']}")
                logger.info(f"  API calls: {stats['api_calls']}")
            
        logger.info("=" * 60)
        logger.info(f"Detailed statistics saved to: {args.stats_file}")
        
        # Clean up the application context
        try:
            # Only pop the context if it was successfully pushed earlier
            if 'app_ctx' in locals() and app_ctx:
                logger.info("Cleaning up application context")
                try:
                    app_ctx.pop()
                    logger.info("Application context cleaned up successfully")
                except Exception as ctx_err:
                    logger.warning(f"Could not pop app context normally: {str(ctx_err)}")
                    # Try alternate cleanup approach
                    try:
                        from flask import _app_ctx_stack
                        if _app_ctx_stack.top is not None:
                            _app_ctx_stack.pop()
                            logger.info("Application context cleaned up using _app_ctx_stack")
                    except Exception:
                        # Last resort - just make sure we don't crash
                        pass
        except Exception as e:
            logger.error(f"Error cleaning up application context: {str(e)}")
            # Continue regardless of cleanup success

def main():
    """Main entry point for the script"""
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Configure logging based on verbosity
        setup_logging_level(args.verbose)
        
        logger.info("=" * 60)
        logger.info("STARTING MULTI-SOURCE PAPER INGESTION")
        logger.info("=" * 60)
        logger.info(f"Sources: {args.sources}")
        logger.info(f"Run time: {args.run_time} ({args.run_seconds} seconds)")
        logger.info(f"Batch size: {args.batch_size}")
        logger.info(f"Delay between batches: {args.min_delay}-{args.max_delay} seconds")
        
        # Check if required directories exist
        pdf_store_dir = "app/static/uploads/pdf_store"
        if not os.path.exists(pdf_store_dir):
            logger.info(f"Creating PDF store directory: {pdf_store_dir}")
            os.makedirs(pdf_store_dir, exist_ok=True)
        
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
