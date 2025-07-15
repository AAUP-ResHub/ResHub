===========================================================================
RESHUB CHATBOT PIPELINE DOCUMENTATION
===========================================================================

Table of Contents:
-----------------
1. High-Level Overview
2. Sequence Diagram
3. Component Inventory
   3.1. Frontend
   3.2. Backend Routes
   3.3. Vector Layer
   3.4. Data Ingestion
   3.5. Databases
   3.6. Docker Services & Volumes
4. Critical Environment Variables & Secrets
5. Logging & Monitoring
6. Known Failure Modes & Mitigations
7. End-to-End Request Example
8. Change & Deploy Checklist
9. Glossary

===========================================================================
1. HIGH-LEVEL OVERVIEW
===========================================================================

The ResHub chatbot pipeline provides a comprehensive research assistance system that enables users to query academic papers and knowledge bases through natural language. The pipeline ingests PDF research papers, extracts and processes text content, generates vector embeddings, and stores them in a Qdrant vector database for semantic search. When a user submits a query, the system converts it to embeddings, performs similarity searches against the vector store, retrieves relevant document chunks, and formats them into a coherent response with proper citations. The system incorporates fallback mechanisms at multiple levels to ensure robustness, including simulated embeddings when OpenAI services are unavailable and an in-memory store when Qdrant connectivity fails.


===========================================================================
2. SEQUENCE DIAGRAM
===========================================================================

User -> Frontend: Submits query through web interface
Frontend -> Backend: HTTP POST to /chatbot/api/chat or /chatbot/api/chat/test
Backend -> VectorStore: Generate embeddings for query text
VectorStore -> OpenAI API: Request embeddings (with fallback)
VectorStore <-- OpenAI API: Return embeddings or error
  alt: OpenAI API fails
    VectorStore -> Simulation: Generate deterministic embeddings from query hash
  end
Backend <-- VectorStore: Return embeddings
Backend -> VectorStore: Search for relevant documents
VectorStore -> Qdrant: Query collection using embeddings
  alt: Qdrant client available
    VectorStore -> Qdrant: Try search method 1 (query_vector)
      alt: Method 1 fails
        VectorStore -> Qdrant: Try search method 2 (direct vector)
          alt: Method 2 fails
            VectorStore -> Qdrant: Try search method 3 (with payload filter)
          end
      end
    VectorStore <-- Qdrant: Return search results
  else: Qdrant unavailable or all methods fail
    VectorStore -> Memory Store: Fallback to in-memory search
    VectorStore <-- Memory Store: Return search results
  end
Backend <-- VectorStore: Return document chunks
Backend -> Response Formatter: Format chunks into coherent response
Frontend <-- Backend: Return JSON response
User <-- Frontend: Display formatted answer with citations


===========================================================================
3. COMPONENT INVENTORY
===========================================================================

3.1. Frontend
-------------

FILES:
- app/templates/chatbot.html - Main chatbot interface template
- app/static/js/chatbot.js - Client-side chatbot functionality
- app/static/css/chatbot.css - Chatbot-specific styles

KEY FUNCTIONS:
- initChatbot() - Initializes chatbot UI and event handlers
- submitQuery(query, sessionId) - Sends user query to backend API
- displayResponse(response) - Renders formatted responses with citations
- handleError(error) - Displays user-friendly error messages
- showTypingIndicator()/hideTypingIndicator() - Manages loading state

EVENT FLOW:
1. User enters query in input field and submits (Enter or button click)
2. Frontend validates input, shows loading state
3. AJAX request to /chatbot/api/chat endpoint
4. Response processing (citations, formatting)
5. Display in chat window with proper attribution
6. Session management via browser localStorage

3.2. Backend Routes
------------------

FILES:
- app/chatbot/routes.py - API endpoints and route handlers
- app/chatbot/__init__.py - Blueprint registration

KEY ENDPOINTS:
1. /chatbot/api/chat
   - Method: POST
   - Parameters: prompt (text), session_id (optional), limit (optional)
   - Returns: JSON with answer, citations, chat_id, latency_ms
   - Description: Main production endpoint for chatbot queries

2. /chatbot/api/chat/test
   - Method: POST
   - Parameters: prompt (text), debug (boolean), session_id (optional)
   - Returns: Same as /chat plus extras field with debugging info
   - Description: Testing endpoint with additional debug information

3. /chatbot/api/upload
   - Method: POST
   - Parameters: file (PDF), metadata (JSON)
   - Returns: JSON with status, document_id
   - Description: Document ingestion endpoint

4. /chatbot/api/health
   - Method: GET
   - Returns: Status of vector store, connection health
   - Description: Health check endpoint for monitoring

3.3. Vector Layer
----------------

FILES:
- app/chatbot/vector_store.py - Core vector database functionality
- app/chatbot/embedding.py - Embedding generation utilities

QDRANT CONFIGURATION:
- Collection Name: reshub_papers
- Vector Size: 1536 (OpenAI embedding dimension)
- Distance Metric: Cosine
- Vector Fields:
  * dense: Dense vector representation (1536 dimensions)
  * sparse_indices: Sparse vector indices (optional)
  * sparse_values: Sparse vector values (optional)

HEALTH CHECK LOGIC:
- HTTP connection test to Qdrant server
- Collection existence verification
- Status check (green/yellow/red)
- Points count validation

SEARCH METHODS:
1. Primary: client.search with query_vector parameter
2. Fallback 1: search with direct vector parameter
3. Fallback 2: search with payload filter
4. Final Fallback: In-memory search using simulated embeddings

3.4. Data Ingestion
------------------

FILES:
- app/chatbot/ingest.py - Document processing pipeline
- app/chatbot/pdf_utils.py - PDF extraction utilities

INGESTION WORKFLOW:
1. Document Upload: PDF file submitted via API
2. Text Extraction:
   - PyPDF2 for content extraction
   - Layout analysis for proper text flow
   - OCR fallback for scanned documents
3. Chunking:
   - Text segmented into semantic chunks (~200-300 words)
   - Paragraph and section boundaries preserved
   - Overlap between chunks (30-50 words)
4. Metadata Extraction:
   - Title, authors, publication date, citations
   - Keywords and abstract when available
5. Embedding Generation:
   - OpenAI API for embedding vectors
   - Each chunk embedded separately
   - Both dense and sparse vectors generated
6. Vector Storage:
   - Chunks and metadata stored in Qdrant
   - PostgreSQL reference records created
7. Verification:
   - Search test to validate retrievability
   - Error reporting for failed documents

3.5. Databases
-------------

POSTGRESQL:
- Tables:
  * users - User authentication and profiles
  * documents - Metadata about ingested documents
  * document_chunks - References to vector chunks
  * chat_sessions - User conversation history
  * chat_messages - Individual Q&A pairs
  * chat_feedback - User ratings and feedback

ORM MODELS:
- app/models.py - SQLAlchemy models
  * User - Authentication details, permissions
  * Document - Paper metadata and references
  * DocumentChunk - Text segment references
  * ChatSession - Conversation tracking
  * ChatMessage - Individual exchanges
  * ChatFeedback - Quality metrics

RELATIONSHIPS:
- User 1:N ChatSession
- ChatSession 1:N ChatMessage
- Document 1:N DocumentChunk
- ChatMessage N:M DocumentChunk (citations)

QDRANT VECTOR DB:
- Collection: reshub_papers
- Points: Document chunks with embeddings
- Payload: Text, metadata, citations, source references

3.6. Docker Services & Volumes
-----------------------------

SERVICES:
1. web - Flask application
   - Image: Custom built from Dockerfile
   - Ports: 5000:5000
   - Dependencies: db, qdrant
   - Health Check: /health endpoint

2. db - PostgreSQL database
   - Image: postgres:13
   - Ports: 5432:5432
   - Volumes: postgres_data
   - Health Check: pg_isready

3. qdrant - Vector database
   - Image: qdrant/qdrant:latest
   - Ports: 6333:6333 (API), 6334:6334 (web UI)
   - Volumes: qdrant_data
   - Health Check: /healthz endpoint
   - Resources: 1-2GB memory allocation

4. n8n - Workflow automation
   - Image: n8nio/n8n:latest
   - Ports: 5678:5678
   - Volumes: n8n_data
   - Dependencies: web
   - Health Check: /healthz endpoint

VOLUMES:
- postgres_data - Database persistence
- qdrant_data - Vector database storage
- n8n_data - Workflow configurations
- storage - Uploaded files and generated assets

===========================================================================
4. CRITICAL ENVIRONMENT VARIABLES & SECRETS
===========================================================================

API KEYS:
- OPENAI_API_KEY - For embedding generation and optional AI completion
- SERPAPI_API_KEY - For web search integration (optional)

DATABASE CONFIGURATION:
- DATABASE_URL - PostgreSQL connection string
- SQLALCHEMY_TRACK_MODIFICATIONS - SQL tracking flag

VECTOR DATABASE:
- VECTOR_DB_HOST - Qdrant server hostname
- VECTOR_DB_PORT - Qdrant server port
- VECTOR_DB_API_KEY - Qdrant API key (if authentication enabled)
- VECTOR_DB_COLLECTION - Collection name (default: reshub_papers)

APPLICATION SETTINGS:
- FLASK_ENV - Environment setting (development/production)
- FLASK_APP - Application entrypoint
- SECRET_KEY - Flask application secret
- LOG_LEVEL - Logging verbosity
- UPLOAD_FOLDER - Path for file uploads
- MAX_CONTENT_LENGTH - Maximum upload file size

AUTHENTICATION:
- JWT_SECRET_KEY - JWT token secret
- JWT_ACCESS_TOKEN_EXPIRES - Token lifetime


===========================================================================
5. LOGGING & MONITORING
===========================================================================

LOG PATHS:
- Application Logs: /app/logs/app.log (container) or ./logs/app.log (local)
- Error Logs: /app/logs/error.log
- Access Logs: via gunicorn to stdout/stderr (captured by Docker)

LOG LEVELS:
- Production: WARNING and above (errors, critical issues)
- Development: INFO and above (includes API calls, search operations)
- Debug: DEBUG level (includes query details, embedding generation)

STRUCTURED LOGGING:
- Format: [Timestamp] - [Module] - [Level] - [RequestID] [Message]
- Request IDs: Unique per request, passed through pipeline for tracing

METRICS:
- Endpoint Response Times: Tracked via before_request/after_request
- Search Latency: Measured and included in API responses
- Error Rates: Logged and monitored
- Vector Store Health: Status checks every 10 minutes

HEALTH CHECKS:
- /health - Overall application health
- /chatbot/api/health - Chatbot subsystem status
- Database Connectivity: Periodic ping check
- Qdrant Connectivity: Status of vector database
- Document Count: Number of ingested documents

ALERTING:
- Critical Errors: Logged with ERROR level
- Service Degradation: WARNING level with specific codes
- Health Check Failures: Triggers alert after 3 consecutive failures


===========================================================================
6. KNOWN FAILURE MODES & MITIGATIONS
===========================================================================

1. OpenAI API Unavailable
   - Failure Mode: Embedding generation fails due to API errors or rate limits
   - Symptoms: Embedding errors in logs, slow responses
   - Mitigation: Fallback to deterministic simulated embeddings based on text hash

2. Qdrant Connection Failures
   - Failure Mode: Cannot connect to vector database
   - Symptoms: Connection timeouts, HTTP 5xx errors
   - Mitigation: Fallback to in-memory search with test documents

3. Malformed Query Embeddings
   - Failure Mode: Generated embeddings are None or invalid format
   - Symptoms: TypeError exceptions, "NoneType is not subscriptable"
   - Mitigation: Robust checking and conversion of embedding formats

4. PDF Extraction Failures
   - Failure Mode: Cannot extract text from PDF documents
   - Symptoms: Empty chunks, low-quality search results
   - Mitigation: OCR fallback, document quality warnings

5. Database Connection Issues
   - Failure Mode: PostgreSQL connection errors
   - Symptoms: 500 errors on API calls requiring database
   - Mitigation: Connection pooling, automatic reconnection

6. Search Returns No Results
   - Failure Mode: No relevant documents found
   - Symptoms: Empty results, generic responses
   - Mitigation: Fallback content, suggested queries, year filter adjustment

7. Memory Exhaustion
   - Failure Mode: Large documents consume too much memory
   - Symptoms: Container OOM errors, application crashes
   - Mitigation: Document size limits, chunking improvements

8. Rate Limiting
   - Failure Mode: Too many requests from a single user/IP
   - Symptoms: 429 Too Many Requests responses
   - Mitigation: Redis-based rate limiting, graceful degradation


===========================================================================
7. END-TO-END REQUEST EXAMPLE
===========================================================================

DOCUMENT INGESTION:

```
# Upload a research paper
curl -X POST http://localhost:5000/chatbot/api/upload \
  -F "file=@example_paper.pdf" \
  -F "metadata={\"title\":\"Example Research Paper\",\"authors\":[\"John Doe\",\"Jane Smith\"],\"year\":2023,\"keywords\":[\"machine learning\",\"natural language processing\"]}"
```

RESPONSE:
```json
{
  "status": "success",
  "document_id": "doc_c7a42f9e",
  "chunks_processed": 14,
  "message": "Document successfully processed and indexed"
}
```

CHATBOT QUERY:

```
# Ask a question to the chatbot
curl -X POST http://localhost:5000/chatbot/api/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What are the key findings in recent NLP research?", "session_id":"user_session_123"}'
```

RESPONSE:
```json
{
  "answer": "Recent NLP research has made several key advances: (1) Large language models have shown emergent capabilities when scaled to sufficient size, (2) Transformer architectures continue to dominate the field with improvements in efficiency and context length, (3) Retrieval-augmented generation helps ground models in factual knowledge, reducing hallucinations.",
  "chat_id": 145,
  "citations": [
    {
      "text": "Example Research Paper (Doe & Smith, 2023)",
      "document_id": "doc_c7a42f9e",
      "chunk_id": "chunk_7b23a1d9"
    }
  ],
  "latency_ms": 324,
  "session_id": "user_session_123"
}
```

DEBUG TESTING:

```
# Test endpoint with debug info
curl -X POST http://localhost:5000/chatbot/api/chat/test \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What are the key findings in recent NLP research?", "debug":true}'
```

DEBUG RESPONSE:
```json
{
  "answer": "Recent NLP research has made several key advances: (1) Large language models have shown emergent capabilities when scaled to sufficient size, (2) Transformer architectures continue to dominate the field with improvements in efficiency and context length, (3) Retrieval-augmented generation helps ground models in factual knowledge, reducing hallucinations.",
  "chat_id": 146,
  "citations": [...],
  "latency_ms": 347,
  "session_id": "test_session_89a1b2c3",
  "test_mode": true,
  "extras": {
    "vector_search_time_ms": 125,
    "chunks_retrieved": 3,
    "qdrant_status": "connected",
    "embedding_source": "openai",
    "search_method": "query_vector"
  }
}
```


===========================================================================
8. CHANGE & DEPLOY CHECKLIST
===========================================================================

LOCAL DEVELOPMENT:
1. Clone repository and install dependencies
   - `git clone https://github.com/youraccount/reshub.git`
   - `pip install -r requirements.txt`
   - Set up .env file with required variables

2. Run tests before making changes
   - `pytest -xvs tests/`
   - `pytest -xvs tests/chatbot/` (chatbot-specific)

MAKING CHANGES:
1. Vector store modifications:
   - Update vector_store.py for search changes
   - Test with local Qdrant instance
   - Verify fallback mechanisms work

2. Frontend changes:
   - Modify static/js/chatbot.js and templates
   - Test with local Flask server

3. API changes:
   - Update routes.py for endpoint modifications
   - Document any parameter changes

BUILD & DEPLOYMENT:
1. Rebuild Docker image
   - `docker compose build web`

2. Restart services
   - For code-only changes: `docker compose restart web`
   - For dependency changes: `docker compose up -d --force-recreate web`

3. Verify deployment
   - Check logs: `docker compose logs -f web`
   - Test health endpoint: http://localhost:5000/health
   - Test chatbot API: http://localhost:5000/chatbot/api/health

SMOKE TESTING:
1. Basic functionality
   - Upload a test document
   - Query related to the document
   - Verify correct citations

2. Edge cases
   - Test with malformed queries
   - Test with non-existent documents
   - Test with OpenAI API disabled

ROLLBACK PROCEDURE:
1. If deployment fails
   - `docker compose stop web`
   - `docker tag reshub-web:previous reshub-web:latest`
   - `docker compose up -d web`

2. Database rollback
   - Restore from latest backup if schema changed
   - `docker compose exec db pg_restore -U postgres -d reshub /backups/latest.dump`


===========================================================================
9. GLOSSARY
===========================================================================

AI - Artificial Intelligence
API - Application Programming Interface
CLIP - Contrastive Language-Image Pre-Training (for multimodal embeddings)
DB - Database
DVC - Data Version Control (for large file management)
Embedding - Vector representation of text or other data
FAISS - Facebook AI Similarity Search (vector indexing library)
GPU - Graphics Processing Unit (for acceleration)
JWT - JSON Web Token (for authentication)
LLM - Large Language Model
NLP - Natural Language Processing
OCR - Optical Character Recognition
ORM - Object-Relational Mapping
PDF - Portable Document Format
RAG - Retrieval Augmented Generation
RDBMS - Relational Database Management System
REST - Representational State Transfer
SQL - Structured Query Language
UX - User Experience
VDB - Vector Database
Qdrant - Vector Database used in ResHub (from "quadrant")
SQL - Structured Query Language
API - Application Programming Interface

