"""
File Encryptor - Encrypts and decrypts files using AES-256 encryption
Uses pyaescrypt for secure file encryption with password protection
"""

import os
import pyAesCrypt
import logging
from pathlib import Path
from typing import Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FileEncryptor:
    """Handles file encryption and decryption using AES-256"""
    
    def __init__(self, vault_directory: str = "secure_vault", buffer_size: int = 64*1024):
        """
        Initialize file encryptor
        
        Args:
            vault_directory: Directory to store encrypted files
            buffer_size: Buffer size for encryption (default: 64KB)
        """
        self.vault_directory = vault_directory
        self.buffer_size = buffer_size
        
        # Create vault directory if it doesn't exist
        os.makedirs(vault_directory, exist_ok=True)
    
    def encrypt_file(
        self,
        file_path: str,
        password: str,
        output_path: Optional[str] = None,
        delete_original: bool = False
    ) -> Tuple[bool, str, str]:
        """
        Encrypt a file using AES-256
        
        Args:
            file_path: Path to file to encrypt
            password: Password for encryption
            output_path: Optional custom output path (defaults to vault directory)
            delete_original: Whether to securely delete original file after encryption
            
        Returns:
            Tuple of (success, encrypted_file_path, message)
        """
        try:
            # Validate input file
            if not os.path.exists(file_path):
                return False, "", f"File not found: {file_path}"
            
            if not password or len(password) < 8:
                return False, "", "Password must be at least 8 characters long"
            
            # Determine output path
            if output_path is None:
                filename = os.path.basename(file_path)
                output_path = os.path.join(self.vault_directory, f"{filename}.aes")
            
            # If output file already exists, add number suffix
            if os.path.exists(output_path):
                base, ext = os.path.splitext(output_path)
                counter = 1
                while os.path.exists(f"{base}_{counter}{ext}"):
                    counter += 1
                output_path = f"{base}_{counter}{ext}"
            
            logger.info(f"Encrypting {file_path} to {output_path}")
            
            # Encrypt the file
            pyAesCrypt.encryptFile(
                file_path,
                output_path,
                password,
                self.buffer_size
            )
            
            logger.info(f"Encryption successful: {output_path}")
            
            # Delete original file if requested
            if delete_original:
                try:
                    self._secure_delete(file_path)
                    logger.info(f"Original file securely deleted: {file_path}")
                    deletion_msg = " Original file deleted."
                except Exception as e:
                    logger.warning(f"Failed to delete original file: {e}")
                    deletion_msg = " Warning: Original file could not be deleted."
            else:
                deletion_msg = ""
            
            return True, output_path, f"File encrypted successfully!{deletion_msg}"
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return False, "", f"Encryption failed: {str(e)}"
    
    def decrypt_file(
        self,
        encrypted_file_path: str,
        password: str,
        output_path: Optional[str] = None,
        delete_encrypted: bool = False
    ) -> Tuple[bool, str, str]:
        """
        Decrypt an encrypted file
        
        Args:
            encrypted_file_path: Path to encrypted file (.aes)
            password: Password for decryption
            output_path: Optional custom output path
            delete_encrypted: Whether to delete encrypted file after successful decryption
            
        Returns:
            Tuple of (success, decrypted_file_path, message)
        """
        try:
            # Validate input file
            if not os.path.exists(encrypted_file_path):
                return False, "", f"Encrypted file not found: {encrypted_file_path}"
            
            if not password:
                return False, "", "Password is required for decryption"
            
            # Determine output path
            if output_path is None:
                # Remove .aes extension and restore original filename
                if encrypted_file_path.endswith('.aes'):
                    output_path = encrypted_file_path[:-4]
                else:
                    output_path = encrypted_file_path + '.decrypted'
            
            # If output file already exists, add suffix
            if os.path.exists(output_path):
                base, ext = os.path.splitext(output_path)
                counter = 1
                while os.path.exists(f"{base}_decrypted_{counter}{ext}"):
                    counter += 1
                output_path = f"{base}_decrypted_{counter}{ext}"
            
            logger.info(f"Decrypting {encrypted_file_path} to {output_path}")
            
            # Decrypt the file
            pyAesCrypt.decryptFile(
                encrypted_file_path,
                output_path,
                password,
                self.buffer_size
            )
            
            logger.info(f"Decryption successful: {output_path}")
            
            # Delete encrypted file if requested
            if delete_encrypted:
                try:
                    os.remove(encrypted_file_path)
                    logger.info(f"Encrypted file deleted: {encrypted_file_path}")
                    deletion_msg = " Encrypted file deleted."
                except Exception as e:
                    logger.warning(f"Failed to delete encrypted file: {e}")
                    deletion_msg = " Warning: Encrypted file could not be deleted."
            else:
                deletion_msg = ""
            
            return True, output_path, f"File decrypted successfully!{deletion_msg}"
            
        except ValueError as e:
            # Wrong password or corrupted file
            logger.error(f"Decryption failed - likely wrong password: {e}")
            return False, "", "Decryption failed: Invalid password or corrupted file"
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return False, "", f"Decryption failed: {str(e)}"
    
    def _secure_delete(self, file_path: str):
        """
        Securely delete a file by overwriting with random data before deletion
        
        Args:
            file_path: Path to file to delete
        """
        try:
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Overwrite with random data (3 passes)
            with open(file_path, 'wb') as f:
                for _ in range(3):
                    f.seek(0)
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())
            
            # Delete the file
            os.remove(file_path)
            
        except Exception as e:
            logger.error(f"Secure deletion failed: {e}")
            # Fallback to regular deletion
            if os.path.exists(file_path):
                os.remove(file_path)
    
    def list_encrypted_files(self) -> list:
        """
        List all encrypted files in the vault
        
        Returns:
            List of encrypted file paths
        """
        try:
            encrypted_files = []
            for filename in os.listdir(self.vault_directory):
                if filename.endswith('.aes'):
                    file_path = os.path.join(self.vault_directory, filename)
                    encrypted_files.append(file_path)
            return encrypted_files
        except Exception as e:
            logger.error(f"Failed to list encrypted files: {e}")
            return []
    
    def get_vault_stats(self) -> dict:
        """
        Get statistics about the vault
        
        Returns:
            Dictionary with vault statistics
        """
        try:
            encrypted_files = self.list_encrypted_files()
            total_size = sum(os.path.getsize(f) for f in encrypted_files)
            
            return {
                'vault_path': os.path.abspath(self.vault_directory),
                'total_files': len(encrypted_files),
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2)
            }
        except Exception as e:
            logger.error(f"Failed to get vault stats: {e}")
            return {
                'vault_path': self.vault_directory,
                'total_files': 0,
                'total_size_bytes': 0,
                'total_size_mb': 0
            }


# Convenience functions for standalone use
def encrypt_file(file_path: str, password: str, vault_dir: str = "secure_vault") -> Tuple[bool, str, str]:
    """
    Convenience function to encrypt a file
    
    Args:
        file_path: File to encrypt
        password: Encryption password
        vault_dir: Vault directory
        
    Returns:
        Tuple of (success, encrypted_path, message)
    """
    encryptor = FileEncryptor(vault_directory=vault_dir)
    return encryptor.encrypt_file(file_path, password)


def decrypt_file(encrypted_path: str, password: str) -> Tuple[bool, str, str]:
    """
    Convenience function to decrypt a file
    
    Args:
        encrypted_path: Encrypted file path
        password: Decryption password
        
    Returns:
        Tuple of (success, decrypted_path, message)
    """
    encryptor = FileEncryptor()
    return encryptor.decrypt_file(encrypted_path, password)


if __name__ == "__main__":
    # Example usage
    print("File Encryptor - AES-256 Encryption")
    print("=" * 60)
    
    encryptor = FileEncryptor()
    stats = encryptor.get_vault_stats()
    
    print(f"Vault Directory: {stats['vault_path']}")
    print(f"Encrypted Files: {stats['total_files']}")
    print(f"Total Size: {stats['total_size_mb']} MB")
    print("=" * 60)
