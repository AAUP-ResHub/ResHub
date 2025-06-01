from app import create_app
from sqlalchemy import text

# Create an application context
app = create_app()

with app.app_context():
    from app import db
    
    print("Creating FTS5 table and triggers...")
    
    # Create the FTS5 virtual table
    db.session.execute(text('''
        CREATE VIRTUAL TABLE IF NOT EXISTS research_papers_fts USING fts5(
            paper_id UNINDEXED,
            title,
            abstract,
            tokenize = 'porter unicode61'
        );
    '''))
    
    # Create triggers (drop first if they exist to avoid errors)
    db.session.execute(text('DROP TRIGGER IF EXISTS research_papers_ai;'))
    db.session.execute(text('''
        CREATE TRIGGER research_papers_ai AFTER INSERT ON research_papers BEGIN
            INSERT INTO research_papers_fts (paper_id, title, abstract)
            VALUES (new.id, new.title, new.abstract);
        END;
    '''))
    
    db.session.execute(text('DROP TRIGGER IF EXISTS research_papers_ad;'))
    db.session.execute(text('''
        CREATE TRIGGER research_papers_ad AFTER DELETE ON research_papers BEGIN
            DELETE FROM research_papers_fts WHERE paper_id = old.id;
        END;
    '''))
    
    db.session.execute(text('DROP TRIGGER IF EXISTS research_papers_au;'))
    db.session.execute(text('''
        CREATE TRIGGER research_papers_au AFTER UPDATE OF title, abstract ON research_papers BEGIN
            UPDATE research_papers_fts SET 
                title = new.title, 
                abstract = new.abstract
            WHERE paper_id = old.id; 
        END;
    '''))
    
    db.session.commit()
    print("FTS5 table and triggers created successfully!")
    
    # Populate FTS table with existing data
    try:
        # First, let's inspect the table structure to get the correct column names
        table_info = db.session.execute(text("PRAGMA table_info(research_papers)")).fetchall()
        print("Research Papers table structure:")
        for col in table_info:
            print(f"Column: {col[1]}, Type: {col[2]}")
        
        # Now use the correct column name for the primary key (probably paper_id instead of id)
        db.session.execute(text('DELETE FROM research_papers_fts;'))  # Clear any existing data
        db.session.execute(text('''
            INSERT INTO research_papers_fts (paper_id, title, abstract) 
            SELECT paper_id, title, abstract FROM research_papers;
        '''))
        db.session.commit()
        
        # Verify the data was inserted
        result = db.session.execute(text("SELECT COUNT(*) FROM research_papers_fts")).scalar()
        print(f"Successfully populated FTS table with {result} records")
    except Exception as e:
        db.session.rollback()
        print(f"Error populating FTS table: {e}")
        print("This might be expected if you don't have any research papers yet.")

print("Done!")

