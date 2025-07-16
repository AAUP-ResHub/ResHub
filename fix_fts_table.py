#!/usr/bin/env python
"""
Full-Text Search (FTS) Repair Utility

This script was created to fix issues with the SQLite FTS5 virtual table for research papers,
which was causing errors when trying to upload new research papers.

Problem:
After adding the missing columns to the research_papers table, uploads were still failing
with the error: "vtable constructor failed: research_papers_fts"
This occurs because the FTS5 virtual table that provides full-text search functionality
for papers was corrupted or improperly configured.

Solution:
This script attempts to:
1. Drop existing FTS tables and triggers that may be corrupted
2. Create a new properly structured FTS5 virtual table
3. Set up the necessary triggers to keep the search index in sync with the main table
4. Re-populate the FTS table with existing paper data

Context:
This is part of a series of database fixes to ensure the ResHub application can
properly handle research paper uploads. The FTS functionality provides search capabilities
for paper titles and abstracts, but if corrupted, it prevents even basic CRUD operations
on the research_papers table.
"""

import os
import sqlite3
from datetime import datetime

# Path to your SQLite database file
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'app.db')

def fix_fts_table():
    """Fix the Full-Text Search tables and triggers for research_papers"""
    print(f"Connecting to database at: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}")
        return False
        
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if the research_papers table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='research_papers';")
        if not cursor.fetchone():
            print("Error: research_papers table does not exist!")
            return False
        
        print("Dropping existing FTS tables and triggers...")
        # Drop existing triggers if they exist
        cursor.execute("DROP TRIGGER IF EXISTS research_papers_ai;")
        cursor.execute("DROP TRIGGER IF EXISTS research_papers_au;")
        cursor.execute("DROP TRIGGER IF EXISTS research_papers_ad;")
        
        # Drop the FTS table if it exists
        cursor.execute("DROP TABLE IF EXISTS research_papers_fts;")
        cursor.execute("DROP TABLE IF EXISTS research_papers_fts_idx;")
        cursor.execute("DROP TABLE IF EXISTS research_papers_fts_data;")
        cursor.execute("DROP TABLE IF EXISTS research_papers_fts_docsize;")
        cursor.execute("DROP TABLE IF EXISTS research_papers_fts_config;")
        
        print("Creating new FTS5 table...")
        # Create a new FTS5 table
        cursor.execute("""
            CREATE VIRTUAL TABLE research_papers_fts USING fts5(
                paper_id UNINDEXED,
                title,
                abstract,
                tokenize='porter unicode61'
            );
        """)
        
        print("Creating INSERT trigger...")
        # Create trigger for INSERT operations
        cursor.execute("""
            CREATE TRIGGER research_papers_ai AFTER INSERT ON research_papers BEGIN
                INSERT INTO research_papers_fts (paper_id, title, abstract)
                VALUES (new.paper_id, new.title, new.abstract);
            END;
        """)
        
        print("Creating UPDATE trigger...")
        # Create trigger for UPDATE operations
        cursor.execute("""
            CREATE TRIGGER research_papers_au AFTER UPDATE ON research_papers BEGIN
                UPDATE research_papers_fts 
                SET title = new.title, abstract = new.abstract
                WHERE paper_id = old.paper_id;
            END;
        """)
        
        print("Creating DELETE trigger...")
        # Create trigger for DELETE operations
        cursor.execute("""
            CREATE TRIGGER research_papers_ad AFTER DELETE ON research_papers BEGIN
                DELETE FROM research_papers_fts WHERE paper_id = old.paper_id;
            END;
        """)
        
        # Populate the FTS table with existing data
        print("Populating FTS table with existing data...")
        cursor.execute("""
            INSERT INTO research_papers_fts (paper_id, title, abstract)
            SELECT paper_id, title, abstract FROM research_papers;
        """)
        
        # Verify that rows were added to the FTS table
        result = cursor.execute("SELECT COUNT(*) FROM research_papers_fts;").fetchone()[0]
        print(f"Successfully populated FTS table with {result} records")
        
        conn.commit()
        print("FTS table and triggers have been successfully recreated!")
        return True
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    fix_fts_table()
