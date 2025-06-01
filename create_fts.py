import os
import sqlite3
from app import create_app
from sqlalchemy import text, inspect

# Create an application context
app = create_app()

# Get the instance folder path where app.db is stored
instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
db_path = os.path.join(instance_path, 'app.db')

print(f"Using database at: {db_path}")

# Ensure the instance directory exists
os.makedirs(instance_path, exist_ok=True)

# Direct SQLite connection to check if FTS5 is available
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if FTS5 is available
cursor.execute("SELECT sqlite_compileoption_used('ENABLE_FTS5')")
fts5_available = cursor.fetchone()[0]

if not fts5_available:
    print("WARNING: FTS5 extension is not available in this SQLite build")
else:
    print("FTS5 extension is available")

# Close the direct connection
conn.close()

with app.app_context():
    from app import db
    from app.models import ResearchPaper
    
    print("Creating FTS5 table and triggers...")
    
    # First, check if FTS table exists and drop it
    inspector = inspect(db.engine)
    if 'research_papers_fts' in inspector.get_table_names():
        print("Dropping existing FTS5 table...")
        db.session.execute(text('DROP TABLE IF EXISTS research_papers_fts;'))
    
    # Create the FTS5 table with external content for research_papers
    print("Creating new FTS5 table...")
    db.session.execute(text('''
        CREATE VIRTUAL TABLE research_papers_fts USING fts5(
            paper_id, 
            title, 
            abstract, 
            content='research_papers', 
            content_rowid='paper_id'
        );
    '''))
    
    # Create triggers (drop first if they exist to avoid errors)
    db.session.execute(text('DROP TRIGGER IF EXISTS research_papers_ai;'))
    print("Creating INSERT trigger...")
    db.session.execute(text('''
        CREATE TRIGGER IF NOT EXISTS research_papers_ai AFTER INSERT ON research_papers BEGIN
            INSERT INTO research_papers_fts (paper_id, title, abstract)
            VALUES (new.paper_id, new.title, new.abstract);
        END;
    '''))
    
    db.session.execute(text('DROP TRIGGER IF EXISTS research_papers_ad;'))
    print("Creating DELETE trigger...")
    db.session.execute(text('''
        CREATE TRIGGER IF NOT EXISTS research_papers_ad AFTER DELETE ON research_papers BEGIN
            DELETE FROM research_papers_fts WHERE paper_id = old.paper_id;
        END;
    '''))
    
    db.session.execute(text('DROP TRIGGER IF EXISTS research_papers_au;'))
    print("Creating UPDATE trigger...")
    db.session.execute(text('''
        CREATE TRIGGER IF NOT EXISTS research_papers_au AFTER UPDATE OF title, abstract ON research_papers BEGIN
            UPDATE research_papers_fts SET 
                title = new.title, 
                abstract = new.abstract
            WHERE paper_id = old.paper_id; 
        END;
    '''))
    
    db.session.commit()
    print("FTS5 table and triggers created successfully!")
    
    # Let's check the structure of research_papers to see what columns it has
    inspector = inspect(db.engine)
    columns = [col for col in inspector.get_columns('research_papers')]
    print("Research Papers table structure:")
    for column in columns:
        print(f"Column: {column['name']}, Type: {str(column['type']).upper()}")
        
    # Check if there are papers in the database
    paper_count = ResearchPaper.query.count()
    print(f"Found {paper_count} papers in the database")
        
    # Now use the correct column name for the primary key (probably paper_id instead of id)
    db.session.execute(text('DELETE FROM research_papers_fts;'))    # Populate the FTS5 table with existing data
    print("Populating FTS5 table with existing data...")
    db.session.execute(text('''
        DELETE FROM research_papers_fts;
        INSERT INTO research_papers_fts (paper_id, title, abstract) 
        SELECT paper_id, title, abstract FROM research_papers;
    '''))
    
    # Verify that rows were added to the FTS table
    result = db.session.execute(text('SELECT COUNT(*) FROM research_papers_fts;')).scalar()
    print(f"Successfully populated FTS table with {result} records")
    
    # Test a query to verify it works
    test_query = "paper"
    test_result = db.session.execute(text('''
        SELECT paper_id FROM research_papers_fts 
        WHERE research_papers_fts MATCH :query
    '''), {"query": test_query}).fetchall()
    print(f"Test query '{test_query}' returned {len(test_result)} results")
    if test_result:
        print(f"Found papers with IDs: {', '.join(str(r[0]) for r in test_result)}")
    
    db.session.commit()
    print("Done!")
    
    # Now add support for a simple search form in the base template
    print("\nMake sure to update app/templates/base.html to include a search form in the navbar:")
    print('''
    <!-- Add this in your navbar -->
    <form class="d-flex" action="{{ url_for('search.results') }}" method="get">
        <input class="form-control me-2" type="search" placeholder="Search papers..." name="q" aria-label="Search">
        <button class="btn btn-outline-light" type="submit">Search</button>
    </form>
    ''')
    print("\nNow restart your Flask application to start using the search feature.")
