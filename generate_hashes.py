"""
Generate Hash Baseline - Creates baseline hash file for integrity checking
Run this after installing or updating the application
"""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path


def calculate_file_hash(filepath: str) -> str:
    """Calculate SHA-256 hash of a file"""
    sha256_hash = hashlib.sha256()
    
    try:
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"Error calculating hash for {filepath}: {e}")
        return ""


def generate_baseline(output_file: str = "file_hashes.json"):
    """
    Generate baseline hash file for all protected Python files
    
    Args:
        output_file: Path to output JSON file
    """
    protected_files = [
        'pipeline.py',
        'llm.py',
        'glm_ocr.py',
        'get_files.py',
        'encode_documents.py',
        'vectordb.py',
        'embedding_creator.py',
        'ui.py'
    ]
    
    print("=" * 60)
    print("TRACE - Generating Hash Baseline")
    print("=" * 60)
    print()
    
    hashes = {}
    missing_files = []
    
    for filename in protected_files:
        if not os.path.exists(filename):
            print(f"⚠️  {filename} - NOT FOUND")
            missing_files.append(filename)
            continue
        
        file_hash = calculate_file_hash(filename)
        if file_hash:
            hashes[filename] = file_hash
            file_size = os.path.getsize(filename)
            print(f"✓ {filename}")
            print(f"  Hash: {file_hash[:16]}...")
            print(f"  Size: {file_size:,} bytes")
        else:
            print(f"✗ {filename} - FAILED TO HASH")
            missing_files.append(filename)
    
    print()
    print("=" * 60)
    
    if missing_files:
        print(f"\n⚠️  Warning: {len(missing_files)} file(s) not found:")
        for f in missing_files:
            print(f"  • {f}")
        print("\nContinuing with available files...")
    
    # Add metadata
    baseline_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_files": len(hashes),
            "generator_version": "1.0"
        },
        "hashes": hashes
    }
    
    # Save to file
    try:
        # For easier reading, save hashes directly (not nested under "hashes" key)
        with open(output_file, 'w') as f:
            json.dump(hashes, f, indent=2)
        
        # Save metadata separately
        metadata_file = output_file.replace('.json', '_metadata.json')
        with open(metadata_file, 'w') as f:
            json.dump(baseline_data['metadata'], f, indent=2)
        
        print(f"\n✓ Baseline saved to: {output_file}")
        print(f"✓ Metadata saved to: {metadata_file}")
        print(f"\nTotal files protected: {len(hashes)}")
        print("\n" + "=" * 60)
        print("Integrity baseline generated successfully!")
        
    except Exception as e:
        print(f"\n✗ Error saving baseline: {e}")
        return False
    
    return True


if __name__ == "__main__":
    import sys
    
    # Check if custom output file specified
    output_file = "file_hashes.json"
    if len(sys.argv) > 1:
        output_file = sys.argv[1]
    
    # Confirm before overwriting existing baseline
    if os.path.exists(output_file):
        print(f"⚠️  Warning: {output_file} already exists!")
        response = input("Overwrite existing baseline? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("Cancelled.")
            sys.exit(0)
        print()
    
    success = generate_baseline(output_file)
    sys.exit(0 if success else 1)
