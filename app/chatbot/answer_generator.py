import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check for OpenAI availability
OPENAI_AVAILABLE = False

try:
    # Import OpenAI conditionally - don't fail if not installed
    import openai
    # Set API key if available
    if os.getenv("OPENAI_API_KEY"):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        OPENAI_AVAILABLE = True
except ImportError:
    print("OpenAI package not installed. Answer generation will be simulated.")

class AnswerGenerator:
    """
    Generates research answers based on retrieved text chunks.
    Uses OpenAI GPT models if available, with fallback to template-based answers.
    """
    
    def __init__(self, model_name="gpt-4o"):
        """
        Initialize the answer generator.
        
        Args:
            model_name: Name of the OpenAI model to use
        """
        self.model_name = model_name
    
    def generate(self, query, chunks, citation_style="APA", max_tokens=1000):
        """
        Generate a research answer based on retrieved chunks.
        
        Args:
            query: User's research question
            chunks: List of retrieved text chunks with metadata
            citation_style: Citation style (APA, MLA, InlineURL)
            max_tokens: Maximum length of the answer
            
        Returns:
            Dictionary with answer, extras, and citations
        """
        # Format chunks for context
        context = self._format_context(chunks)
        
        # Generate answer using OpenAI if available
        if OPENAI_AVAILABLE:
            try:
                return self._generate_with_openai(query, context, chunks, citation_style, max_tokens)
            except Exception as e:
                print(f"OpenAI answer generation failed: {str(e)}")
        
        # Fallback to template-based answer
        return self._generate_fallback(query, chunks, citation_style)
    
    def _format_context(self, chunks):
        """Format the chunks into context for the prompt."""
        context = ""
        for i, chunk in enumerate(chunks[:12]):  # Limit to 12 chunks
            metadata = chunk.get("metadata", {})
            title = metadata.get("title", "Untitled Paper")
            authors = metadata.get("authors", ["Unknown"])
            if isinstance(authors, str):
                # Handle case where authors is a string (e.g., from database)
                authors = authors.split(", ")
            year = metadata.get("year", "n.d.")
            source_id = metadata.get("source_id", "")
            
            # Format author string (first author et al. for multiple authors)
            author_str = authors[0]
            if len(authors) > 1:
                author_str += " et al."
            
            # Truncate text if too long
            text = chunk.get("text", "")
            if len(text) > 1500:
                text = text[:1500] + "..."
            
            context += f"[{i+1}] {title} ({author_str}, {year}):\n{text}\n\n"
        
        return context
    
    def _generate_with_openai(self, query, context, chunks, citation_style, max_tokens):
        """Generate answer using OpenAI API."""
        # Create system prompt
        system_prompt = f"""
You are ResHub Research Assistant, an AI that helps researchers locate, understand, and synthesise scholarly literature from the excerpts provided.

Return **valid XML** using exactly these tags:

<answer>...</answer>
<extras>...</extras>
<citations>...</citations>

Guidelines
• Write complete, conclusive sentences—**never** end with ellipses (...) or imply the answer is unfinished.  
• Use paragraphs and bullet points for clarity where helpful.  
• Cite **only** information present in the provided excerpts. Do **not** invent or fill gaps.  
• In the <answer> and <extras> tags, place inline citation numbers like [1], [2] immediately after the information they support.  
• In the <citations> tag, create a numbered list of the full sources you cited, formatted in {citation_style} style. The numbers must correspond to the context excerpts you used.  
• In the <extras> tag, briefly list any key limitations, methodologies, or future research directions mentioned. If none are present, leave this tag empty.  
• If no excerpt is relevant to the query, return exactly: `<answer>No relevant information found.</answer>` and leave the other tags empty.  
• Escape any literal “<” or “>” characters inside tag content as &lt; or &gt;.  
• Aim to stay within **{max_tokens} tokens**; if space is tight, prefer concise synthesis.  

Example (for structure only):
<answer>Deep-learning approaches consistently outperform traditional methods in forecasting tasks [1].</answer>
<extras>Key limitations mentioned in the literature include small sample sizes and overfitting risks [3].</extras>
<citations>
[1] Author, A. A. (Year). Title of work. Journal, volume(issue), pages.  
[3] Another, B. B. (Year). A different title. Journal, volume(issue), pages.  
</citations>
"""
        
        # Create user message
        user_message = f"Question: {query}\n\nRelevant passages:\n{context}"
        
        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.2,
            top_p=0.95,
            max_tokens=max_tokens,
            stop=["###"]
        )

        # Extract response - compatible with v0.28.x
        full_response = response.choices[0].message.content
        
        # Parse sections (simplified parsing)
        answer = ""
        extras = ""
        citations = ""
        
        if "<answer>" in full_response and "</answer>" in full_response:
            answer = full_response.split("<answer>")[1].split("</answer>")[0].strip()
        
        if "<extras>" in full_response and "</extras>" in full_response:
            extras = full_response.split("<extras>")[1].split("</extras>")[0].strip()
        
        if "<citations>" in full_response and "</citations>" in full_response:
            citations = full_response.split("<citations>")[1].split("</citations>")[0].strip()
        
        return {
            "answer": answer,
            "extras": extras,
            "citations": citations,
            "token_in": len(user_message) // 4,  # Approximate token count
            "token_out": len(full_response) // 4  # Approximate token count
        }
    
    def _generate_fallback(self, query, chunks, citation_style):
        """Generate a fallback answer without using OpenAI."""
        # Create a simple answer using the most relevant chunk
        if not chunks:
            return {
                "answer": "I couldn't find any relevant research papers for your query.",
                "extras": "Please try a different question or adjust your search terms.",
                "citations": "",
                "token_in": len(query) // 4,
                "token_out": 50  # Approximate
            }
        
        # Use the top chunk for the answer
        top_chunk = chunks[0]
        metadata = top_chunk.get("metadata", {})
        title = metadata.get("title", "Untitled Paper")
        authors = metadata.get("authors", ["Unknown"])
        if isinstance(authors, str):
            authors = authors.split(", ")
        year = metadata.get("year", "n.d.")
        
        # Format citation based on style
        citation = ""
        if citation_style == "APA":
            author_list = ", ".join(authors[:-1]) + " & " + authors[-1] if len(authors) > 1 else authors[0]
            citation = f"{author_list} ({year}). {title}."
        elif citation_style == "MLA":
            author_list = ", ".join(authors[:-1]) + ", and " + authors[-1] if len(authors) > 1 else authors[0]
            citation = f"{author_list}. \"{title}.\" {year}."
        else:  # InlineURL
            citation = f"{title} ({year}). Retrieved from: {metadata.get('url', 'n/a')}"
        
        # Extract a snippet from the chunk text
        text = top_chunk.get("text", "")
        snippet = text[:500] + "..." if len(text) > 500 else text
        
        answer = f"Based on the research I found, {snippet}"
        
        extras = f"This information comes primarily from '{title}' by {', '.join(authors[:3])}"
        if len(authors) > 3:
            extras += " and others"
        extras += f", published in {year}."
        
        return {
            "answer": answer,
            "extras": extras,
            "citations": f"[1] {citation}",
            "token_in": len(query) // 4,
            "token_out": (len(answer) + len(extras) + len(citation)) // 4  # Approximate
        }
    
    def format_citation(self, metadata, citation_style):
        """Format citation for a paper based on metadata and style."""
        title = metadata.get("title", "Untitled")
        authors = metadata.get("authors", ["Unknown"])
        if isinstance(authors, str):
            authors = authors.split(", ")
        year = metadata.get("year", "n.d.")
        url = metadata.get("url", "")
        
        if citation_style == "APA":
            author_list = ", ".join(authors[:-1]) + " & " + authors[-1] if len(authors) > 1 else authors[0]
            return f"{author_list} ({year}). {title}."
        elif citation_style == "MLA":
            author_list = ", ".join(authors[:-1]) + ", and " + authors[-1] if len(authors) > 1 else authors[0]
            return f"{author_list}. \"{title}.\" {year}."
        else:  # InlineURL
            return f"{title} ({year}). Retrieved from: {url}"
