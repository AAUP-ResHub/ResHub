/**
 * Response Parser for ResHub Chatbot
 * 
 * Parses XML-formatted responses from the AI into structured objects.
 */

/**
 * Parse XML-formatted AI response
 * @param {string} xmlString - Raw XML response from AI
 * @returns {Object} Structured response object
 */
export function parse(xmlString) {
  if (!xmlString || typeof xmlString !== 'string') {
    return {
      answer: xmlString || '',
      citations: [],
      extras: ''
    };
  }

  const result = {
    answer: '',
    citations: [],
    extras: ''
  };

  try {
    // Extract answer content
    const answerMatch = xmlString.match(/<answer>([\s\S]*?)<\/answer>/i);
    if (answerMatch) {
      result.answer = answerMatch[1].trim();
    }

    // Extract extras content
    const extrasMatch = xmlString.match(/<extras>([\s\S]*?)<\/extras>/i);
    if (extrasMatch) {
      result.extras = extrasMatch[1].trim();
    }

    // Extract citations
    const citationsMatch = xmlString.match(/<citations>([\s\S]*?)<\/citations>/i);
    if (citationsMatch) {
      const citationsContent = citationsMatch[1];
      
      // Parse individual citation entries
      const citationMatches = citationsContent.match(/<citation[^>]*>([\s\S]*?)<\/citation>/gi);
      if (citationMatches) {
        result.citations = citationMatches.map(citation => {
          const contentMatch = citation.match(/<citation[^>]*>([\s\S]*?)<\/citation>/i);
          const content = contentMatch ? contentMatch[1].trim() : '';
          
          // Extract attributes if present
          const idMatch = citation.match(/id=["']([^"']+)["']/i);
          const titleMatch = citation.match(/title=["']([^"']+)["']/i);
          const authorsMatch = citation.match(/authors=["']([^"']+)["']/i);
          const yearMatch = citation.match(/year=["']([^"']+)["']/i);
          
          return {
            id: idMatch ? idMatch[1] : null,
            title: titleMatch ? titleMatch[1] : null,
            authors: authorsMatch ? authorsMatch[1] : null,
            year: yearMatch ? yearMatch[1] : null,
            content: content
          };
        });
      }
    }

    // If no XML structure found, treat entire string as answer
    if (!result.answer && !result.citations.length && !result.extras) {
      result.answer = xmlString.trim();
    }

  } catch (error) {
    console.warn('Error parsing XML response:', error);
    // Fallback to treating entire string as answer
    result.answer = xmlString.trim();
  }

  return result;
}

/**
 * Parse citations from a citations string
 * @param {string} citationsString - Citations content
 * @returns {Array} Array of citation objects
 */
export function parseCitations(citationsString) {
  if (!citationsString) return [];

  try {
    // Try to parse as JSON first
    const jsonCitations = JSON.parse(citationsString);
    if (Array.isArray(jsonCitations)) {
      return jsonCitations;
    }
  } catch (e) {
    // Not JSON, continue with XML parsing
  }

  // Parse as XML citations
  const citations = [];
  const citationMatches = citationsString.match(/<citation[^>]*>([\s\S]*?)<\/citation>/gi);
  
  if (citationMatches) {
    citations.push(...citationMatches.map(citation => {
      const contentMatch = citation.match(/<citation[^>]*>([\s\S]*?)<\/citation>/i);
      return {
        content: contentMatch ? contentMatch[1].trim() : citation
      };
    }));
  } else {
    // Split by common delimiters if no XML structure
    const lines = citationsString.split(/\n|;|\|/).filter(line => line.trim());
    citations.push(...lines.map(line => ({ content: line.trim() })));
  }

  return citations;
}

/**
 * Format citation for display
 * @param {Object} citation - Citation object
 * @returns {string} Formatted citation string
 */
export function formatCitation(citation) {
  if (!citation) return '';

  if (citation.content) {
    return citation.content;
  }

  // Build citation from components
  let formatted = '';
  
  if (citation.authors) {
    formatted += citation.authors;
  }
  
  if (citation.year) {
    formatted += ` (${citation.year})`;
  }
  
  if (citation.title) {
    formatted += `. ${citation.title}`;
  }

  return formatted || 'Unknown citation';
}

/**
 * Check if response contains XML structure
 * @param {string} response - Response string
 * @returns {boolean} True if XML structure detected
 */
export function hasXMLStructure(response) {
  if (!response || typeof response !== 'string') return false;
  
  return /<(answer|citations|extras)>/i.test(response);
}

export default {
  parse,
  parseCitations,
  formatCitation,
  hasXMLStructure
};
