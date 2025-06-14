from flask import jsonify, url_for, current_app
from flask_login import login_required

from app.models import Citation, CitationStyle, ResearchPaper
from app.extensions import db
from app.citation import citation_bp
from app.citation.routes import generate_bibtex_from_paper, format_bibtex_as_apa, format_bibtex_as_mla, format_bibtex_as_ieee

# This file re-exports the api_bp from api_routes to maintain compatibility
from app.api_routes import api_bp

# API endpoint for retrieving citations for a paper
@api_bp.route('/api/citation/<int:paper_id>', endpoint='api_citation')
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
        
        # Generate citations in each available style
        for style in CitationStyle:
            try:
                # Check if citation already exists for this style
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
                    formatted_text = format_bibtex_as_apa(citation.bibtex_string)
                elif style == CitationStyle.MLA:
                    formatted_text = format_bibtex_as_mla(citation.bibtex_string)
                elif style == CitationStyle.IEEE:
                    formatted_text = format_bibtex_as_ieee(citation.bibtex_string)
                else:
                    # This should never happen since we're explicitly checking each style
                    formatted_text = "Unknown citation style"
                
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
