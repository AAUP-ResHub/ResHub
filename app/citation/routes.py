from datetime import datetime
from io import StringIO, BytesIO
from flask import render_template, redirect, url_for, flash, request, jsonify, send_file, abort, current_app
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app.citation import citation_bp
from app.models import Citation, CitationStyle, ResearchPaper
from app.extensions import db

import pybtex.database
from pybtex.style.formatting.unsrt import Style as UnsrtStyle
from pybtex.backends.html import Backend as HtmlBackend
from pybtex.style.template import field, join, words, optional, sentence

# Dictionary to map citation styles to their formatters
CITATION_FORMATTERS = {}

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

@citation_bp.route('/api/citation/<int:paper_id>')
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
                    current_app.logger.error(f"Failed to generate citation for paper {paper_id} style {style}: {gen_exc}")
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
