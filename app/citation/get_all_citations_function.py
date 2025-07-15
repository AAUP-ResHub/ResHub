
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


