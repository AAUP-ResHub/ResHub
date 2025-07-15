import hashlib
import json
import os
import re
import requests
import time
import urllib.parse
from bs4 import BeautifulSoup
from datetime import datetime
from flask import current_app
from app.chatbot.api_monitoring import track_api_usage, core_quota_manager, QuotaManager

class ArxivFetcher:
    """Fetches papers from the arXiv API."""
    
    def __init__(self, base_url="http://export.arxiv.org/api/query"):
        self.base_url = base_url
    
    def search(self, query, max_results=50, start=0, year_filter=None):
        """
        Search arXiv for papers matching the query.
        
        Args:
            query: Search terms
            max_results: Maximum number of results to return
            start: Start index for pagination
            year_filter: Optional filter for publication year (e.g. "last 5 years" or "2019-2024")
            
        Returns:
            List of paper metadata dictionaries
        """
        # Process year filter
        if year_filter:
            if "last" in year_filter.lower():
                # Extract number of years
                years_match = re.search(r'(\d+)', year_filter)
                if years_match:
                    years = int(years_match.group(1))
                    current_year = datetime.now().year
                    start_year = current_year - years
                    query = f"{query} AND submittedDate:[{start_year} TO {current_year}]"
            elif "-" in year_filter:
                # Year range (e.g., "2018-2023")
                years = year_filter.split("-")
                if len(years) == 2:
                    start_year, end_year = years
                    query = f"{query} AND submittedDate:[{start_year} TO {end_year}]"
        
        # Prepare request parameters
        params = {
            "search_query": query,
            "start": start,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending"
        }
        
        # Make request
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"ArXiv API request failed: {str(e)}")
            return []
        
        # Parse XML response
        # This is simplified - in production we'd use a proper XML parser
        results = []
        
        # Extract entries using regex (simplified approach)
        entries = re.findall(r'<entry>(.*?)</entry>', response.text, re.DOTALL)
        
        for entry in entries:
            # Extract paper details
            id_match = re.search(r'<id>(.*?)</id>', entry)
            title_match = re.search(r'<title>(.*?)</title>', entry)
            summary_match = re.search(r'<summary>(.*?)</summary>', entry)
            published_match = re.search(r'<published>(.*?)</published>', entry)
            
            # Extract all authors
            authors = re.findall(r'<author><name>(.*?)</name></author>', entry)
            
            # Extract PDF link
            pdf_link = None
            links = re.findall(r'<link[^>]*>(.*?)</link>', entry)
            for link in links:
                if 'pdf' in link.lower():
                    pdf_link_match = re.search(r'href="([^"]*)"', link)
                    if pdf_link_match:
                        pdf_link = pdf_link_match.group(1)
            
            # Only add entry if we have the required fields
            if id_match and title_match:
                arxiv_id = id_match.group(1).split('/')[-1]
                title = title_match.group(1)
                abstract = summary_match.group(1) if summary_match else ""
                
                # Extract year from published date
                year = None
                if published_match:
                    year_match = re.search(r'(\d{4})', published_match.group(1))
                    if year_match:
                        year = int(year_match.group(1))
                
                results.append({
                    'id': arxiv_id,
                    'title': title,
                    'abstract': abstract,
                    'authors': authors,
                    'year': year,
                    'url': f"https://arxiv.org/abs/{arxiv_id}",
                    'pdf_url': f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                    'source': 'arxiv'
                })
        
        return results
    
    def download_paper(self, arxiv_id, store_dir='app/static/uploads/pdf_store'):
        """
        Download a paper from arXiv by ID.
        
        Args:
            arxiv_id: arXiv ID
            store_dir: Directory to store the PDF
            
        Returns:
            Tuple of (file_path, file_hash)
        """
        # Create store directory if it doesn't exist
        os.makedirs(store_dir, exist_ok=True)
        
        # Fetch the PDF
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        try:
            response = requests.get(pdf_url, stream=True)
            response.raise_for_status()
            
            # Calculate SHA-256 hash
            content = response.content
            file_hash = hashlib.sha256(content).hexdigest()
            
            # Save PDF with hash as filename
            file_path = os.path.join(store_dir, f"{file_hash}.pdf")
            
            with open(file_path, 'wb') as f:
                f.write(content)
                
            return file_path, file_hash
            
        except requests.exceptions.RequestException as e:
            print(f"Failed to download PDF from arXiv: {str(e)}")
            return None, None


class SemanticScholarFetcher:
    """Fetches papers from the Semantic Scholar API."""
    
    def __init__(self, api_key=None, base_url="https://api.semanticscholar.org/graph/v1"):
        """Initialize the SemanticScholarFetcher with API key.
        
        Args:
            api_key (str): Semantic Scholar API key. If None, will try to get from environment.
            base_url (str): Base URL for the Semantic Scholar API.
        """
        # Get API key from environment if not provided
        if api_key is None:
            self.api_key = os.environ.get('SEMANTIC_SCHOLAR_API_KEY')
        else:
            self.api_key = api_key
            
        self.base_url = base_url
        
        # Track rate limit information
        self.last_response_headers = None
        self.rate_limit_remaining = None
        self.rate_limit_reset = None
        self.backoff_time = 1  # Initial backoff time in seconds
    
    def _update_rate_limit_info(self, response):
        """Update rate limit information from response headers.
        
        Args:
            response: Response from requests library
            
        Returns:
            None
        """
        self.last_response_headers = response.headers
        
        # Extract rate limit information
        # Header names may vary, these are common ones
        self.rate_limit_remaining = response.headers.get('X-Rate-Limit-Remaining')
        self.rate_limit_reset = response.headers.get('X-Rate-Limit-Reset')
        
        # Log rate limit information
        if 'current_app' in globals():
            if self.rate_limit_remaining is not None:
                try:
                    remaining = int(self.rate_limit_remaining)
                    if remaining < 20:  # Warning threshold
                        current_app.logger.warning(
                            f"Semantic Scholar API quota running low! Only {remaining} requests remaining."
                        )
                except (ValueError, TypeError):
                    pass
    
    def _handle_rate_limit(self, response):
        """Handle rate limiting by implementing exponential backoff.
        
        Args:
            response: Response from requests library
            
        Returns:
            bool: True if the request was successful after retrying, False otherwise
        """
        if response.status_code == 429:  # Too Many Requests
            if 'current_app' in globals():
                current_app.logger.warning(
                    f"Semantic Scholar API rate limit exceeded. Backing off for {self.backoff_time} seconds."
                )
            else:
                print(f"Semantic Scholar API rate limit exceeded. Backing off for {self.backoff_time} seconds.")
                
            # Wait for backoff time
            time.sleep(self.backoff_time)
            
            # Increase backoff time for next attempt (exponential backoff)
            self.backoff_time = min(self.backoff_time * 2, 60)  # Cap at 60 seconds
            
            return False
        
        # Reset backoff time if request was successful
        self.backoff_time = 1
        return True
    
    @track_api_usage("SemanticScholar")
    def search(self, query, max_results=50, year_filter=None, open_access_only=True):
        """
        Search Semantic Scholar for papers matching the query.
        
        Args:
            query: Search terms
            max_results: Maximum number of results to return
            year_filter: Optional filter for publication year (e.g. "last 5 years" or "2019-2024")
            open_access_only: Only return papers with open access PDFs available
            
        Returns:
            List of paper metadata dictionaries
        """
        # Check if API key is available
        if not self.api_key:
            if 'current_app' in globals():
                current_app.logger.error("Semantic Scholar API key is required")
            else:
                print("Semantic Scholar API key is required")
            return []
            
        # Check if we have sufficient quota before making request
        if not semantic_scholar_quota_manager.check_quota():
            if 'current_app' in globals():
                current_app.logger.warning("Semantic Scholar API daily quota exceeded")
            else:
                print("Semantic Scholar API daily quota exceeded")
            return []
            
        # Process year filter
        year_params = {}
        if year_filter:
            if "last" in year_filter.lower():
                # Extract number of years
                years_match = re.search(r'(\d+)', year_filter)
                if years_match:
                    years = int(years_match.group(1))
                    current_year = datetime.now().year
                    start_year = current_year - years
                    year_params = {"year": f"{start_year}-{current_year}"}
            elif "-" in year_filter:
                # Year range (e.g., "2018-2023")
                year_params = {"year": year_filter}
        
        # Build the endpoint and params
        endpoint = f"{self.base_url}/paper/search"
        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,abstract,authors,year,url,openAccessPdf",
        }
        
        # Add open access filter if required
        if open_access_only:
            params["openAccessPdf"] = "true"
            
        params.update(year_params)
        
        # Prepare headers with API key
        headers = {
            "x-api-key": self.api_key
        }
        
        # Make request with retry logic for rate limiting
        max_retries = 3
        retries = 0
        
        while retries < max_retries:
            try:
                if 'current_app' in globals():
                    current_app.logger.info(f"Making Semantic Scholar API request: {endpoint}")
                
                response = requests.get(endpoint, params=params, headers=headers)
                
                # Update rate limit information regardless of status code
                self._update_rate_limit_info(response)
                
                # Handle rate limiting
                if response.status_code == 429:  # Too Many Requests
                    success = self._handle_rate_limit(response)
                    if not success:
                        retries += 1
                        continue
                        
                # For other errors, raise exception
                response.raise_for_status()
                
                # Parse the response data
                data = response.json()
                
                # Increment quota usage on successful request
                semantic_scholar_quota_manager.increment_usage()
                
                break  # Exit the retry loop if successful
                
            except requests.exceptions.RequestException as e:
                if 'current_app' in globals():
                    current_app.logger.error(f"Semantic Scholar API request failed: {str(e)}")
                else:
                    print(f"Semantic Scholar API request failed: {str(e)}")
                    
                # If it's not a rate limit issue or we've maxed out retries, return empty results
                if retries >= max_retries - 1:
                    return []
                    
                retries += 1
                time.sleep(2)  # Simple backoff for non-rate-limit errors
                
            except json.JSONDecodeError:
                if 'current_app' in globals():
                    current_app.logger.error("Failed to parse Semantic Scholar API response")
                else:
                    print("Failed to parse Semantic Scholar API response")
                return []
        
        # Process results
        results = []
        for paper in data.get('data', []):
            # Get PDF URL if available
            pdf_url = None
            if paper.get('openAccessPdf'):
                pdf_url = paper['openAccessPdf'].get('url')
            
            # Extract authors
            authors = []
            for author in paper.get('authors', []):
                if author.get('name'):
                    authors.append(author['name'])
            
            results.append({
                'id': paper.get('paperId', ''),
                'title': paper.get('title', ''),
                'abstract': paper.get('abstract', ''),
                'authors': authors,
                'year': paper.get('year'),
                'url': paper.get('url', ''),
                'pdf_url': pdf_url,
                'source': 'semantic_scholar'
            })
            
        if 'current_app' in globals():
            current_app.logger.info(f"Found {len(results)} papers from Semantic Scholar")
            
        return results
    
    @track_api_usage("SemanticScholar")
    def get_paper_details(self, paper_id):
        """
        Get detailed paper information from Semantic Scholar by ID.
        
        Args:
            paper_id: Semantic Scholar paper ID, DOI, arXiv ID, etc.
            
        Returns:
            Dictionary with paper details or None if not found
        """
        # Check if API key is available
        if not self.api_key:
            if 'current_app' in globals():
                current_app.logger.error("Semantic Scholar API key is required")
            else:
                print("Semantic Scholar API key is required")
            return None
            
        # Check if we have sufficient quota before making request
        if not semantic_scholar_quota_manager.check_quota():
            if 'current_app' in globals():
                current_app.logger.warning("Semantic Scholar API daily quota exceeded")
            else:
                print("Semantic Scholar API daily quota exceeded")
            return None
        
        # Build the endpoint
        endpoint = f"{self.base_url}/paper/{paper_id}"
        
        # Define the fields we want to get
        params = {
            "fields": "paperId,title,abstract,authors,year,url,openAccessPdf"
        }
        
        # Prepare headers with API key
        headers = {
            "x-api-key": self.api_key
        }
        
        # Make request with retry logic for rate limiting
        max_retries = 3
        retries = 0
        
        while retries < max_retries:
            try:
                if 'current_app' in globals():
                    current_app.logger.info(f"Fetching Semantic Scholar paper details for ID: {paper_id}")
                
                response = requests.get(endpoint, params=params, headers=headers)
                
                # Update rate limit information regardless of status code
                self._update_rate_limit_info(response)
                
                # Handle rate limiting
                if response.status_code == 429:  # Too Many Requests
                    success = self._handle_rate_limit(response)
                    if not success:
                        retries += 1
                        continue
                        
                # For other errors, raise exception
                response.raise_for_status()
                
                # Parse the response data
                data = response.json()
                
                # Increment quota usage on successful request
                semantic_scholar_quota_manager.increment_usage()
                
                return data
                
            except requests.exceptions.RequestException as e:
                if 'current_app' in globals():
                    current_app.logger.error(f"Semantic Scholar API request failed: {str(e)}")
                else:
                    print(f"Semantic Scholar API request failed: {str(e)}")
                    
                # If it's not a rate limit issue or we've maxed out retries, return None
                if retries >= max_retries - 1:
                    return None
                    
                retries += 1
                time.sleep(2)  # Simple backoff for non-rate-limit errors
                
            except json.JSONDecodeError:
                if 'current_app' in globals():
                    current_app.logger.error("Failed to parse Semantic Scholar API response")
                else:
                    print("Failed to parse Semantic Scholar API response")
                return None
        
        return None
        
    @track_api_usage("SemanticScholar")
    def download_paper(self, paper_id, store_dir='app/static/uploads/pdf_store'):
        """
        Download a paper from Semantic Scholar by ID.
        
        Args:
            paper_id: Semantic Scholar paper ID
            store_dir: Directory to store the PDF
            
        Returns:
            Tuple of (file_path, file_hash)
        """
        # Create store directory if it doesn't exist
        os.makedirs(store_dir, exist_ok=True)
        
        # Get paper details to find PDF URL
        paper_details = self.get_paper_details(paper_id)
        
        if not paper_details:
            if 'current_app' in globals():
                current_app.logger.error(f"Could not find paper with ID: {paper_id}")
            else:
                print(f"Could not find paper with ID: {paper_id}")
            return None, None
        
        # Extract PDF URL if available
        pdf_url = None
        if paper_details.get('openAccessPdf'):
            pdf_url = paper_details['openAccessPdf'].get('url')
        
        if not pdf_url:
            if 'current_app' in globals():
                current_app.logger.warning(f"No open access PDF available for paper ID: {paper_id}")
            else:
                print(f"No open access PDF available for paper ID: {paper_id}")
            return None, None
        
        # Download the PDF
        try:
            if 'current_app' in globals():
                current_app.logger.info(f"Downloading PDF from {pdf_url}")
            
            response = requests.get(pdf_url, stream=True)
            response.raise_for_status()
            
            # Calculate SHA-256 hash
            content = response.content
            file_hash = hashlib.sha256(content).hexdigest()
            
            # Save PDF with hash as filename
            file_path = os.path.join(store_dir, f"{file_hash}.pdf")
            
            with open(file_path, 'wb') as f:
                f.write(content)
            
            if 'current_app' in globals():
                current_app.logger.info(f"Successfully downloaded and saved PDF to {file_path}")
                
            return file_path, file_hash
            
        except requests.exceptions.RequestException as e:
            if 'current_app' in globals():
                current_app.logger.error(f"Failed to download PDF: {str(e)}")
            else:
                print(f"Failed to download PDF: {str(e)}")
            return None, None


# Imports moved to top of file

# Create quota manager for Semantic Scholar API
semantic_scholar_quota_manager = QuotaManager(api_name="SemanticScholar", daily_limit=5000)  # Adjust limit as needed

class CoreFetcher:
    """Class to interact with the CORE API for searching and downloading papers."""
    
    def __init__(self, api_key=None):
        """Initialize the CoreFetcher with API key.
        
        Args:
            api_key (str): CORE API key. If None, will try to get from environment.
        """
        if api_key is None:
            self.api_key = os.environ.get('CORE_API_KEY')
        else:
            self.api_key = api_key
        self.base_url = "https://api.core.ac.uk/v3"
        self.last_response_headers = None
        self.rate_limit_remaining = None
        self.rate_limit_reset = None
    
    @track_api_usage("CORE")
    def search(self, query, max_results=50, year_filter=None):
        """
        Search CORE for papers matching the query.
            
        Args:
            query (str): Search query string
            max_results (int): Maximum number of results to return
            year_filter (int, optional): Filter papers by publication year
            
        Returns:
            list: List of papers matching the search criteria
        """
        if not self.api_key:
            current_app.logger.error("CORE API key is required")
            return []
        
        # Check if we have sufficient quota before making request
        if not core_quota_manager.check_quota():
            current_app.logger.warning("CORE API daily quota exceeded")
            return []
        
        try:
            # Prepare query parameters
            params = {
                'q': query,
                'limit': max_results,
                'offset': 0
            }
            
            # Add year filter if provided
            if year_filter:
                params['year'] = year_filter
            
            # Make the request
            endpoint = f"{self.base_url}/search/works"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(endpoint, headers=headers, params=params)
            
            # Store response headers for quota monitoring
            self.last_response_headers = response.headers
            
            # Extract and store rate limit info
            if 'X-Rate-Limit-Remaining' in response.headers:
                self.rate_limit_remaining = response.headers['X-Rate-Limit-Remaining']
                current_app.logger.info(f"CORE API rate limit remaining: {self.rate_limit_remaining}")
                
            if 'X-Rate-Limit-Reset' in response.headers:
                self.rate_limit_reset = response.headers['X-Rate-Limit-Reset']
            
            # Increment quota usage counter
            core_quota_manager.increment_usage()
            
            response.raise_for_status()
            data = response.json()
            
            # Process results
            all_results = []
            priority_results = []  # Papers with downloadUrl
            normal_results = []    # Papers without downloadUrl but with acceptable fulltextStatus
            
            for work in data.get('results', []):
                # Check fulltextStatus - skip papers with problematic status
                fulltext_status = work.get('fulltextStatus')
                if fulltext_status in ['disabled', 'notFound', 'error']:
                    current_app.logger.debug(f"Skipping paper with fulltextStatus '{fulltext_status}'")
                    continue
                    
                # Extract authors
                authors = []
                for author in work.get('authors', []):
                    if isinstance(author, dict) and author.get('name'):
                        authors.append(author['name'])
                    elif isinstance(author, str):
                        authors.append(author)
                
                # Get PDF URL if available
                pdf_url = None
                for download in work.get('downloadUrls', []):
                    if download.get('type') == 'pdf':
                        pdf_url = download.get('url')
                        break
                
                paper_info = {
                    'id': work.get('id', ''),
                    'title': work.get('title', ''),
                    'abstract': work.get('abstract', ''),
                    'authors': authors,
                    'year': work.get('year'),
                    'url': work.get('sourceFulltextUrls', [''])[0] if work.get('sourceFulltextUrls') else '',
                    'pdf_url': pdf_url,
                    'source': 'core',
                    'fulltextStatus': fulltext_status
                }
                
                # Prioritize papers with downloadUrl
                if work.get('downloadUrl') or pdf_url:
                    priority_results.append(paper_info)
                else:
                    normal_results.append(paper_info)
            
            # Combine results with priority papers first
            all_results = priority_results + normal_results
            
            # Log the filtering results
            current_app.logger.info(f"CORE search: found {len(data.get('results', []))} papers, filtered to {len(all_results)} with priority on {len(priority_results)} having PDF URLs")
            
            return all_results
            
        except requests.exceptions.HTTPError as e:
            current_app.logger.error(f"Error searching CORE API: {str(e)}")
            # Specifically propagate rate limit errors (429) for proper error handling
            if e.response.status_code == 429:
                raise e
            return []
        except Exception as e:
            current_app.logger.error(f"Error searching CORE API: {str(e)}")
            return []

    @track_api_usage("CORE")
    def download_paper(self, paper_id, store_dir='app/static/uploads/pdf_store'):
        """
        Download a paper from CORE by ID.

        Args:
            paper_id: CORE paper ID
            store_dir: Directory to store the PDF

        Returns:
            Tuple of (file_path, file_hash)
        """
        if not self.api_key:
            current_app.logger.error("CORE API key is required")
            return None, None
            
        # Check if we have sufficient quota before making request
        if not core_quota_manager.check_quota():
            current_app.logger.warning("CORE API daily quota exceeded")
            return None, None

        # Ensure storage directory exists
        os.makedirs(store_dir, exist_ok=True)
        
        # Initialize variables that might be needed in exception handlers
        pdf_content = None
        file_path = None
        file_hash = None

        # Main try block for the entire download operation
        try:
            # First get paper details to find PDF URL
            endpoint = f"{self.base_url}/works/{paper_id}"
            headers = {"Authorization": f"Bearer {self.api_key}"}

            # Request paper details
            response = requests.get(endpoint, headers=headers)
            response.raise_for_status()

            # Store headers for quota monitoring
            self.last_response_headers = response.headers

            # Extract rate limit information if available
            if 'X-Rate-Limit-Remaining' in response.headers:
                self.rate_limit_remaining = response.headers['X-Rate-Limit-Remaining']
                current_app.logger.info(f"CORE API rate limit remaining: {self.rate_limit_remaining}")

            if 'X-Rate-Limit-Reset' in response.headers:
                self.rate_limit_reset = response.headers['X-Rate-Limit-Reset']
                
            # Increment quota usage counter
            core_quota_manager.increment_usage()

            paper_data = response.json()
            
            # Enhanced fulltext status check with more detailed logging
            fulltext_status = paper_data.get('fulltextStatus')
            if fulltext_status in ['disabled', 'notFound', 'error']:
                current_app.logger.warning(f"Paper ID {paper_id} has fulltext status '{fulltext_status}', skipping download")
                return None, None
            
            # Continue with download attempt even if fulltext_status is None
            if fulltext_status is None:
                current_app.logger.info(f"Paper ID {paper_id} has no fulltext status, will attempt to find PDF URL in other fields")
        
            # Log the fulltext status for debugging purposes
            current_app.logger.info(f"Paper ID {paper_id} fulltext status: {fulltext_status}")
        
            # Get and log paper metadata to help with debugging
            paper_title = paper_data.get('title', 'Unknown Title')
            paper_year = paper_data.get('year')
            paper_doi = paper_data.get('doi')
            current_app.logger.info(f"Processing paper: '{paper_title}' (Year: {paper_year}, DOI: {paper_doi})")
        
            # Track available PDF-related fields in paper_data for debugging
            pdf_fields = []
            if paper_data.get('downloadUrl'):
                pdf_fields.append('downloadUrl')
            if paper_data.get('downloadUrls'):
                pdf_fields.append('downloadUrls')
            if paper_data.get('sourceFulltextUrls'):
                pdf_fields.append('sourceFulltextUrls')
        
            current_app.logger.info(f"PDF fields available: {', '.join(pdf_fields) if pdf_fields else 'None'}")
                
            # Initialize collection for potential PDF URLs with their priority scores
            # Lower scores are higher priority
            pdf_url_candidates = []
        
            # ATTEMPT 1: Try to use the direct downloadUrl field (primary source, most reliable)
            if paper_data.get('downloadUrl'):
                url = paper_data.get('downloadUrl')
                if url and isinstance(url, str) and url.startswith('http'):
                    pdf_url_candidates.append((1, url, 'downloadUrl'))
                    current_app.logger.info(f"Found downloadUrl for paper ID: {paper_id}")
        
            # ATTEMPT 2: Check the downloadUrls array (legacy/compatibility method)
            for download in paper_data.get('downloadUrls', []):
                if download and isinstance(download, dict) and download.get('type') == 'pdf':
                    url = download.get('url')
                    if url and isinstance(url, str) and url.startswith('http'):
                        pdf_url_candidates.append((2, url, 'downloadUrls'))
                        current_app.logger.info(f"Found URL in downloadUrls array: {url[:60]}...")
        
            # ATTEMPT 3: Try direct download endpoint from CORE API
            direct_endpoint = f"{self.base_url}/works/{paper_id}/download?format=pdf"
            try:
                # Only perform HEAD request to check availability without downloading
                head_response = requests.head(direct_endpoint, headers=headers, timeout=5)
                if head_response.status_code == 200:
                    content_type = head_response.headers.get('Content-Type', '')
                    if 'pdf' in content_type.lower() or 'octet-stream' in content_type.lower():
                        pdf_url_candidates.append((3, direct_endpoint, 'direct_endpoint'))
                        current_app.logger.info(f"Direct endpoint available for paper ID: {paper_id}")
            except Exception as e:
                current_app.logger.warning(f"Direct endpoint check failed for paper ID {paper_id}: {str(e)}")
        
            # ATTEMPT 4: Check sourceFulltextUrls (may contain external repository links)
            if paper_data.get('sourceFulltextUrls'):
                for i, url in enumerate(paper_data.get('sourceFulltextUrls')):
                    if url and isinstance(url, str) and url.startswith('http'):
                        # Add with higher priority number (lower priority) based on position
                        pdf_url_candidates.append((4 + i * 0.1, url, f'sourceFulltextUrls[{i}]'))
                        current_app.logger.info(f"Found sourceFulltextUrl: {url[:60]}...")
        
            # ATTEMPT 5: Check links field if it exists
            for i, link in enumerate(paper_data.get('links', [])):
                if link and isinstance(link, str) and link.startswith('http'):
                    if '.pdf' in link.lower():
                        pdf_url_candidates.append((5 + i * 0.1, link, f'links[{i}]'))
                        current_app.logger.info(f"Found PDF link in links field: {link[:60]}...")
        
            # Sort by priority score (lowest first = highest priority)
            pdf_url_candidates.sort()
        
            # Log all found candidates
            current_app.logger.info(f"Found {len(pdf_url_candidates)} PDF URL candidates")
            for score, url, source in pdf_url_candidates[:5]:  # Log up to 5 candidates
                current_app.logger.info(f"  - [{score:.1f}] {source}: {url[:60]}...")
            
            # Select best URL (first in sorted list) or None if no candidates
            pdf_url = pdf_url_candidates[0][1] if pdf_url_candidates else None
        
            if pdf_url:
                current_app.logger.info(f"Selected best PDF URL: {pdf_url[:60]}...")
            else:
                current_app.logger.warning(f"No valid PDF URLs found for paper ID: {paper_id}")

            if not pdf_url:
                current_app.logger.warning(f"No PDF URL found for paper ID: {paper_id} after all attempts")
                return None, None
                
            # Enhanced PDF download with retries and better error handling
            max_retries = 2
            retry_delay = 1.0  # seconds
            user_agent = "ResHub Research Assistant/1.0"
            
            # Extend headers for download request
            download_headers = {
                "User-Agent": user_agent,
                "Accept": "application/pdf,application/octet-stream,*/*"
            }
            
            # Authentication headers if downloading from CORE API
            if pdf_url.startswith(self.base_url):
                download_headers["Authorization"] = f"Bearer {self.api_key}"
            
            current_app.logger.info(f"Downloading PDF from: {pdf_url[:60]}...")
            
            # Implement retry logic
            for attempt in range(max_retries + 1):
                try:
                    # Use a timeout to avoid hanging on slow connections
                    pdf_response = requests.get(
                        pdf_url, 
                        stream=True, 
                        headers=download_headers,
                        timeout=30
                    )
                    pdf_response.raise_for_status()
                    
                    # Verify content type is PDF or binary
                    content_type = pdf_response.headers.get('Content-Type', '').lower()
                    if not ('pdf' in content_type or 'octet-stream' in content_type or 'binary' in content_type):
                        current_app.logger.warning(
                            f"Unexpected content type: {content_type} for paper ID: {paper_id}. "
                            f"Will attempt to continue anyway."
                        )
                    
                    # Check if the content is too small to be a valid PDF (< 1000 bytes)
                    content_length = int(pdf_response.headers.get('Content-Length', 0))
                    if content_length > 0 and content_length < 1000:
                        current_app.logger.warning(
                            f"Suspiciously small PDF ({content_length} bytes) for paper ID: {paper_id}. "
                            f"Will attempt to continue anyway."
                        )
                    
                    # Calculate hash from PDF content
                    pdf_content = pdf_response.content
                    
                    # Double check we actually got some content
                    if not pdf_content or len(pdf_content) < 100:  # Arbitrary minimum for a valid PDF
                        current_app.logger.error(f"Empty or too small PDF content for paper ID: {paper_id}")
                        if attempt < max_retries:
                            current_app.logger.info(f"Retrying download (attempt {attempt+1} of {max_retries})")
                            time.sleep(retry_delay * (2**attempt))  # Exponential backoff
                            continue
                        return None, None
                    
                    file_hash = hashlib.sha256(pdf_content).hexdigest()
                    
                    # Save to file
                    file_path = os.path.join(store_dir, f"{file_hash}.pdf")
                    with open(file_path, 'wb') as f:
                        f.write(pdf_content)
                    
                    current_app.logger.info(f"Successfully downloaded PDF for paper ID: {paper_id} ({len(pdf_content)} bytes)")
                    break  # Success, exit retry loop
                    
                except requests.exceptions.HTTPError as http_err:
                    if attempt < max_retries:
                        current_app.logger.warning(
                            f"HTTP error ({http_err.response.status_code}) downloading PDF: {str(http_err)}. "
                            f"Retrying ({attempt+1}/{max_retries})..."
                        )
                        time.sleep(retry_delay * (2**attempt))  # Exponential backoff
                    else:
                        raise  # Re-raise to be caught by the outer exception handler
                        
                except (requests.exceptions.RequestException, IOError) as err:
                    if attempt < max_retries:
                        current_app.logger.warning(
                            f"Error downloading PDF: {str(err)}. Retrying ({attempt+1}/{max_retries})..."
                        )
                        time.sleep(retry_delay * (2**attempt))  # Exponential backoff
                    else:
                        current_app.logger.error(f"Failed to download PDF after {max_retries} retries: {str(err)}")
                        return None, None
            
            # If we've gotten here, we successfully downloaded the PDF
            # Calculate hash from PDF content
            file_hash = hashlib.sha256(pdf_content).hexdigest()
            
            # Save to file
            file_path = os.path.join(store_dir, f"{file_hash}.pdf")
            with open(file_path, 'wb') as f:
                f.write(pdf_content)
            
            current_app.logger.info(f"Successfully downloaded PDF for paper ID: {paper_id} ({len(pdf_content)} bytes)")
            # Done with retry loop
            
            # Return the successful download results
            return file_path, file_hash
            
        # Properly aligned exception handlers for the main try block
        except requests.exceptions.HTTPError as e:
            # Enhanced HTTP error handling with specific status code handling
            status_code = e.response.status_code if hasattr(e, 'response') else 'unknown'
            
            if hasattr(e, 'response') and e.response.status_code == 429:
                # Rate limiting - propagate this for proper handling upstream
                current_app.logger.error(f"CORE API rate limit exceeded: {str(e)}")
                raise e
            elif hasattr(e, 'response') and e.response.status_code == 404:
                current_app.logger.error(f"PDF not found (404) for paper ID {paper_id}: {str(e)}")
            elif hasattr(e, 'response') and e.response.status_code >= 500:
                current_app.logger.error(f"CORE API server error ({status_code}) for paper ID {paper_id}: {str(e)}")
            else:
                current_app.logger.error(f"HTTP error ({status_code}) downloading paper from CORE: {str(e)}")
            return None, None
            
        except requests.exceptions.Timeout as e:
            current_app.logger.error(f"Timeout error downloading PDF for paper ID {paper_id}: {str(e)}")
            return None, None
            
        except requests.exceptions.ConnectionError as e:
            current_app.logger.error(f"Connection error to CORE API for paper ID {paper_id}: {str(e)}")
            return None, None
            
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Failed to download paper from CORE for paper ID {paper_id}: {str(e)}")
            return None, None
            
        except json.JSONDecodeError as e:
            current_app.logger.error(f"Failed to parse CORE API response for paper ID {paper_id}: {str(e)}")
            return None, None
            
        except IOError as e:
            current_app.logger.error(f"I/O error saving PDF for paper ID {paper_id}: {str(e)}")
            return None, None
            
        except Exception as e:
            current_app.logger.error(f"Unexpected error downloading paper from CORE for paper ID {paper_id}: {str(e)}")
            return None, None
            
        # Note: The function already returns within the try block or in exception handlers
