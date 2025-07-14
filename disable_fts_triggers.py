#!/usr/bin/env python
"""
FTS Triggers Disabling Utility

This script was created as a targeted solution to fix errors encountered when uploading research papers
and when accessing the forum from the navigation menu.

Problem:
After attempting to add missing columns to the research_papers table, we still encountered 
SQLAlchemy OperationalErrors: "vtable constructor failed: research_papers_fts"
This error occurred during both paper upload operations and when accessing the forum functionality.

The issue was related to the Full-Text Search (FTS) virtual table system in SQLite, which was 
corrupted or improperly configured. Specifically, the triggers that automatically update the 
FTS index were causing SQL errors when database operations were performed.

Solution:
This script disables (removes) the problematic FTS triggers that were causing errors.
By removing these triggers, we prevent the automatic updates to the FTS virtual table
that were failing during paper uploads and forum access.

Trade-offs:
- Advantage: Users can now upload research papers and access the forum without errors
- Disadvantage: The full-text search functionality for papers will not work until properly reconfigured

Context:
This is part of a series of database fixes addressing schema mismatches in the ResHub application.
Previously, we fixed issues with missing columns in both the workspace_files table and the
research_papers table. This script addresses the related FTS virtual table configuration
that was preventing normal database operations.
"""

import os
import sqlite3

# Path to your SQLite database file
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'app.db')

def disable_fts_triggers():
    """Disable the FTS triggers that are causing errors"""
    print(f"Connecting to database at: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}")
        return False
        
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("Dropping existing FTS triggers...")
        # Drop existing triggers that are causing issues
        cursor.execute("DROP TRIGGER IF EXISTS research_papers_ai;")
        cursor.execute("DROP TRIGGER IF EXISTS research_papers_au;")
        cursor.execute("DROP TRIGGER IF EXISTS research_papers_ad;")
        
        conn.commit()
        print("FTS triggers have been successfully removed!")
        print("You should now be able to upload papers without FTS errors.")
        return True
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    disable_fts_triggers()
