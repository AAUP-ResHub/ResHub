import os
import hashlib
import re
import shutil
import tempfile
import requests
import time
from datetime import datetime
import logging
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError
from flask import current_app
from app import db
from app.chatbot.models import IndexedDocument

class PDFProcessor:
    """
    Utility class for processing PDF research papers.
    - Extracts text from PDFs
    - Chunks text for embedding generation
    - Stores PDFs with SHA-256 filenames
    - Downloads and processes PDFs from URLs
    """
    
    def __init__(self, store_dir='app/static/uploads/pdf_store'):
        """Initialize the PDF processor with the storage directory."""
        self.store_dir = store_dir
        os.makedirs(self.store_dir, exist_ok=True)
        
    def _log(self, level, message):
        """
        Helper method to log messages with proper handling for Flask context.
        
        Args:
            level: Log level ('info', 'warning', 'error')
            message: Message to log
        """
        try:
            # Try to use Flask's logger if we're in a Flask context
            flask_app_available = False
            try:
                # This will raise RuntimeError if we're outside application context
                if current_app:
                    flask_app_available = True
            except (RuntimeError, AttributeError):
                flask_app_available = False
            
            if flask_app_available:
                if level == 'error':
                    current_app.logger.error(message)
                elif level == 'warning':
                    current_app.logger.warning(message)
                else:
                    current_app.logger.info(message)
            else:
                # Fallback to standard logging
                logger = logging.getLogger(__name__)
                if level == 'error':
                    logger.error(message)
                elif level == 'warning':
                    logger.warning(message)
                else:
                    logger.info(message)
        except Exception as e:
            # Last resort if all else fails
            print(f"{message} (Logger error: {str(e)})")
    
    def process_pdf(self, pdf_path, metadata=None):
        """
        Process a PDF file:
        1. Calculate SHA-256 hash
        2. Store PDF in the target directory with hash filename
        3. Extract text and create chunks
        4. Store metadata in database
        
        Args:
            pdf_path: Path to the PDF file
            metadata: Dictionary with optional metadata (title, authors, etc.)
            
        Returns:
            Tuple of (document_id, stored_path, chunks)
        """
        # Check if file exists
        if not os.path.exists(pdf_path):
            self._log('error', f"PDF file does not exist: {pdf_path}")
            return None, None, []
            
        # Check if file is empty
        if os.path.getsize(pdf_path) == 0:
            self._log('error', f"PDF file is empty: {pdf_path}")
            return None, None, []
        
        try:
            # Calculate SHA-256 hash
            with open(pdf_path, 'rb') as f:
                content = f.read()
                file_hash = hashlib.sha256(content).hexdigest()
            
            # Define target path
            target_path = os.path.join(self.store_dir, f"{file_hash}.pdf")
            
            # Create storage directory if it doesn't exist
            os.makedirs(self.store_dir, exist_ok=True)
            
            # Store PDF if it doesn't exist
            if not os.path.exists(target_path):
                with open(target_path, 'wb') as f:
                    f.write(content)
                self._log('info', f"Saved PDF to {target_path}")
            else:
                self._log('info', f"PDF already exists at {target_path}")
            
            # Extract text and create chunks
            chunks = self.extract_chunks(target_path)
            if not chunks:
                self._log('warning', f"No text chunks extracted from {pdf_path}")
            else:
                self._log('info', f"Extracted {len(chunks)} text chunks from {pdf_path}")
            
            # Initialize doc regardless of metadata presence
            # Convert author list to JSON if needed
            authors_json = metadata.get('authors', []) if metadata else []
            if isinstance(authors_json, list):
                authors_json = ", ".join(authors_json)  # Convert to string for simpler storage
        
            # Store in database
            doc = IndexedDocument(
                document_id=file_hash,
                title=metadata.get('title', 'Untitled') if metadata else 'Untitled',
                authors=authors_json,
                year=metadata.get('year') if metadata else None,
                source=metadata.get('source', 'local') if metadata else 'local',
                source_id=metadata.get('source_id', '') if metadata else '',
                file_path=target_path,
                chunk_count=len(chunks)
            )
        
            # Check if document already exists
            existing_doc = IndexedDocument.query.get(file_hash)
            if existing_doc:
                # Update existing document
                existing_doc.title = doc.title
                existing_doc.authors = doc.authors
                existing_doc.year = doc.year
                existing_doc.source = doc.source
                existing_doc.source_id = doc.source_id
                existing_doc.chunk_count = doc.chunk_count
            else:
                # Add new document
                db.session.add(doc)
                
            db.session.commit()
            self._log('info', f"Stored metadata in database for document {file_hash}")
        
        except Exception as e:
            self._log('error', f"Error processing PDF {pdf_path}: {str(e)}")
            return None, None, []
            
        return file_hash, target_path, chunks
    
    def extract_chunks(self, pdf_path, chunk_size=300, overlap=50):
        """
        Extract text from PDF and split into chunks.
        
        Args:
            pdf_path: Path to the PDF file
            chunk_size: Target chunk size in tokens (approximate)
            overlap: Target overlap between chunks in tokens
            
        Returns:
            List of text chunks
        """
        self._log('info', f"Extracting text from PDF: {pdf_path}")
        
        if not os.path.exists(pdf_path):
            self._log('error', f"PDF file not found: {pdf_path}")
            return []
            
        if os.path.getsize(pdf_path) == 0:
            self._log('error', f"PDF file is empty: {pdf_path}")
            return []
        
        try:
            # Extract text from PDF
            reader = PdfReader(pdf_path)
            
            # Check if PDF has pages
            if len(reader.pages) == 0:
                self._log('warning', f"PDF contains no pages: {pdf_path}")
                return []
                
            text = ""
            for page_num, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text() or ""
                    text += page_text + "\n\n"
                except Exception as e:
                    self._log('warning', f"Error extracting text from page {page_num} in {pdf_path}: {str(e)}")
                
            # Check if PDF is image-only or encrypted
            if not text.strip():
                self._log('warning', f"PDF appears to be image-only or has no extractable text: {pdf_path}")
                return []
            
            # Simple chunking (approximate tokens by characters/4)
            chunks = []
            # Rough estimate: 1 token = 4 characters
            char_size = chunk_size * 4
            overlap_chars = overlap * 4
            
            # Split text by paragraphs first
            paragraphs = text.split("\n\n")
            current_chunk = ""
            
            for para in paragraphs:
                # If adding this paragraph would exceed chunk size, save current chunk and start new one
                if len(current_chunk) + len(para) > char_size and current_chunk:
                    chunks.append(current_chunk.strip())
                    # Keep some overlap with previous chunk
                    current_chunk = current_chunk[-overlap_chars:] if len(current_chunk) > overlap_chars else current_chunk
                
                current_chunk += para + "\n\n"
            
            # Don't forget the last chunk
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
                
            # Log the result
            if chunks:
                self._log('info', f"Successfully created {len(chunks)} chunks from {pdf_path}")
            else:
                self._log('warning', f"No chunks generated from {pdf_path}")
                
            return chunks
            
        except PdfReadError as e:
            self._log('error', f"PDF read error for {pdf_path}: {str(e)}")
            return []
        except Exception as e:
            self._log('error', f"Error extracting text from PDF {pdf_path}: {str(e)}")
            return []
            
    def process_from_url(self, url, metadata=None, timeout=30, max_retries=3):
        """
        Download and process a PDF from a URL.
        
        Args:
            url: URL of the PDF to download
            metadata: Optional metadata for the document
            timeout: Timeout for the HTTP request in seconds
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of text chunks extracted from the PDF or empty list on failure
        """
        # Log attempt to process PDF from URL
        self._log('info', f"Processing PDF from URL: {url}")
        
        chunks = []
        temp_file = None
        
        try:
            # Create a temporary file to store the PDF
            temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
            os.close(temp_fd)
            temp_file = temp_path
            
            # Download the PDF with retry logic
            retry_count = 0
            while retry_count < max_retries:
                try:
                    # Use a generous timeout and stream the response
                    self._log('info', f"Downloading PDF (attempt {retry_count + 1}/{max_retries})")
                    headers = {"User-Agent": "ResHub Research Assistant/1.0"}
                    response = requests.get(url, stream=True, timeout=timeout, headers=headers)
                    response.raise_for_status()
                    
                    # Check if content type is PDF
                    content_type = response.headers.get('Content-Type', '').lower()
                    if 'pdf' not in content_type and 'octet-stream' not in content_type and 'application/download' not in content_type:
                        self._log('warning', f"URL may not point to a PDF. Content-Type: {content_type}")
                        # Continue anyway, we'll verify the content later
                    
                    # Save the PDF to the temporary file
                    with open(temp_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    # Verify the downloaded file is a valid PDF
                    self._validate_pdf(temp_path)
                    
                    # Process the PDF using the existing method
                    document_id, stored_path, chunks = self.process_pdf(temp_path, metadata)
                    self._log('info', f"Successfully processed PDF from URL: {url}. Generated {len(chunks)} chunks.")
                    break
                    
                except requests.exceptions.Timeout:
                    retry_count += 1
                    if retry_count >= max_retries:
                        self._log('error', f"Timeout downloading PDF after {max_retries} attempts: {url}")
                        break
                    self._log('warning', f"Timeout downloading PDF from {url}, retrying ({retry_count}/{max_retries})")
                    # Exponential backoff
                    time.sleep(2 ** retry_count)
                    
                except requests.exceptions.HTTPError as e:
                    status_code = e.response.status_code if hasattr(e, 'response') and hasattr(e.response, 'status_code') else 'unknown'
                    self._log('error', f"HTTP Error {status_code} downloading PDF: {url}")
                    if status_code in (403, 404, 410):  # Not found or forbidden
                        break  # Don't retry for these status codes
                    retry_count += 1
                    if retry_count >= max_retries:
                        break
                    time.sleep(2 ** retry_count)
                    
                except (PdfReadError, ValueError) as e:
                    # PDF validation error
                    self._log('error', f"Invalid PDF file from {url}: {str(e)}")
                    break  # Don't retry for invalid PDFs
                    
                except requests.exceptions.RequestException as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        self._log('error', f"Failed to download PDF after {max_retries} attempts: {str(e)}")
                        break
                    self._log('warning', f"Error downloading PDF from {url}, retrying ({retry_count}/{max_retries}): {str(e)}")
                    time.sleep(2 ** retry_count)
                    
        except Exception as e:
            self._log('error', f"Unexpected error processing PDF from URL {url}: {str(e)}")
            
        finally:
            # Clean up the temporary file
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except Exception as e:
                    self._log('warning', f"Failed to delete temporary file {temp_file}: {str(e)}")
        
        return chunks
    
    def _validate_pdf(self, file_path):
        """
        Validate that a file is a proper PDF document.
        
        Args:
            file_path: Path to the PDF file
            
        Raises:
            ValueError: If the file is not a valid PDF
            PdfReadError: If PyPDF2 cannot read the file
        """
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise ValueError("Empty file")
            
        if file_size > 50 * 1024 * 1024:  # 50MB
            raise ValueError(f"File too large ({file_size / (1024*1024):.2f} MB)")
        
        # Try to read the PDF with PyPDF2
        try:
            reader = PdfReader(file_path)
            if len(reader.pages) == 0:
                raise ValueError("PDF contains no pages")
                
            # Try to extract some text to verify it's readable
            sample_text = reader.pages[0].extract_text()
            if sample_text is None or len(sample_text.strip()) == 0:
                # PDF might be image-only, but it's still a valid PDF
                pass
                
        except PdfReadError:
            raise  # Re-raise the PdfReadError
        except Exception as e:
            raise ValueError(f"Failed to validate PDF: {str(e)}")
    
    def hash_file(self, file_path):
        """Calculate SHA-256 hash of a file."""
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        return file_hash
    
    def update_metadata(self, document_id, metadata):
        """
        Update the metadata of an indexed document.
        
        Args:
            document_id: The document ID to update
            metadata: Dictionary with metadata to update
            
        Returns:
            Updated IndexedDocument or None if not found
        """
        # Find the document in the database
        document = IndexedDocument.query.get(document_id)
        
        if not document:
            return None
            
        # Update fields if provided
        if 'title' in metadata:
            document.title = metadata['title']
        if 'authors' in metadata:
            # Convert author list to string if needed
            authors = metadata['authors']
            if isinstance(authors, list):
                authors = ", ".join(authors)
            document.authors = authors
        if 'year' in metadata:
            document.year = metadata['year']
        if 'source' in metadata:
            document.source = metadata['source']
        if 'source_id' in metadata:
            document.source_id = metadata['source_id']
        if 'url' in metadata:
            document.url = metadata['url']
            
        # Update timestamp
        document.updated_at = datetime.utcnow()
        db.session.commit()
        
        return document
    
    def get_document_stats(self):
        """
        Get statistics about indexed documents.
        
        Returns:
            Dictionary with statistics
        """
        # Get document count
        doc_count = IndexedDocument.query.count()
        
        # Get vector count
        vector_count = db.session.query(db.func.sum(IndexedDocument.chunk_count)).scalar() or 0
        
        # Calculate storage used
        storage_used = 0
        if os.path.exists(self.store_dir):
            for file in os.listdir(self.store_dir):
                if file.endswith('.pdf'):
                    file_path = os.path.join(self.store_dir, file)
                    storage_used += os.path.getsize(file_path)
        
        # Get last indexed date
        last_doc = IndexedDocument.query.order_by(IndexedDocument.created_at.desc()).first()
        last_indexed = last_doc.created_at if last_doc else None
        
        # Get source distribution
        sources = db.session.query(IndexedDocument.source, db.func.count(IndexedDocument.source))\
                .group_by(IndexedDocument.source).all()
        source_distribution = {source: count for source, count in sources}
        
        # Get year distribution
        years = db.session.query(IndexedDocument.year, db.func.count(IndexedDocument.year))\
                .group_by(IndexedDocument.year).all()
        year_distribution = {year: count for year, count in years if year is not None}
        
        return {
            'doc_count': doc_count,
            'vector_count': vector_count,
            'storage_used': storage_used,
            'last_indexed': last_indexed,
            'source_distribution': source_distribution,
            'year_distribution': year_distribution
        }
        
    def clean_orphaned_files(self):
        """
        Delete PDF files that are not referenced in the database.
        
        Returns:
            Tuple of (count of files deleted, space freed in bytes)
        """
        # Get all indexed document IDs
        indexed_ids = [doc.document_id for doc in IndexedDocument.query.all()]
        
        # Check all files in the storage directory
        count = 0
        space_freed = 0
        
        if os.path.exists(self.store_dir):
            for file in os.listdir(self.store_dir):
                if file.endswith('.pdf'):
                    # Get the file ID (remove .pdf extension)
                    file_id = file[:-4]
                    file_path = os.path.join(self.store_dir, file)
                    
                    # Check if this file is not in the indexed documents
                    if file_id not in indexed_ids:
                        # Get file size before deleting
                        file_size = os.path.getsize(file_path)
                        space_freed += file_size
                        
                        # Delete the file
                        os.remove(file_path)
                        count += 1
        
        return count, space_freed
    
    def export_pdf(self, document_id, target_path):
        """
        Export a PDF file to a specified location.
        
        Args:
            document_id: The document ID to export
            target_path: The target path to copy the PDF to
            
        Returns:
            Boolean indicating success
        """
        # Find the document in the database
        document = IndexedDocument.query.get(document_id)
        
        if not document or not os.path.exists(document.file_path):
            return False
            
        # Copy the file
        try:
            shutil.copy2(document.file_path, target_path)
            return True
        except Exception as e:
            print(f"Error exporting PDF: {str(e)}")
            return False
            
    def get_chunks(self, pdf_path, chunk_size=300, overlap=50):
        """
        Wrapper for extract_chunks to maintain compatibility with multi_source_ingest.py.
        
        Args:
            pdf_path: Path to the PDF file
            chunk_size: Target chunk size in tokens (approximate)
            overlap: Target overlap between chunks in tokens
            
        Returns:
            List of text chunks
        """
        return self.extract_chunks(pdf_path, chunk_size, overlap)
