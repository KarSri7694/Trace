"""
Database Reset Utility - Fix ChromaDB Collection Errors

This script resets the ChromaDB collection if you encounter errors like:
  "Failed to create ChromaDB collection"

Run this script to delete and recreate the collection.
"""

import os
import shutil
import sys


def reset_database(db_path="./chroma_db"):
    """Reset the ChromaDB database by deleting and recreating it"""
    
    print("=" * 80)
    print("ChromaDB Database Reset Utility")
    print("=" * 80)
    print()
    
    if os.path.exists(db_path):
        print(f"Found database at: {db_path}")
        print(f"Database size: {get_folder_size(db_path):.2f} MB")
        print()
        
        response = input("Are you sure you want to delete this database? (yes/no): ")
        
        if response.lower() in ['yes', 'y']:
            try:
                print(f"\nDeleting database folder: {db_path}")
                shutil.rmtree(db_path)
                print("✓ Database deleted successfully!")
                print()
                print("Next steps:")
                print("1. Run your encoding script again")
                print("2. The database will be recreated automatically")
                print()
                return True
            except Exception as e:
                print(f"✗ Error deleting database: {e}")
                print()
                print("Manual fix:")
                print(f"1. Close all programs using the database")
                print(f"2. Delete the folder manually: {os.path.abspath(db_path)}")
                return False
        else:
            print("Operation cancelled.")
            return False
    else:
        print(f"Database not found at: {db_path}")
        print("No action needed - database will be created on next encoding.")
        return True


def get_folder_size(folder_path):
    """Get the size of a folder in MB"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.exists(filepath):
                total_size += os.path.getsize(filepath)
    return total_size / (1024 * 1024)  # Convert to MB


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Reset ChromaDB database to fix collection errors"
    )
    parser.add_argument(
        "--db-path",
        default="./chroma_db",
        help="Path to ChromaDB database (default: ./chroma_db)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete without confirmation"
    )
    
    args = parser.parse_args()
    
    if args.force:
        if os.path.exists(args.db_path):
            try:
                shutil.rmtree(args.db_path)
                print(f"✓ Deleted database: {args.db_path}")
            except Exception as e:
                print(f"✗ Error: {e}")
                sys.exit(1)
        else:
            print(f"Database not found: {args.db_path}")
    else:
        success = reset_database(args.db_path)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
