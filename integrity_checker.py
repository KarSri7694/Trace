"""
Integrity Checker - Verifies program files haven't been tampered with
Calculates SHA-256 hashes of all Python files and compares against known baseline
"""

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class IntegrityChecker:
    """Checks file integrity using SHA-256 hashes"""
    
    def __init__(self, baseline_file: str = "file_hashes.json"):
        """
        Initialize integrity checker
        
        Args:
            baseline_file: Path to JSON file containing baseline hashes
        """
        self.baseline_file = baseline_file
        self.baseline_hashes = {}
        self.protected_files = [
            'pipeline.py',
            'llm.py',
            'glm_ocr.py',
            'get_files.py',
            'encode_documents.py',
            'vectordb.py',
            'embedding_creator.py',
            'ui.py'
        ]
    
    def calculate_file_hash(self, filepath: str) -> str:
        """
        Calculate SHA-256 hash of a file
        
        Args:
            filepath: Path to the file
            
        Returns:
            Hex digest of the file hash
        """
        sha256_hash = hashlib.sha256()
        
        try:
            with open(filepath, "rb") as f:
                # Read file in chunks to handle large files
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            print(f"Error calculating hash for {filepath}: {e}")
            return ""
    
    def load_baseline(self) -> bool:
        """
        Load baseline hashes from file
        
        Returns:
            True if loaded successfully, False otherwise
        """
        if not os.path.exists(self.baseline_file):
            print(f"WARNING: Baseline hash file '{self.baseline_file}' not found!")
            print("Run 'python generate_hashes.py' to create baseline.")
            return False
        
        try:
            with open(self.baseline_file, 'r') as f:
                self.baseline_hashes = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading baseline hashes: {e}")
            return False
    
    def verify_file(self, filepath: str) -> Tuple[bool, str]:
        """
        Verify a single file against baseline
        
        Args:
            filepath: Path to file to verify
            
        Returns:
            Tuple of (is_valid, message)
        """
        filename = os.path.basename(filepath)
        
        if filename not in self.baseline_hashes:
            return False, f"No baseline hash found for {filename}"
        
        current_hash = self.calculate_file_hash(filepath)
        expected_hash = self.baseline_hashes[filename]
        
        if current_hash != expected_hash:
            return False, f"Hash mismatch for {filename}"
        
        return True, f"{filename} verified"
    
    def verify_all(self, verbose: bool = True) -> Tuple[bool, List[str]]:
        """
        Verify all protected files
        
        Args:
            verbose: Print verification messages
            
        Returns:
            Tuple of (all_valid, failed_files)
        """
        if not self.load_baseline():
            return False, ["Baseline not loaded"]
        
        failed_files = []
        
        for filename in self.protected_files:
            if not os.path.exists(filename):
                msg = f"CRITICAL: Required file '{filename}' is missing!"
                failed_files.append(msg)
                if verbose:
                    print(msg)
                continue
            
            is_valid, message = self.verify_file(filename)
            
            if verbose:
                status = "✓" if is_valid else "✗"
                print(f"{status} {message}")
            
            if not is_valid:
                failed_files.append(message)
        
        return len(failed_files) == 0, failed_files
    
    def verify_or_exit(self):
        """
        Verify all files and exit if any verification fails
        Should be called at program startup
        """
        print("=" * 60)
        print("TRACE - Integrity Verification")
        print("=" * 60)
        
        all_valid, failed_files = self.verify_all(verbose=True)
        
        print("=" * 60)
        
        if all_valid:
            print("✓ All files verified successfully")
            print("=" * 60)
            return True
        else:
            print("\n🚨 INTEGRITY CHECK FAILED!")
            print("=" * 60)
            print("\nThe following files failed verification:")
            for failure in failed_files:
                print(f"  • {failure}")
            
            print("\n⚠️  WARNING: Program files may have been tampered with!")
            print("Possible reasons:")
            print("  1. Files were modified after baseline was generated")
            print("  2. Files were corrupted")
            print("  3. Malicious tampering")
            
            print("\nRecommended actions:")
            print("  1. If you made legitimate changes, regenerate baseline:")
            print("     python generate_hashes.py")
            print("  2. Otherwise, restore files from a trusted backup")
            
            print("\n❌ EXECUTION BLOCKED FOR SECURITY")
            print("=" * 60)
            
            sys.exit(1)


def check_integrity():
    """
    Convenience function to check integrity and exit if invalid
    Call this at the start of your main program
    """
    checker = IntegrityChecker()
    checker.verify_or_exit()


if __name__ == "__main__":
    # Standalone execution - verify and report
    checker = IntegrityChecker()
    checker.verify_or_exit()
