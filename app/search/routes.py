from flask import request, render_template, current_app, flash
from . import search_bp  # from app.search import search_bp
from app import db  # For executing raw SQL
from app.models import ResearchPaper  # To fetch full paper objects
from sqlalchemy import text, or_  # For executing literal SQL queries
import traceback
import re

@search_bp.route('/', methods=['GET'])  # This will make the route accessible at /search/
def results():
    query_string = request.args.get('q', '').strip()
    papers_with_highlights = []  # Will store dicts: {'paper': ResearchPaper_obj, 'title_highlight': '...', 'abstract_highlight': '...'}
    
    if query_string:
        try:
            # Use a simple SQL-based search approach instead of FTS5
            # This should work regardless of whether FTS5 is set up
            search_terms = query_string.split()
            
            # Build search filter conditions
            filters = []
            for term in search_terms:
                term_like = f'%{term}%'
                filters.append(or_(
                    ResearchPaper.title.ilike(term_like),
                    ResearchPaper.abstract.ilike(term_like),
                    ResearchPaper.keywords.ilike(term_like)
                ))
            
            # Combine all filters with AND (papers must match all terms)
            papers = ResearchPaper.query
            for filter_condition in filters:
                papers = papers.filter(filter_condition)
            
            # Get results ordered by newest first
            search_results = papers.order_by(ResearchPaper.publish_date.desc()).all()
            
            # Highlight search terms in results
            for paper in search_results:
                # Simple highlighting function
                def highlight_text(text, terms):
                    if not text:
                        return None
                    
                    highlighted = text
                    for term in terms:
                        # Case-insensitive replacement with regex
                        pattern = re.compile(re.escape(term), re.IGNORECASE)
                        highlighted = pattern.sub(f'<strong>{term}</strong>', highlighted)
                    
                    # If text is too long, create a snippet around the first match
                    if len(highlighted) > 200:
                        # Find position of first highlight
                        first_highlight_pos = highlighted.find('<strong>')
                        if first_highlight_pos > 0:
                            # Calculate start position for snippet
                            start_pos = max(0, first_highlight_pos - 100)
                            # Find a space to start cleanly
                            if start_pos > 0:
                                start_pos = highlighted.find(' ', start_pos - 20)
                            
                            # Extract snippet
                            end_pos = min(len(highlighted), start_pos + 200)
                            highlighted = '...' + highlighted[start_pos:end_pos] + '...'
                    
                    return highlighted
                
                # Create highlighted versions of title and abstract
                title_highlight = highlight_text(paper.title, search_terms)
                abstract_highlight = highlight_text(paper.abstract, search_terms)
                
                # Add to results
                papers_with_highlights.append({
                    'paper': paper,
                    'title_highlight': title_highlight,
                    'abstract_highlight': abstract_highlight
                })
            
        except Exception as e:
            error_msg = f"Search query failed for '{query_string}': {str(e)}"
            tb = traceback.format_exc()
            current_app.logger.error(f"{error_msg}\n{tb}")
            
            # Flash an error message to help with debugging
            flash('Search encountered an error. Please try again.', 'danger')
    
    return render_template('search/results.html', query=query_string, papers_with_highlights=papers_with_highlights)