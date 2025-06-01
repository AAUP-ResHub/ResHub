from flask import request, render_template, current_app
from . import search_bp  # from app.search import search_bp
from app import db  # For executing raw SQL
from app.models import ResearchPaper  # To fetch full paper objects
from sqlalchemy import text  # For executing literal SQL queries

@search_bp.route('/', methods=['GET'])  # This will make the route accessible at /search/
def results():
    query_string = request.args.get('q', '').strip()
    papers_with_highlights = []  # Will store dicts: {'paper': ResearchPaper_obj, 'title_highlight': '...', 'abstract_highlight': '...'}
    
    if query_string:
        try:
            # Using FTS5 MATCH operator and snippet function for highlighting.
            # The snippet function arguments are: table_name, column_name, 
            #                                   highlight_start_tag, highlight_end_tag, 
            #                                   ellipsis, num_tokens_around_match.
            sql_fts_query = """
                SELECT 
                    paper_id, 
                    snippet(research_papers_fts, 'title', '<strong>', '</strong>', '...', 15) as title_highlight,
                    snippet(research_papers_fts, 'abstract', '<strong>', '</strong>', '...', 15) as abstract_highlight
                FROM research_papers_fts
                WHERE research_papers_fts MATCH :query
                ORDER BY rank; 
            """
            # The 'rank' pseudo-column is provided by FTS5 for ordering by relevance.

            search_results_raw = db.session.execute(text(sql_fts_query), {'query': query_string}).mappings().fetchall()
            # .mappings() allows accessing columns by name like row['paper_id']

            if search_results_raw:
                paper_ids_from_fts = [row['paper_id'] for row in search_results_raw]
                
                # Fetch the actual ResearchPaper objects from the main table
                # We need a way to map them back to the highlights and maintain order
                if paper_ids_from_fts:
                    papers_map = {p.id: p for p in ResearchPaper.query.filter(ResearchPaper.id.in_(paper_ids_from_fts)).all()}
                    
                    for row_data in search_results_raw:
                        paper_obj = papers_map.get(row_data['paper_id'])
                        if paper_obj:
                            papers_with_highlights.append({
                                'paper': paper_obj,
                                'title_highlight': row_data['title_highlight'],
                                'abstract_highlight': row_data['abstract_highlight']
                            })
            
        except Exception as e:
            current_app.logger.error(f"Search query failed for '{query_string}': {e}")
            # Optionally, flash an error message to the user
            # from flask import flash
            # flash('Search encountered an error. Please try again.', 'danger')
    
    # Person 3 will create the 'search/results.html' template
    return render_template('search(testing)/results.html', query=query_string, papers_with_highlights=papers_with_highlights)