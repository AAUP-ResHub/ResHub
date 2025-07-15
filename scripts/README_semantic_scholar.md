# Semantic Scholar Ingestion Script

## Overview
The `ingest_semantic_scholar.py` script implements a complete pipeline for ingesting academic papers from Semantic Scholar into the ResHub system. It handles:

- Paper search with comprehensive filtering options
- PDF downloading and validation
- Text extraction and chunking
- Vector store indexing
- Detailed logging and statistics

## Prerequisites

1. A valid Semantic Scholar API key set in your `.env` file:
   ```
   SEMANTIC_SCHOLAR_API_KEY=your_api_key_here
   ```

2. Flask application setup with proper configuration

## Usage

```bash
python scripts/ingest_semantic_scholar.py --query "machine learning" --max-results 20 --year-filter "last 5 years"
```

### Command Line Arguments

#### Search Parameters
- `--query` (required): Search terms for finding papers
- `--max-results`: Maximum number of papers to fetch (default: 10)
- `--year-filter`: Filter by publication year (e.g., "last 5 years", "2020-2023", "2022")
- `--open-access-only`: Only fetch papers with open access PDFs (default: True)
- `--min-citation-count`: Minimum citation count for papers
- `--venue`: Filter by publication venue/journal
- `--publication-types`: Comma-separated list of publication types (e.g., "Journal,Conference")

#### Processing Parameters
- `--batch-size`: Number of papers to process in each batch (default: 2)
- `--delay`: Delay in seconds between processing batches (default: 3.0)
- `--max-papers`: Maximum number of papers to process

#### Output Options
- `--stats-file`: Output file for detailed statistics (JSON format)
- `--verbose`, `-v`: Increase verbosity (can be used multiple times)

## Examples

### Basic Search
```bash
python scripts/ingest_semantic_scholar.py --query "transformer models"
```

### Advanced Filtering
```bash
python scripts/ingest_semantic_scholar.py --query "machine learning healthcare" --year-filter "last 3 years" --min-citation-count 50 --venue "Nature" --publication-types "Journal"
```

### Custom Batch Processing
```bash
python scripts/ingest_semantic_scholar.py --query "climate change" --max-results 30 --batch-size 3 --delay 5 --max-papers 15
```

### Detailed Statistics
```bash
python scripts/ingest_semantic_scholar.py --query "quantum computing" --stats-file "quantum_stats.json" --verbose
```

## Output

The script provides:
- Real-time progress logs
- A summary of results upon completion
- Optional detailed statistics in JSON format

## Troubleshooting

If you encounter issues:

1. Verify your Semantic Scholar API key is correct and has sufficient quota
2. Check your Flask application configuration
3. Review the log file created in the current directory
4. Increase verbosity with `-v` or `-vv` for more detailed logs
