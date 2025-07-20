#!/usr/bin/env python3
"""
Script to diagnose and fix notification IntegrityError issues
"""

from app import create_app
from app.models import Notification, RegisteredUser
from app.extensions import db
import traceback

def diagnose_notification_issues():
    """Diagnose notification database issues"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("=== Notification Database Diagnosis ===")
            
            # 1. Check for notifications with NULL recipient_registered_user_id
            print("\n1. Checking for notifications with NULL recipient_registered_user_id...")
            null_recipients = Notification.query.filter(Notification.recipient_registered_user_id.is_(None)).all()
            print(f"Found {len(null_recipients)} notifications with NULL recipient_registered_user_id")
            
            for notif in null_recipients:
                print(f"  - Notification ID: {notif.notification_id}, Message: {notif.message[:50]}...")
            
            # 2. Check total count of notifications
            total_notifications = Notification.query.count()
            print(f"\n2. Total notifications in database: {total_notifications}")
            
            # 3. Check for notifications with invalid foreign key references
            print("\n3. Checking for notifications with invalid recipient IDs...")
            all_notifications = Notification.query.all()
            invalid_refs = []
            
            for notif in all_notifications:
                if notif.recipient_registered_user_id:
                    recipient = RegisteredUser.query.get(notif.recipient_registered_user_id)
                    if not recipient:
                        invalid_refs.append(notif)
            
            print(f"Found {len(invalid_refs)} notifications with invalid recipient references")
            for notif in invalid_refs:
                print(f"  - Notification ID: {notif.notification_id}, Invalid recipient ID: {notif.recipient_registered_user_id}")
            
            # 4. Check for problematic notification (ID 1 from error)
            print("\n4. Checking notification ID 1 (from error message)...")
            notif_1 = Notification.query.get(1)
            if notif_1:
                print(f"  - Notification ID 1 exists:")
                print(f"    Message: {notif_1.message}")
                print(f"    Recipient ID: {notif_1.recipient_registered_user_id}")
                print(f"    Read status: {notif_1.is_read}")
                print(f"    Date: {notif_1.sent_date}")
                
                # Check if recipient exists
                if notif_1.recipient_registered_user_id:
                    recipient = RegisteredUser.query.get(notif_1.recipient_registered_user_id)
                    print(f"    Recipient exists: {recipient is not None}")
                else:
                    print("    Recipient ID is NULL!")
            else:
                print("  - Notification ID 1 does not exist")
                
        except Exception as e:
            print(f"Error during diagnosis: {e}")
            traceback.print_exc()

def fix_notification_issues():
    """Attempt to fix notification database issues"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("\n=== Attempting to Fix Notification Issues ===")
            
            # Option 1: Delete notifications with NULL recipient_registered_user_id
            null_notifications = Notification.query.filter(Notification.recipient_registered_user_id.is_(None)).all()
            
            if null_notifications:
                print(f"\nFound {len(null_notifications)} notifications with NULL recipient IDs")
                print("Options:")
                print("1. Delete these invalid notifications")
                print("2. Skip deletion and manual fix required")
                
                choice = input("Choose option (1 or 2): ").strip()
                
                if choice == "1":
                    for notif in null_notifications:
                        print(f"Deleting notification ID {notif.notification_id}")
                        db.session.delete(notif)
                    
                    db.session.commit()
                    print("Invalid notifications deleted successfully!")
                else:
                    print("Skipping automatic deletion.")
            
            # Option 2: Fix notifications with invalid foreign key references
            all_notifications = Notification.query.all()
            invalid_refs = []
            
            for notif in all_notifications:
                if notif.recipient_registered_user_id:
                    recipient = RegisteredUser.query.get(notif.recipient_registered_user_id)
                    if not recipient:
                        invalid_refs.append(notif)
            
            if invalid_refs:
                print(f"\nFound {len(invalid_refs)} notifications with invalid recipient references")
                print("These notifications reference users that don't exist.")
                print("Options:")
                print("1. Delete these orphaned notifications")
                print("2. Skip deletion")
                
                choice = input("Choose option (1 or 2): ").strip()
                
                if choice == "1":
                    for notif in invalid_refs:
                        print(f"Deleting orphaned notification ID {notif.notification_id}")
                        db.session.delete(notif)
                    
                    db.session.commit()
                    print("Orphaned notifications deleted successfully!")
                else:
                    print("Skipping deletion of orphaned notifications.")
                    
        except Exception as e:
            db.session.rollback()
            print(f"Error during fix: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    print("Notification Database Repair Tool")
    print("=" * 40)
    
    # First, diagnose the issues
    diagnose_notification_issues()
    
    # Ask if user wants to attempt fixes
    print("\n" + "=" * 40)
    fix_choice = input("Would you like to attempt automatic fixes? (y/n): ").strip().lower()
    
    if fix_choice == 'y':
        fix_notification_issues()
    else:
        print("Skipping automatic fixes. Manual intervention may be required.")
    
    print("\nDiagnosis complete!")
