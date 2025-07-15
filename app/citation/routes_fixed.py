from datetime import datetime
from io import StringIO, BytesIO
import numpy as np
from flask import render_template, redirect, url_for, flash, request, jsonify, send_file, abort, current_app
from flask_login import login_required, current_user
from sentence_transformers import SentenceTransformer
from typing import Dict, List, Any, Tuple
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from app.citation import citation_bp
from app.models import User, RegisteredUser, PremiumUser, ResearchPaper, Citation, CitationStyle
from app.extensions import db

import pybtex.database
from pybtex.style.formatting.unsrt import Style as UnsrtStyle
from pybtex.backends.html import Backend as HtmlBackend
from pybtex.style.template import field, join, words, optional, sentence

# Dictionary to map citation styles to their formatters
CITATION_FORMATTERS = {}

# Initialize sentence transformer model with caching
_model = None
_journal_embeddings_cache = {}

def get_model():
    """Lazy load the sentence transformer model"""
    global _model
    if _model is None:
        try:
            print("Loading sentence transformer model 'all-MiniLM-L6-v2'...")
            _model = SentenceTransformer('all-MiniLM-L6-v2')
            print(f"Model loaded successfully: {type(_model).__name__}")
        except Exception as e:
            print(f"ERROR LOADING MODEL: {str(e)}")
            import traceback
            traceback.print_exc()
            _model = None
    return _model

def get_text_embedding(text: str) -> np.ndarray:
    """Get embedding for a text string"""
    if not text or not isinstance(text, str) or len(text.strip()) == 0:
        print("WARNING: Empty or invalid text provided for embedding")
        return None
        
    model = get_model()
    if model is None:
        print("WARNING: Model not available for embedding")
        return None
    
    try:
        # Truncate very long texts to avoid memory issues
        if len(text) > 10000:
            print(f"Text too long ({len(text)} chars), truncating to 10000 chars")
            text = text[:10000]
            
        print(f"Encoding text of length {len(text)}")
        embedding = model.encode(text, convert_to_numpy=True)
        print(f"Successfully created embedding with shape {embedding.shape}")
        return embedding
    except Exception as e:
        print(f"ERROR encoding text: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def get_journal_embedding(journal: Dict[str, Any]) -> np.ndarray:
    """Get embedding for a journal, with caching"""
    global _journal_embeddings_cache
    journal_id = journal.get('id', journal.get('name', ''))
    
    # Return cached embedding if available
    if journal_id in _journal_embeddings_cache:
        return _journal_embeddings_cache[journal_id]
    
    # Prepare text for embedding
    text = f"{journal.get('name', '')} {journal.get('field', '')} {journal.get('scope_description', '')}"
    
    # Get embedding
    embedding = get_text_embedding(text)
    
    # Cache the embedding
    if embedding is not None:
        _journal_embeddings_cache[journal_id] = embedding
        
    return embedding

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors"""
    if a is None or b is None:
        return 0.0
        
    # Normalize the vectors
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    
    # Handle zero vectors
    if a_norm == 0 or b_norm == 0:
        return 0.0
        
    # Calculate cosine similarity
    return np.dot(a, b) / (a_norm * b_norm)

def format_bibtex_as_apa(bibtex_string):
    """
    Format a BibTeX entry in APA style
    """
    bib_data = pybtex.database.parse_string(bibtex_string, 'bibtex')
    
    # Custom formatting for APA style
    # This is simplified; a complete implementation would need more formatting rules
    entries = list(bib_data.entries.items())
    if not entries:
        return "Invalid BibTeX data"
    
    key, entry = entries[0]
    
    # Extract author information
    authors = []
    if 'author' in entry.persons:
        for person in entry.persons['author']:
            last_name = ' '.join(person.last_names)
            initials = ''.join(p[0] + '.' for p in person.first_names + person.middle_names)
            authors.append(f"{last_name}, {initials}")
    
    author_text = ", ".join(authors[:-1])
    if len(authors) > 1:
        author_text += f", & {authors[-1]}"
    elif authors:
        author_text = authors[0]
    
    # Get year
    year = entry.fields.get('year', 'n.d.')
    
    # Get title
    title = entry.fields.get('title', 'Untitled')
    
    # Get source info (journal, publisher, etc.)
    journal = entry.fields.get('journal', '')
    publisher = entry.fields.get('publisher', '')
    
    # For APA style
    citation = f"{author_text} ({year}). {title}."
    
    if journal:
        volume = entry.fields.get('volume', '')
        number = entry.fields.get('number', '')
        pages = entry.fields.get('pages', '')
        
        citation += f" {journal}"
        if volume:
            citation += f", {volume}"
            if number:
                citation += f"({number})"
        if pages:
            citation += f", {pages}"
        citation += "."
    elif publisher:
        citation += f" {publisher}."
    
    return citation

def format_bibtex_as_mla(bibtex_string):
    """
    Format a BibTeX entry in MLA style
    """
    bib_data = pybtex.database.parse_string(bibtex_string, 'bibtex')
    
    entries = list(bib_data.entries.items())
    if not entries:
        return "Invalid BibTeX data"
    
    key, entry = entries[0]
    
    # Extract author information for MLA
    authors = []
    if 'author' in entry.persons:
        for person in entry.persons['author']:
            last_name = ' '.join(person.last_names)
            first_name = ' '.join(person.first_names)
            middle_names = ' '.join(person.middle_names)
            if middle_names:
                authors.append(f"{last_name}, {first_name} {middle_names}")
            else:
                authors.append(f"{last_name}, {first_name}")
    
    # Format authors for MLA
    if len(authors) == 1:
        author_text = authors[0]
    elif len(authors) == 2:
        author_text = f"{authors[0]} and {authors[1].split(', ')[1]} {authors[1].split(', ')[0]}"
    elif len(authors) > 2:
        author_text = f"{authors[0]}, et al"
    else:
        author_text = ""
        
    # Get title
    title = entry.fields.get('title', 'Untitled')
    
    # Get container (journal, book, etc.)
    journal = entry.fields.get('journal', '')
    
    # Get other metadata
    year = entry.fields.get('year', '')
    publisher = entry.fields.get('publisher', '')
    volume = entry.fields.get('volume', '')
    number = entry.fields.get('number', '')
    pages = entry.fields.get('pages', '')
    
    # Build MLA citation
    citation = f"{author_text}. \"{title}.\""
    
    if journal:
        citation += f" {journal}"
        if volume:
            citation += f", vol. {volume}"
        if number:
            citation += f", no. {number}"
        if year:
            citation += f", {year}"
        if pages:
            citation += f", pp. {pages}"
    elif publisher:
        citation += f" {publisher}"
        if year:
            citation += f", {year}"
    
    citation += "."
    
    return citation

def format_bibtex_as_ieee(bibtex_string):
    """
    Format a BibTeX entry in IEEE style
    """
    bib_data = pybtex.database.parse_string(bibtex_string, 'bibtex')
    
    entries = list(bib_data.entries.items())
    if not entries:
        return "Invalid BibTeX data"
    
    key, entry = entries[0]
    
    # Extract author information for IEEE
    authors = []
    if 'author' in entry.persons:
        for person in entry.persons['author']:
            first_initials = ''.join(p[0] + '.' for p in person.first_names + person.middle_names)
            last_name = ' '.join(person.last_names)
            authors.append(f"{first_initials} {last_name}")
    
    # Format authors for IEEE
    author_text = ", ".join(authors)
    
    # Get title
    title = entry.fields.get('title', 'Untitled')
    
    # Get journal/publisher info
    journal = entry.fields.get('journal', '')
    publisher = entry.fields.get('publisher', '')
    
    # Get other metadata
    year = entry.fields.get('year', '')
    volume = entry.fields.get('volume', '')
    number = entry.fields.get('number', '')
    pages = entry.fields.get('pages', '')
    
    # Build IEEE citation
    citation = f"{author_text}, \"{title}\","
    
    if journal:
        citation += f" {journal}"
        if volume:
            citation += f", vol. {volume}"
        if number:
            citation += f", no. {number}"
        if pages:
            citation += f", pp. {pages}"
        if year:
            citation += f", {year}"
    elif publisher:
        citation += f" {publisher}"
        if year:
            citation += f", {year}"
    
    citation += "."
    
    return citation

def generate_bibtex_from_paper(paper):
    """
    Generate BibTeX entry from a ResearchPaper object, using provided metadata or safe defaults.
    """
    if not paper:
        current_app.logger.warning("generate_bibtex_from_paper called with None object")
        raise ValueError("No paper provided")
        
    entry_key = f"paper{paper.paper_id}"
    current_year = datetime.utcnow().year
    
    # Use citation metadata fields if available, or fallback to defaults
    
    # Handle authors - use the authors field if available, otherwise try owner name
    if paper.authors:
        # Use provided author list
        author_list = paper.authors
    else:
        # Fallback to owner info
        author = "Unknown Author"
        try:
            if hasattr(paper, 'owner') and paper.owner and hasattr(paper.owner, 'user') and paper.owner.user:
                firstname = paper.owner.first_name or ''
                lastname = paper.owner.last_name or paper.owner.user.username
                if firstname or lastname:
                    author = f"{lastname}, {firstname}" if firstname else lastname
                else:
                    author = paper.owner.user.username
        except Exception as e:
            current_app.logger.warning(f"Error getting author name for paper {paper.paper_id}: {e}")
            # Continue with default author name
        author_list = author
    
    # Create a new bibliography data object
    bib_data = pybtex.database.BibliographyData()
    
    # Get publication year or default to the current year
    year = paper.publication_year or (str(paper.publish_date.year if paper.publish_date else current_year))
    
    # Create the article entry with available metadata
    fields = [
        ('title', paper.title or "Untitled Paper"),
        ('year', year),
        ('journal', paper.journal or "Research Hub Journal"),
    ]
    
    # Add optional fields if available
    if paper.volume:
        fields.append(('volume', paper.volume))
    
    if paper.issue:
        fields.append(('number', paper.issue))
    
    if paper.pages:
        fields.append(('pages', paper.pages))
    
    if paper.publisher:
        fields.append(('publisher', paper.publisher))
    
    if paper.doi:
        fields.append(('doi', paper.doi))
    
    article_entry = pybtex.database.Entry('article', fields)
    
    # Add authors - split by comma if multiple authors
    authors_list = [author.strip() for author in author_list.split(',')] if isinstance(author_list, str) else [author_list]
    article_entry.persons['author'] = [pybtex.database.Person(author) for author in authors_list if author]
    
    # Add to bibliography
    bib_data.add_entry(entry_key, article_entry)
    
    # Convert to BibTeX string
    return bib_data.to_string('bibtex')

@citation_bp.route('/generate/<int:paper_id>/<style_name>')
@login_required
def generate(paper_id, style_name):
    """Generate a citation for a paper in the specified style"""
    try:
        # Convert style_name string to CitationStyle enum
        style = getattr(CitationStyle, style_name.upper())
        
        # Check if paper exists
        paper = ResearchPaper.query.get_or_404(paper_id)
        
        # Check if citation already exists
        citation = Citation.query.filter_by(paper_id=paper_id, style=style).first()
        
        if not citation:
            # Generate BibTeX if citation doesn't exist
            bibtex_string = generate_bibtex_from_paper(paper)
            
            # Create new citation
            citation = Citation(
                paper_id=paper_id,
                style=style,
                bibtex_string=bibtex_string
            )
            
            db.session.add(citation)
            db.session.commit()
        
        # Format the citation according to style
        if style == CitationStyle.APA:
            formatted_citation = format_bibtex_as_apa(citation.bibtex_string)
        elif style == CitationStyle.MLA:
            formatted_citation = format_bibtex_as_mla(citation.bibtex_string)
        elif style == CitationStyle.IEEE:
            formatted_citation = format_bibtex_as_ieee(citation.bibtex_string)
        
        return jsonify({
            'citation_id': citation.id,
            'formatted_citation': formatted_citation,
            'style': style.value
        })
        
    except (AttributeError, ValueError):
        return jsonify({'error': 'Invalid citation style'}), 400
    except Exception as e:
        current_app.logger.error(f"Citation generation error: {str(e)}")
        return jsonify({'error': 'Failed to generate citation'}), 500

@citation_bp.route('/export/<int:citation_id>', methods=['POST'])
@login_required
def export_citation(citation_id):
    try:
        # Get the citation
        citation = Citation.query.get_or_404(citation_id)
        
        # Get form data
        export_format = request.form.get('export_format', 'text')
        
        # Prepare the content based on the requested export format
        if export_format == 'bibtex':
            content = citation.bibtex_string
            content_type = 'application/x-bibtex'
            file_ext = '.bib'
        else:  # Default to text
            content = get_formatted_citation_text(citation)
            content_type = 'text/plain'
            file_ext = '.txt'
        
        # Generate a safe filename
        safe_title = "citation_" + str(citation.id)
        filename = safe_title + file_ext
        
        # Create the response
        response = make_response(content)
        response.headers['Content-Type'] = content_type
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    except Exception as e:
        current_app.logger.error(f"Error exporting citation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@citation_bp.route('/api/citation/<int:paper_id>')
@login_required
def api_get_citations(paper_id):
    """API endpoint for retrieving formatted citations in all available styles for a paper"""
    try:
        # Debug logging
        current_app.logger.info(f"API citation request for paper_id: {paper_id}")
        
        # Check if paper exists
        paper = ResearchPaper.query.get_or_404(paper_id)
        current_app.logger.info(f"Found paper: {paper.title}")
        
        # Dictionary to store formatted citations by style
        formatted_citations = {}
        
        # Log paper metadata for debugging
        current_app.logger.info(f"Paper metadata - Authors: {paper.authors}, Year: {paper.publication_year}, "  
                                f"Journal: {paper.journal}, Volume: {paper.volume}, Issue: {paper.issue}, " 
                                f"Pages: {paper.pages}, DOI: {paper.doi}")
        
        # Generate citations in each available style
        for style in CitationStyle:
            try:
                current_app.logger.info(f"Processing citation style: {style.value}")
                # Check if citation already exists for this style
                citation = Citation.query.filter_by(paper_id=paper_id, style=style).first()
                
                if not citation:
                    current_app.logger.info(f"No existing citation found for style {style.value}, generating new one")
                    # Generate BibTeX if citation doesn't exist
                    try:
                        bibtex_string = generate_bibtex_from_paper(paper)
                        current_app.logger.info(f"Generated BibTeX: {bibtex_string[:100]}...")
                    except Exception as e:
                        current_app.logger.error(f"Error in generate_bibtex_from_paper: {str(e)}")
                        raise
                    
                    # Create new citation
                    citation = Citation(
                        paper_id=paper_id,
                        style=style,
                        bibtex_string=bibtex_string
                    )
                    
                    db.session.add(citation)
                    db.session.commit()
                    current_app.logger.info(f"Created new citation record id: {citation.id}")
                else:
                    current_app.logger.info(f"Found existing citation id: {citation.id}")
                    
                # Double-check that we have BibTeX data
                if not citation.bibtex_string:
                    current_app.logger.warning(f"Citation {citation.id} has empty BibTeX string")
                    citation.bibtex_string = generate_bibtex_from_paper(paper)
                    db.session.commit()
                
                # Format the citation according to style
                try:
                    current_app.logger.info(f"Formatting citation style: {style.value}")
                    if style == CitationStyle.APA:
                        formatted_text = format_bibtex_as_apa(citation.bibtex_string)
                    elif style == CitationStyle.MLA:
                        formatted_text = format_bibtex_as_mla(citation.bibtex_string)
                    elif style == CitationStyle.IEEE:
                        formatted_text = format_bibtex_as_ieee(citation.bibtex_string)
                    else:
                        # This should never happen since we're explicitly checking each style
                        formatted_text = "Unknown citation style"
                    
                    current_app.logger.info(f"Successfully formatted citation: {formatted_text[:100]}")
                except Exception as e:
                    current_app.logger.error(f"Error formatting citation in {style.value} style: {str(e)}")
                    formatted_text = f"Error formatting citation: {str(e)}"
                
                # Add citation info to response dictionary
                formatted_citations[style.value] = {
                    'id': citation.id,
                    'formatted_text': formatted_text,
                    'style': style.value,
                    'download_url': url_for('citation.download', citation_id=citation.id),
                    'copy_url': url_for('citation.copy', citation_id=citation.id),
                    'permalink': url_for('citation.download', citation_id=citation.id, _external=True),
                    'copy_count': citation.copy_count,
                    'download_count': citation.download_count
                }
                current_app.logger.info(f"Added {style.value} citation to response")
            except Exception as e:
                current_app.logger.error(f"Error generating {style.value} citation: {str(e)}")
                # Continue with other styles even if one fails
        
        # Return the formatted citations as JSON
        return jsonify({
            'paper_id': paper_id,
            'paper_title': paper.title,
            'citations': formatted_citations
        })
    except Exception as e:
        current_app.logger.error(f"API citation generation error: {str(e)}")
        return jsonify({'error': 'Failed to generate citations'}), 500

@citation_bp.route('/download/<int:citation_id>')
@login_required
def download(citation_id):
    """Download a citation as a .bib file"""
    citation = Citation.query.get_or_404(citation_id)
    
    # Increment download counter
    citation.download_count += 1
    db.session.commit()
    
    # Check if it's an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'download_count': citation.download_count
        })
    
    # Create in-memory file for regular download
    bibtex_file = BytesIO(citation.bibtex_string.encode('utf-8'))
    
    # Generate filename using paper title
    paper_title = citation.paper.title.replace(' ', '_')[:30]
    filename = f"{paper_title}_citation.bib"
    
    return send_file(
        bibtex_file, 
        mimetype='application/x-bibtex',
        as_attachment=True,
        download_name=filename
    )

@citation_bp.route('/copy/<int:citation_id>')
@login_required
def copy(citation_id):
    """Return the citation text and increment the copy counter"""
    citation = Citation.query.get_or_404(citation_id)
    
    # Increment copy counter
    citation.copy_count += 1
    db.session.commit()
    
    # Format the citation according to style
    if citation.style == CitationStyle.APA:
        formatted_citation = format_bibtex_as_apa(citation.bibtex_string)
    elif citation.style == CitationStyle.MLA:
        formatted_citation = format_bibtex_as_mla(citation.bibtex_string)
    elif citation.style == CitationStyle.IEEE:
        formatted_citation = format_bibtex_as_ieee(citation.bibtex_string)
    
    return jsonify({
        'formatted_citation': formatted_citation,
        'copy_count': citation.copy_count,
        'success': True
    })

@citation_bp.route('/export-all')
@login_required
def export_all():
    """Export all citations related to the logged-in user"""
    # Get user's registered profile
    if not hasattr(current_user, 'registered_profile') or current_user.registered_profile is None:
        flash('User profile not found', 'error')
        return redirect(url_for('paper.index'))
    
    user_id = current_user.registered_profile.registered_user_id
    
    # Get papers owned by the user
    papers = ResearchPaper.query.filter_by(owner_registered_user_id=user_id).all()
    paper_ids = [paper.paper_id for paper in papers]
    
    # Get all citations for these papers, preferring APA style
    citations = []
    for paper_id in paper_ids:
        # Try to find APA citation first
        citation = Citation.query.filter_by(paper_id=paper_id, style=CitationStyle.APA).first()
        
        # If APA not found, try other styles
        if not citation:
            citation = Citation.query.filter_by(paper_id=paper_id).first()
        
        # If still no citation, generate one
        if not citation and paper_id:
            paper = ResearchPaper.query.get(paper_id)
            if paper:
                bibtex_string = generate_bibtex_from_paper(paper)
                citation = Citation(paper_id=paper_id, style=CitationStyle.APA, bibtex_string=bibtex_string)
                db.session.add(citation)
                db.session.commit()
        
        if citation:
            citations.append(citation)
    
    if not citations:
        flash('No citations found to export', 'info')
        return redirect(url_for('paper.index'))
    
    # Combine all BibTeX entries
    combined_bibtex = StringIO()
    for citation in citations:
        combined_bibtex.write(citation.bibtex_string)
        combined_bibtex.write("\n\n")
    
    # Generate filename using username
    filename = f"citations_{current_user.username}.bib"
    
    return send_file(
        StringIO(combined_bibtex.getvalue()),
        mimetype='application/x-bibtex',
        as_attachment=True,
        download_name=filename
    )

@citation_bp.route('/view/<int:citation_id>')
@login_required
def view(citation_id):
    """Display citation view for sharing via permalink"""
    # This view requires login as per updated requirements
    citation = Citation.query.get_or_404(citation_id)
    paper = citation.paper
    
    # Format the current citation
    if citation.style == CitationStyle.APA:
        formatted_citation = format_bibtex_as_apa(citation.bibtex_string)
    elif citation.style == CitationStyle.MLA:
        formatted_citation = format_bibtex_as_mla(citation.bibtex_string)
    elif citation.style == CitationStyle.IEEE:
        formatted_citation = format_bibtex_as_ieee(citation.bibtex_string)
    
    # Get all other citation styles for this paper
    all_citations = {}
    for style in CitationStyle:
        if style != citation.style:
            existing_citation = Citation.query.filter_by(paper_id=paper.paper_id, style=style).first()
            if existing_citation:
                if style == CitationStyle.APA:
                    all_citations[style.value] = format_bibtex_as_apa(existing_citation.bibtex_string)
                elif style == CitationStyle.MLA:
                    all_citations[style.value] = format_bibtex_as_mla(existing_citation.bibtex_string)
                elif style == CitationStyle.IEEE:
                    all_citations[style.value] = format_bibtex_as_ieee(existing_citation.bibtex_string)
            else:
                all_citations[style.value] = None
    
    # Add current citation
    all_citations[citation.style.value] = formatted_citation
    
    return render_template(
        'citations/view.html',
        paper=paper,
        current_style=citation.style.value,
        citation=citation,
        all_citations=all_citations
    )

@citation_bp.route('/edit/<int:paper_id>', methods=['GET', 'POST'])
@login_required
def edit_citation_metadata(paper_id):
    """Edit citation metadata for a paper"""
    paper = ResearchPaper.query.get_or_404(paper_id)
    
    # Check if user is authorized to edit (must be the paper owner)
    if paper.owner_registered_user_id != current_user.registered_profile.registered_user_id:
        flash('You do not have permission to edit this paper\'s citation data.', 'danger')
        return redirect(url_for('paper.paper_detail', paper_id=paper_id))
    
    if request.method == 'POST':
        # Update paper with form data
        paper.authors = request.form.get('authors', '')
        paper.publication_year = request.form.get('publication_year', '')
        paper.journal = request.form.get('journal', '')
        paper.volume = request.form.get('volume', '')
        paper.issue = request.form.get('issue', '')
        paper.pages = request.form.get('pages', '')
        paper.publisher = request.form.get('publisher', '')
        paper.doi = request.form.get('doi', '')
        
        # Delete existing citations so they'll be regenerated with new metadata
        Citation.query.filter_by(paper_id=paper_id).delete()
        
        try:
            db.session.commit()
            flash('Citation metadata updated successfully!', 'success')
            return redirect(url_for('paper.paper_detail', paper_id=paper_id))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating citation metadata: {e}")
            flash('An error occurred while updating citation metadata.', 'danger')
            
    # GET request - show form with current values
    return render_template('citations/edit_metadata.html', paper=paper)

@citation_bp.route('/journal-finder', methods=['GET', 'POST'])
@login_required
def journal_finder():
    """Journal finder route for premium users"""
    print("\n======= JOURNAL FINDER ROUTE ACCESSED =======\n")
    print(f"Request method: {request.method}")
    
    # Check if user is authenticated
    if not current_user.is_authenticated:
        flash('You need to log in to access this feature.', 'warning')
        return redirect(url_for('auth.login'))
    
    # Check if user is premium (only premium users can access journal finder)
    # First find the RegisteredUser associated with the current user
    registered_user = db.session.query(RegisteredUser).filter_by(user_id=current_user.user_id).first()
    is_premium = False
    if registered_user:
        # Then check if this RegisteredUser has a premium profile
        is_premium = db.session.query(PremiumUser).filter_by(registered_user_id=registered_user.registered_user_id).first() is not None
    
    if not is_premium:
        print("User is not a premium user")
        return render_template('citations/journal_finder_premium_required.html')
    
    # Import required modules
    import os
    import json
    import string
    import time
    import traceback
    import numpy as np
    from collections import Counter
    from werkzeug.utils import secure_filename
    
    # Initialize variables for both GET and POST requests
    matching_journals = []
    submitted = False
    
    # Load journal data from JSON file
    journals = []
    try:
        # Simplify the path construction to avoid OSErrors on Windows
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        json_path = os.path.join(base_dir, 'journals.json')
        
        print(f"Loading journals from: {json_path}")
        with open(json_path, 'r', encoding='utf-8') as f:
            journals = json.load(f)
        
        print(f"Loaded {len(journals)} journals successfully")
    except Exception as e:
        print(f"ERROR loading journals: {str(e)}")
        flash(f'Error loading journal data: {str(e)}. Please contact support.', 'danger')
        return render_template('citations/journal_finder.html', 
                              matching_journals=[], 
                              submitted=False)
    
    if not journals:
        flash('No journals available in the database', 'warning')
        return render_template('citations/journal_finder.html', 
                              matching_journals=[], 
                              submitted=False)
    
    # Process the form if submitted
    if request.method == 'POST':
        submitted = True
        try:
            # Get form data
            title = request.form.get('title', '').strip()
            abstract = request.form.get('abstract', '').strip()
            open_access_only = request.form.get('open_access_only') == 'on'
            show_all = request.form.get('results_count') == 'all'
            
            # Handle file upload if present
            uploaded_file = request.files.get('paper_file')
            paper_text = ''
            
            if uploaded_file and uploaded_file.filename != '':
                try:
                    # Store the file temporarily
                    filename = secure_filename(uploaded_file.filename)
                    file_path = os.path.join('/tmp', filename)
                    uploaded_file.save(file_path)
                    
                    # Extract text from PDF if it's a PDF file
                    if filename.lower().endswith('.pdf'):
                        try:
                            import PyPDF2
                            with open(file_path, 'rb') as f:
                                pdf_reader = PyPDF2.PdfReader(f)
                                for page_num in range(len(pdf_reader.pages)):
                                    page = pdf_reader.pages[page_num]
                                    paper_text += page.extract_text() + ' '
                        except ImportError:
                            flash('PDF extraction library not available', 'warning')
                        except Exception as e:
                            flash(f'Error extracting text from PDF: {str(e)}', 'warning')
                    else:
                        # For non-PDF files, try reading as text
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                paper_text = f.read()
                        except UnicodeDecodeError:
                            flash('Unable to read the uploaded file. Please ensure it is a text file or PDF.', 'warning')
                        except Exception as e:
                            flash(f'Error reading file: {str(e)}', 'warning')
                    
                    # Clean up temporary file
                    try:
                        os.remove(file_path)
                    except:
                        pass
                except Exception as e:
                    flash(f'Error processing uploaded file: {str(e)}', 'warning')
            
            # Process paper content if we have at least one input source
            if title or abstract or paper_text:
                # Combine all available text
                paper_content = f"{title} {abstract} {paper_text}".strip()
                
                # Helper function to extract keywords (for fallback matching)
                def extract_keywords(text):
                    # Convert to lowercase and remove punctuation
                    text = text.lower()
                    for char in string.punctuation:
                        text = text.replace(char, ' ')
                    
                    # Split into words and remove common words
                    words = text.split()
                    stopwords = set(['and', 'the', 'is', 'in', 'to', 'of', 'a', 'for', 'with', 'on', 'as', 'by', 'that', 'this'])
                    keywords = [word for word in words if word not in stopwords and len(word) > 2]
                    
                    # Find most common words
                    word_counts = Counter(keywords)
                    return [word for word, count in word_counts.most_common(20)]
                
                try:
                    # Start measuring time for embedding generation
                    start_time = time.time()
                    
                    # Import NLP libraries
                    from sentence_transformers import SentenceTransformer
                    
                    # Helper functions for embeddings
                    def get_text_embedding(text, max_length=5000):
                        """Generate an embedding for the given text, with truncation for very long texts"""
                        # Safety check for empty text
                        if not text or len(text.strip()) == 0:
                            return np.zeros(384)
                        
                        # Truncate very long texts to avoid issues
                        if len(text) > max_length:
                            text = text[:max_length]
                        
                        try:
                            # Load model lazily (first time it's needed)
                            global model
                            if 'model' not in globals() or model is None:
                                model = SentenceTransformer('all-MiniLM-L6-v2')
                            
                            # Generate embedding
                            embedding = model.encode(text)
                            return embedding
                        except Exception as e:
                            print(f"ERROR generating embedding: {str(e)}")
                            traceback.print_exc()
                            return np.zeros(384)
                    
                    def cosine_similarity(v1, v2):
                        """Calculate cosine similarity between two vectors"""
                        dot_product = np.dot(v1, v2)
                        norm_v1 = np.linalg.norm(v1)
                        norm_v2 = np.linalg.norm(v2)
                        similarity = dot_product / (norm_v1 * norm_v2) if norm_v1 > 0 and norm_v2 > 0 else 0
                        return similarity
                    
                    # Get paper embedding
                    paper_embedding = get_text_embedding(paper_content)
                    
                    # Cache for journal embeddings
                    journal_embeddings = {}
                    
                    # Compute similarities for all journals
                    similarities = []
                    
                    for journal in journals:
                        # Only include open access journals if the filter is on
                        if open_access_only and not journal.get('open_access', False):
                            continue
                        
                        # Get journal description for semantic matching
                        journal_text = f"{journal.get('name', '')} {journal.get('description', '')} {journal.get('field', '')}"
                        
                        # Get embedding for journal (use cache if available)
                        if journal['name'] in journal_embeddings:
                            journal_embedding = journal_embeddings[journal['name']]
                        else:
                            journal_embedding = get_text_embedding(journal_text)
                            journal_embeddings[journal['name']] = journal_embedding
                        
                        # Compute similarity
                        similarity = cosine_similarity(paper_embedding, journal_embedding)
                        
                        # Add to results
                        similarities.append((journal, similarity))
                    
                    # Sort by similarity score (highest first)
                    similarities.sort(key=lambda x: x[1], reverse=True)
                    
                    # Process results with fallback mechanisms
                    matching_journal_tuples = []
                    threshold = 0.4  # Initial similarity threshold
                    
                    # First attempt: Use semantic similarity with default threshold
                    matching_journal_tuples = [(j, s) for j, s in similarities if s >= threshold]
                    
                    # First fallback: Lower the threshold
                    if not matching_journal_tuples:
                        threshold = 0.2  # Lower threshold
                        matching_journal_tuples = [(j, s) for j, s in similarities if s >= threshold]
                    
                    # Second fallback: Try keyword overlap matching
                    if not matching_journal_tuples:
                        # Extract keywords from the paper content
                        paper_keywords = set(extract_keywords(paper_content))
                        
                        # Match based on keyword overlap
                        keyword_matches = []
                        for journal, _ in similarities:
                            journal_text = f"{journal.get('name', '')} {journal.get('description', '')} {journal.get('field', '')}"
                            journal_keywords = set(extract_keywords(journal_text))
                            
                            # Calculate overlap
                            overlap = len(paper_keywords.intersection(journal_keywords)) / max(1, len(paper_keywords))
                            if overlap > 0:
                                keyword_matches.append((journal, overlap))
                        
                        # Sort by overlap
                        if keyword_matches:
                            keyword_matches.sort(key=lambda x: x[1], reverse=True)
                            matching_journal_tuples = keyword_matches
                    
                    # Third fallback: Default to top journals by field similarity
                    if not matching_journal_tuples:
                        matching_journal_tuples = [(j, s) for j, s in similarities[:5]]
                        flash('No close matches found based on your paper. Showing top journals in your field.', 'info')
                    
                    # Format journal data properly for template display
                    formatted_journals = []
                    for journal, similarity in matching_journal_tuples:
                        # Create a copy of the journal dict to avoid modifying the original
                        j = journal.copy()
                        
                        # Add the match score as a property (convert to percentage)
                        j['match_score'] = similarity
                        
                        # Ensure all required fields exist
                        if 'name' not in j:
                            j['name'] = 'Unknown Journal'
                        if 'field' not in j:
                            j['field'] = 'General'
                        if 'open_access' not in j:
                            j['open_access'] = False
                        if 'submit_link' not in j:
                            j['submit_link'] = '#'
                        if 'aims_scope_link' not in j:
                            j['aims_scope_link'] = '#'
                        
                        # Add to formatted results
                        formatted_journals.append(j)
                    
                    # Replace the tuple list with the formatted journals
                    matching_journals = formatted_journals
                    
                    # Limit results unless "show all" is selected
                    if not show_all and len(matching_journals) > 3:
                        matching_journals = matching_journals[:3]
                    
                    # Measure elapsed time
                    elapsed_time = time.time() - start_time
                    print(f"Journal matching completed in {elapsed_time:.2f}s")
                    
                except Exception as e:
                    print(f"Error in semantic matching: {str(e)}")
                    traceback.print_exc()
                    flash(f"Error matching journals: {str(e)}", 'danger')
            else:
                flash('Please provide a paper title, abstract, or upload a file.', 'warning')
        except Exception as e:
            print(f"Error processing form: {str(e)}")
            traceback.print_exc()
            flash(f"Error processing your request: {str(e)}", 'danger')
            submitted = False  # Don't show results on error
    
    # Render template with results
    return render_template('citations/journal_finder.html',
                          matching_journals=matching_journals,
                          submitted=submitted)

> @citation_bp.route('/api/citation/<int:paper_id>')
  @login_required
  def get_all_citations(paper_id):
      """API endpoint to get all citation styles for a paper"""
      paper = ResearchPaper.query.get_or_404(paper_id)
      
      # Prepare result dictionary
      result = {
          'paper_id': paper_id,
          'paper_title': paper.title,
          'citations': {},
          'errors': {}
      }
      
      # Check for existing citations or generate them
      for style in CitationStyle:
          try:
              citation = Citation.query.filter_by(paper_id=paper_id, style=style).first()
              if not citation:
                  # Try to generate citation
                  try:
                      bibtex_string = generate_bibtex_from_paper(paper)
                      citation = Citation(paper_id=paper_id, style=style, bibtex_string=bibtex_string)
                      db.session.add(citation)
                      db.session.commit()
                  except Exception as gen_exc:
                      current_app.logger.error(f"Failed to generate citation for paper {paper_id} style {style}: 
{gen_exc}")
                      result['errors'][style.value] = f"Generation failed: {gen_exc}"
                      continue
              # Format citation
              if style == CitationStyle.APA:
                  formatted_citation = format_bibtex_as_apa(citation.bibtex_string)
              elif style == CitationStyle.MLA:
                  formatted_citation = format_bibtex_as_mla(citation.bibtex_string)
              elif style == CitationStyle.IEEE:
                  formatted_citation = format_bibtex_as_ieee(citation.bibtex_string)
              else:
                  formatted_citation = "Unsupported citation style"
              # Add to results
              result['citations'][style.value] = {
                  'citation_id': citation.id,
                  'formatted_text': formatted_citation,
                  'download_url': url_for('citation.download', citation_id=citation.id, _external=True),
                  'copy_url': url_for('citation.copy', citation_id=citation.id, _external=True),
                  'permalink': url_for('citation.view', citation_id=citation.id, _external=True)
              }
          except Exception as e:
              current_app.logger.error(f"Citation error for paper {paper_id} style {style}: {e}")
              result['errors'][style.value] = str(e)
      return jsonify(result)


