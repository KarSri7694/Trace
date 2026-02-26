"""
Document Encoder - Encodes text and markdown files to vector database
Reads files from file_list_txt.txt and file_list_md.txt and stores them in ChromaDB
"""

import os
import logging
import re
from pathlib import Path
from typing import List, Tuple
from datetime import datetime
import hashlib

from vectordb import create_chroma_client, get_or_create_collection
from get_files import save_file_lists

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentEncoder:
    """Encodes documents from file lists into vector database"""
    
    def __init__(
        self,
        file_lists_folder: str = "temp",
        ocr_result_folder: str = "ocr_result",
        db_path: str = "./chroma_db",
        collection_name: str = "documents",
        scan_directory: str = "."
    ):
        """
        Initialize the document encoder
        
        Args:
            file_lists_folder: Folder containing file_list_*.txt files
            ocr_result_folder: Folder containing OCR result .txt files
            db_path: Path to ChromaDB persistent storage
            collection_name: Name of the ChromaDB collection
            scan_directory: Directory to scan for txt/md files (default: current directory)
        """
        self.file_lists_folder = file_lists_folder
        self.ocr_result_folder = ocr_result_folder
        self.db_path = db_path
        self.collection_name = collection_name
        self.scan_directory = scan_directory
        
        # Lazy initialization - will be created on first use
        self._client = None
        self._collection = None
    
    @property
    def client(self):
        """Lazy load ChromaDB client"""
        if self._client is None:
            logger.info(f"Initializing ChromaDB at {self.db_path}")
            self._client = create_chroma_client(persist_directory=self.db_path)
        return self._client
    
    @property
    def collection(self):
        """Lazy load ChromaDB collection"""
        if self._collection is None:
            logger.info(f"Loading collection: {self.collection_name}")
            
            try:
                self._collection = get_or_create_collection(self.client, self.collection_name)
                
                if self._collection is None:
                    raise RuntimeError(
                        f"Failed to create ChromaDB collection '{self.collection_name}'.\n"
                        f"This may be due to:\n"
                        f"1. Incompatible ChromaDB version\n"
                        f"2. Corrupted database at: {self.db_path}\n"
                        f"3. Collection exists with different embedding function\n"
                        f"\nTry deleting the database folder: {self.db_path}"
                    )
            except Exception as e:
                logger.error(f"Error creating collection: {e}")
                raise RuntimeError(
                    f"Failed to create ChromaDB collection: {str(e)}\n\n"
                    f"Quick fix: Delete the folder '{self.db_path}' and try again."
                )
        
        return self._collection
    
    def get_file_lists(self) -> List[str]:
        """
        Get all file list paths to process
        
        Returns:
            List of file list paths (file_list_txt.txt, file_list_md.txt)
        """
        file_lists = []
        
        # Look for file_list_txt.txt and file_list_md.txt
        for filename in ['file_list_txt.txt', 'file_list_md.txt']:
            file_path = os.path.join(self.file_lists_folder, filename)
            if os.path.exists(file_path):
                file_lists.append(file_path)
                logger.info(f"Found file list: {filename}")
            else:
                logger.warning(f"File list not found: {file_path}")
        
        return file_lists
    
    def get_ocr_files(self) -> List[str]:
        """
        Get all OCR result files from ocr_result folder
        
        Returns:
            List of OCR result file paths
        """
        ocr_files = []
        
        if not os.path.exists(self.ocr_result_folder):
            logger.warning(f"OCR result folder not found: {self.ocr_result_folder}")
            return ocr_files
        
        try:
            for filename in os.listdir(self.ocr_result_folder):
                if filename.endswith('.txt') and filename.startswith('ocr_'):
                    file_path = os.path.join(self.ocr_result_folder, filename)
                    if os.path.isfile(file_path):
                        ocr_files.append(file_path)
            
            logger.info(f"Found {len(ocr_files)} OCR result files")
        except Exception as e:
            logger.error(f"Error reading OCR result folder: {e}")
        
        return ocr_files
    
    def read_file_paths_from_list(self, list_file: str) -> List[str]:
        """
        Read file paths from a file list
        
        Args:
            list_file: Path to the file list
        
        Returns:
            List of file paths
        """
        file_paths = []
        
        try:
            with open(list_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip header lines and empty lines
                    if line and not line.startswith('File List') and not line.startswith('Directory:') and not line.startswith('Timestamp:') and not line.startswith('Total files:') and not line.startswith('='):
                        if os.path.exists(line):
                            file_paths.append(line)
                        else:
                            logger.warning(f"File not found: {line}")
        except Exception as e:
            logger.error(f"Error reading file list {list_file}: {e}")
        
        return file_paths
    
    def read_file_content(self, file_path: str) -> Tuple[str, bool]:
        """
        Read content from a file
        
        Args:
            file_path: Path to the file
        
        Returns:
            Tuple of (content, success)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, True
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                return content, True
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
                return "", False
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return "", False
    
    def generate_document_id(self, file_path: str) -> str:
        """
        Generate a unique document ID based on file path
        
        Args:
            file_path: Path to the file
        
        Returns:
            Unique document ID
        """
        # Use hash of absolute path for consistent ID
        abs_path = os.path.abspath(file_path)
        return hashlib.md5(abs_path.encode()).hexdigest()
    
    def split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using regex
        
        Args:
            text: Text to split
        
        Returns:
            List of sentences
        """
        # Pattern to match sentence boundaries
        # Matches: . ! ? followed by space/newline/end, considering abbreviations
        sentence_pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s+'
        sentences = re.split(sentence_pattern, text)
        return [s.strip() for s in sentences if s.strip()]
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap_sentences: int = 2) -> List[str]:
        """
        Split text into semantic chunks based on sentences and paragraphs
        
        Args:
            text: Text to chunk
            chunk_size: Target size of each chunk in characters
            overlap_sentences: Number of sentences to overlap between chunks
        
        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        
        # First split by paragraphs (double newlines or more)
        paragraphs = re.split(r'\n\s*\n', text)
        
        current_chunk = []
        current_size = 0
        sentence_buffer = []  # For overlap
        
        for paragraph in paragraphs:
            # Split paragraph into sentences
            sentences = self.split_into_sentences(paragraph)
            
            for sentence in sentences:
                sentence_len = len(sentence)
                
                # If adding this sentence exceeds chunk_size and we have content
                if current_size + sentence_len > chunk_size and current_chunk:
                    # Save current chunk
                    chunk_text = ' '.join(current_chunk)
                    chunks.append(chunk_text)
                    
                    # Start new chunk with overlap from previous sentences
                    if overlap_sentences > 0 and sentence_buffer:
                        current_chunk = sentence_buffer[-overlap_sentences:].copy()
                        current_size = sum(len(s) for s in current_chunk)
                    else:
                        current_chunk = []
                        current_size = 0
                    
                    sentence_buffer = current_chunk.copy()
                
                # Add sentence to current chunk
                current_chunk.append(sentence)
                current_size += sentence_len
                
                # Update sentence buffer for overlap
                sentence_buffer.append(sentence)
                if len(sentence_buffer) > overlap_sentences * 2:
                    sentence_buffer.pop(0)
            
            # Add paragraph break marker if not the last paragraph
            if paragraph != paragraphs[-1] and current_chunk:
                current_chunk.append('\n')
        
        # Add remaining chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(chunk_text)
        
        return chunks
    
    def encode_file(self, file_path: str, use_chunking: bool = True, is_ocr: bool = False) -> bool:
        """
        Encode a single file to the vector database
        
        Args:
            file_path: Path to the file
            use_chunking: Whether to split large files into chunks
            is_ocr: Whether this is an OCR result file
        
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Encoding: {Path(file_path).name}")
        
        # Read file content
        content, success = self.read_file_content(file_path)
        if not success or not content.strip():
            logger.warning(f"Skipping empty or unreadable file: {file_path}")
            return False
        
        # Generate metadata
        file_name = Path(file_path).name
        file_ext = Path(file_path).suffix
        file_size = len(content)
        
        metadata = {
            "filename": file_name,
            "filepath": str(Path(file_path).absolute()),
            "extension": file_ext,
            "size": file_size,
            "encoded_at": datetime.now().isoformat(),
            "is_ocr": is_ocr
        }
        
        # For OCR files, extract original filename from ocr_<name>.txt
        if is_ocr and file_name.startswith('ocr_'):
            original_name = file_name[4:-4]  # Remove 'ocr_' prefix and '.txt' suffix
            metadata["original_filename"] = original_name
            metadata["source_type"] = "ocr"
        
        try:
            if use_chunking and len(content) > 1000:
                # Split into chunks for large files
                chunks = self.chunk_text(content)
                logger.info(f"  Split into {len(chunks)} chunks")
                
                for idx, chunk in enumerate(chunks):
                    chunk_id = f"{self.generate_document_id(file_path)}_chunk{idx}"
                    chunk_metadata = metadata.copy()
                    chunk_metadata["chunk_index"] = idx
                    chunk_metadata["total_chunks"] = len(chunks)
                    
                    self.collection.add(
                        documents=[chunk],
                        ids=[chunk_id],
                        metadatas=[chunk_metadata]
                    )
            else:
                # Add whole document
                doc_id = self.generate_document_id(file_path)
                self.collection.add(
                    documents=[content],
                    ids=[doc_id],
                    metadatas=[metadata]
                )
            
            logger.info(f"  ✓ Encoded successfully")
            return True
            
        except Exception as e:
            logger.error(f"  ✗ Error encoding {file_path}: {e}")
            return False
    
    def encode_all_documents(self, use_chunking: bool = True, include_ocr: bool = True, progress_callback=None):
        """
        Encode all documents from file lists and OCR results
        
        Args:
            use_chunking: Whether to split large files into chunks
            include_ocr: Whether to include OCR result files
            progress_callback: Optional callback(current, total, message)
        
        Returns:
            Statistics dictionary
        """
        # First, scan directory and create file lists for txt and md files
        logger.info(f"Scanning {self.scan_directory} for txt and md files...")
        try:
            result = save_file_lists(
                directory=self.scan_directory,
                extensions=['.txt', '.md'],
                output_folder=self.file_lists_folder,
                recursive=False
            )
            logger.info(f"Created {len(result['saved_lists'])} file list(s) with {result['total_files']} files")
        except Exception as e:
            logger.warning(f"Failed to create file lists: {e}")
        
        # Get all file lists
        file_lists = self.get_file_lists()
        
        # Collect all file paths from file lists
        all_files = []
        for file_list in file_lists:
            file_paths = self.read_file_paths_from_list(file_list)
            all_files.extend(file_paths)
            logger.info(f"Loaded {len(file_paths)} files from {Path(file_list).name}")
        
        # Add OCR result files
        ocr_files = []
        if include_ocr:
            ocr_files = self.get_ocr_files()
            all_files.extend(ocr_files)
        
        total_files = len(all_files)
        
        if total_files == 0:
            logger.error("No files found to encode!")
            return {
                "total_files": 0,
                "successful": 0,
                "failed": 0,
                "skipped": 0,
                "ocr_files": 0
            }
        
        logger.info(f"\nTotal files to encode: {total_files}")
        if ocr_files:
            logger.info(f"  - Regular files: {total_files - len(ocr_files)}")
            logger.info(f"  - OCR result files: {len(ocr_files)}")
        
        # Encode each file
        stats = {
            "total_files": total_files,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "ocr_files": len(ocr_files)
        }
        
        for idx, file_path in enumerate(all_files, 1):
            if progress_callback:
                progress_callback(idx, total_files, f"Encoding {Path(file_path).name}")
            
            # Check if this is an OCR file
            is_ocr = file_path in ocr_files
            
            success = self.encode_file(file_path, use_chunking, is_ocr)
            
            if success:
                stats["successful"] += 1
            else:
                stats["failed"] += 1
        
        logger.info(f"\n{'='*80}")
        logger.info(f"ENCODING COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"Total files: {stats['total_files']}")
        logger.info(f"Successfully encoded: {stats['successful']}")
        logger.info(f"Failed: {stats['failed']}")
        if stats['ocr_files'] > 0:
            logger.info(f"OCR result files: {stats['ocr_files']}")
        logger.info(f"Database location: {self.db_path}")
        logger.info(f"Collection: {self.collection_name}")
        logger.info(f"Total documents in collection: {self.collection.count()}")
        
        return stats
    
    def search_similar(self, query: str, n_results: int = 5):
        """
        Search for similar documents
        
        Args:
            query: Search query
            n_results: Number of results to return
        
        Returns:
            Query results (filtered to only include results with similarity > 0.4)
        """
        try:
            # Request more results to account for filtering
            # This ensures we still get enough results after filtering
            fetch_results = n_results * 3  # Fetch 3x to have buffer for filtering
            
            results = self.collection.query(
                query_texts=[query],
                n_results=fetch_results
            )
            
            # Filter results based on similarity threshold (0.4)
            # Similarity = 1 - distance, so distance < 0.6 means similarity > 0.4
            if results and results['distances'] and results['distances'][0]:
                filtered_docs = []
                filtered_metadatas = []
                filtered_distances = []
                filtered_ids = []
                
                for idx, distance in enumerate(results['distances'][0]):
                    similarity = 1 - distance
                    if similarity > 0.4:
                        filtered_docs.append(results['documents'][0][idx])
                        filtered_metadatas.append(results['metadatas'][0][idx])
                        filtered_distances.append(distance)
                        if 'ids' in results and results['ids']:
                            filtered_ids.append(results['ids'][0][idx])
                
                # Limit to requested number of results
                filtered_docs = filtered_docs[:n_results]
                filtered_metadatas = filtered_metadatas[:n_results]
                filtered_distances = filtered_distances[:n_results]
                filtered_ids = filtered_ids[:n_results]
                
                # Reconstruct results dictionary
                filtered_results = {
                    'documents': [filtered_docs],
                    'metadatas': [filtered_metadatas],
                    'distances': [filtered_distances]
                }
                if filtered_ids:
                    filtered_results['ids'] = [filtered_ids]
                
                return filtered_results
            
            return results
        except Exception as e:
            logger.error(f"Error searching: {e}")
            return None
    
    def get_collection_stats(self):
        """Get statistics about the collection"""
        try:
            count = self.collection.count()
            logger.info(f"Collection '{self.collection_name}' contains {count} documents")
            return {"count": count}
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"count": 0}
    
    def get_all_documents(self):
        """Get all documents from the collection grouped by file"""
        try:
            # Get all documents from collection
            results = self.collection.get()
            
            # Group by file path
            files_dict = {}
            
            if results and results['documents']:
                for doc, metadata in zip(results['documents'], results['metadatas']):
                    filepath = metadata.get('filepath', 'Unknown')
                    filename = metadata.get('filename', 'Unknown')
                    
                    if filepath not in files_dict:
                        files_dict[filepath] = {
                            'filename': filename,
                            'metadata': metadata,
                            'content': doc,
                            'chunks': [doc]
                        }
                    else:
                        # Append chunk to existing file
                        files_dict[filepath]['chunks'].append(doc)
                        # Combine content
                        files_dict[filepath]['content'] += "\n" + doc
            
            logger.info(f"Retrieved {len(files_dict)} unique files from collection")
            return files_dict
            
        except Exception as e:
            logger.error(f"Error getting all documents: {e}")
            return {}
    
    def reset_database(self):
        """
        Reset the database collection (delete and recreate)
        Useful for fixing corrupted collections or incompatible versions
        """
        from vectordb import reset_collection
        
        try:
            logger.info(f"Resetting collection: {self.collection_name}")
            self._collection = None  # Clear cached collection
            
            new_collection = reset_collection(self.client, self.collection_name)
            
            if new_collection is None:
                raise RuntimeError("Failed to reset collection")
            
            self._collection = new_collection
            logger.info("Collection reset successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting collection: {e}")
            return False


def main():
    """Main function to encode documents"""
    import sys
    
    try:
        # Create encoder with default settings
        encoder = DocumentEncoder(
            file_lists_folder="temp",
            ocr_result_folder="ocr_result",
            db_path="./chroma_db",
            collection_name="documents"
        )
        
        # Encode all documents
        stats = encoder.encode_all_documents(
            use_chunking=True,
            include_ocr=True
        )
        
        print(f"\n{'='*80}")
        print(f"Encoding completed successfully!")
        print(f"{'='*80}")
        
    except RuntimeError as e:
        print(f"\n{'='*80}")
        print(f"ERROR: {e}")
        print(f"{'='*80}")
        print(f"\nQUICK FIX:")
        print(f"1. Delete the folder: ./chroma_db")
        print(f"2. Run this script again")
        print(f"\nAlternatively, you can reset the database programmatically:")
        print(f"  encoder.reset_database()")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
