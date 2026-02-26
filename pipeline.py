import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from get_files import get_files_by_extension, save_file_lists
from glm_ocr import GLMOCRProcessor
from llm import LlamaCppClient
from encode_documents import DocumentEncoder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PrivacyScanner:
    """Pipeline for scanning files for personal/secret information using OCR and LLM"""
    
    def __init__(
        self,
        llm_base_url: str = "http://localhost:8080",
        ocr_model_path: str = "zai-org/GLM-OCR",
        output_folder: str = "ocr_result",
        enable_encoding: bool = True,
        enable_ocr: bool = True,
        db_path: str = "./chroma_db"
    ):
        """
        Initialize the privacy scanner pipeline
        
        Args:
            llm_base_url: URL for llama.cpp server
            ocr_model_path: Path to GLM-OCR model
            output_folder: Folder to save OCR results
            enable_encoding: Whether to encode OCR results to vector database
            enable_ocr: Whether to run OCR on images
            db_path: Path to ChromaDB storage
        """
        self.llm_client = None
        self.ocr_processor = GLMOCRProcessor(model_path=ocr_model_path) if enable_ocr else None
        self.output_folder = output_folder
        self.llm_base_url = llm_base_url
        self.enable_encoding = enable_encoding
        self.enable_ocr = enable_ocr
        self.db_path = db_path
        self.document_encoder = None
        
        os.makedirs(output_folder, exist_ok=True)
    
    def initialize_llm(self) -> bool:
        """Initialize the LLM client and check if server is running"""
        try:
            logger.info("Initializing LLM client...")
            self.llm_client = LlamaCppClient(base_url=self.llm_base_url)
            
            if not self.llm_client.check_server_status():
                logger.error("LLM server is not responding")
                return False
            
            logger.info("LLM client initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            return False
    
    def initialize_ocr(self) -> bool:
        """Initialize the OCR model using GLMOCRProcessor"""
        if not self.enable_ocr:
            logger.info("OCR is disabled, skipping OCR initialization")
            return True
        
        if self.ocr_processor is None:
            logger.error("OCR processor not available")
            return False
        
        try:
            return self.ocr_processor.load_model()
        except Exception as e:
            logger.error(f"Failed to initialize OCR: {e}")
            return False
    
    def unload_ocr(self):
        """Unload OCR model to free memory using GLMOCRProcessor"""
        if self.ocr_processor is not None:
            self.ocr_processor.unload_model()
    
    def encode_ocr_results(self, scan_directory: str = ".", progress_callback=None) -> Dict:
        """
        Encode all OCR results, text files, and markdown files to vector database
        Should be called after OCR model is unloaded to free memory
        
        Args:
            scan_directory: Directory to scan for txt/md files (default: current directory)
            progress_callback: Optional callback function(current, total, message)
        
        Returns:
            Encoding statistics dictionary
        """
        if not self.enable_encoding:
            logger.info("Document encoding is disabled")
            return {"total_files": 0, "successful": 0, "failed": 0}
        
        logger.info("Starting document encoding...")
        
        # First, scan for txt and md files and create file lists
        if progress_callback:
            progress_callback(88, 100, "Scanning for text and markdown files...")
        
        try:
            result = save_file_lists(
                directory=scan_directory,
                extensions=['.txt', '.md'],
                output_folder='temp',
                recursive=False
            )
            logger.info(f"Created file lists: {result['saved_lists']}")
        except Exception as e:
            logger.warning(f"Failed to create file lists: {e}")
        
        if progress_callback:
            progress_callback(90, 100, "Initializing embedding model...")
        
        # Create encoder (lazy loading - model loads on first use)
        self.document_encoder = DocumentEncoder(
            ocr_result_folder=self.output_folder,
            db_path=self.db_path
        )
        
        if progress_callback:
            progress_callback(92, 100, "Collecting documents to encode...")
        
        # Collect all files to encode
        all_files = []
        
        # Get OCR files
        ocr_files = self.document_encoder.get_ocr_files()
        ocr_count = len(ocr_files)
        all_files.extend([(f, True) for f in ocr_files])  # (file_path, is_ocr)
        logger.info(f"Found {ocr_count} OCR result files")
        
        # Get files from file lists (txt and md)
        file_lists = self.document_encoder.get_file_lists()
        file_list_count = 0
        for file_list in file_lists:
            file_paths = self.document_encoder.read_file_paths_from_list(file_list)
            all_files.extend([(f, False) for f in file_paths])  # (file_path, is_ocr)
            file_list_count += len(file_paths)
            logger.info(f"Found {len(file_paths)} files from {Path(file_list).name}")
        
        if not all_files:
            logger.warning("No files found to encode")
            return {"total_files": 0, "successful": 0, "failed": 0, "ocr_files": 0, "text_files": 0}
        
        logger.info(f"Total files to encode: {len(all_files)} (OCR: {ocr_count}, Text/MD: {file_list_count})")
        
        if progress_callback:
            progress_callback(93, 100, f"Encoding {len(all_files)} documents to vector database...")
        
        # Encode each file
        stats = {
            "total_files": len(all_files),
            "successful": 0,
            "failed": 0,
            "ocr_files": ocr_count,
            "text_files": file_list_count
        }
        
        for idx, (file_path, is_ocr) in enumerate(all_files, 1):
            if idx % 10 == 0 and progress_callback:
                progress = 93 + int((idx / len(all_files)) * 5)
                progress_callback(progress, 100, f"Encoding {idx}/{len(all_files)}...")
            
            success = self.document_encoder.encode_file(file_path, use_chunking=True, is_ocr=is_ocr)
            
            if success:
                stats["successful"] += 1
            else:
                stats["failed"] += 1
        
        logger.info(f"Encoding complete: {stats['successful']}/{stats['total_files']} files encoded")
        return stats
    
    def get_image_files(self, directory: str, recursive: bool = False) -> List[str]:
        """
        Get image files from directory
        
        Args:
            directory: Directory path to scan
            recursive: Whether to scan subdirectories
        
        Returns:
            List of image file paths
        """
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        logger.info(f"Scanning for images in: {directory} (recursive={recursive})")
        
        image_files = get_files_by_extension(directory, image_extensions, recursive)
        logger.info(f"Found {len(image_files)} image(s)")
        
        return image_files
    
    def get_text_files(self, directory: str, recursive: bool = False) -> List[str]:
        """
        Get text and markdown files from directory
        
        Args:
            directory: Directory path to scan
            recursive: Whether to scan subdirectories
        
        Returns:
            List of text/md file paths
        """
        text_extensions = ['.txt', '.md']
        logger.info(f"Scanning for text/md files in: {directory} (recursive={recursive})")
        
        text_files = get_files_by_extension(directory, text_extensions, recursive)
        logger.info(f"Found {len(text_files)} text/md file(s)")
        
        return text_files
    
    def analyze_text_file(self, file_path: str) -> Dict:
        """
        Read and analyze a text/md file for privacy concerns
        
        Args:
            file_path: Path to the text file
        
        Returns:
            Dictionary containing analysis results
        """
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Skip empty files
            if not content.strip():
                logger.warning(f"Skipping empty file: {file_path}")
                return None
            
            # Analyze with LLM
            analysis = self.analyze_text_for_privacy(
                content,
                filename=Path(file_path).name
            )
            analysis['file_path'] = file_path
            analysis['file_type'] = 'text/markdown'
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            return {
                "filename": Path(file_path).name,
                "file_path": file_path,
                "file_type": "text/markdown",
                "contains_sensitive_info": False,
                "risk_level": "error",
                "detected_categories": [],
                "specific_findings": [f"Error: {str(e)}"],
                "recommendations": ["Manual review required"],
                "timestamp": datetime.now().isoformat()
            }
    
    def run_ocr_on_image(self, image_path: str) -> Tuple[str, str]:
        """
        Run OCR on a single image using GLMOCRProcessor
        
        Args:
            image_path: Path to the image file
        
        Returns:
            Tuple of (OCR text, output file path)
        """
        if not self.enable_ocr or self.ocr_processor is None:
            logger.warning("OCR is disabled, skipping image processing")
            return "", ""
        
        try:
            # Use the GLMOCRProcessor to process and save
            ocr_text, output_path = self.ocr_processor.process_and_save(
                image_path,
                self.output_folder,
                prompt="Text Recognition:"
            )
            return ocr_text, output_path
        except Exception as e:
            logger.error(f"Error during OCR processing: {e}")
            raise
    
    def analyze_text_for_privacy(self, text: str, filename: str = "") -> Dict:
        """
        Analyze text using LLM to detect personal/secret information
        
        Args:
            text: Text to analyze
            filename: Optional filename for context
        
        Returns:
            Dictionary containing analysis results
        """
        if self.llm_client is None:
            raise RuntimeError("LLM client not initialized. Call initialize_llm() first.")
        
        logger.info(f"Analyzing text for privacy concerns: {filename}")
        
        try:
            # Use the built-in privacy analysis method from LlamaCppClient
            analysis = self.llm_client.analyze_privacy(
                text=text,
                filename=filename,
                context="OCR extracted from image"
            )
            
            # Add timestamp
            analysis['timestamp'] = datetime.now().isoformat()
            
            # Handle error responses
            if "error" in analysis:
                logger.error(f"LLM analysis error: {analysis.get('error')}")
                return {
                    "filename": filename,
                    "contains_sensitive_info": False,
                    "risk_level": "error",
                    "detected_categories": [],
                    "specific_findings": [f"Error: {analysis.get('error')}"],
                    "recommendations": ["Analysis failed - manual review required"],
                    "timestamp": datetime.now().isoformat()
                }
            
            logger.info(f"Analysis completed: Risk level = {analysis.get('risk_level', 'unknown')}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error during LLM analysis: {e}")
            return {
                "filename": filename,
                "contains_sensitive_info": False,
                "risk_level": "error",
                "detected_categories": [],
                "specific_findings": [f"Error: {str(e)}"],
                "recommendations": ["Analysis failed - manual review required"],
                "timestamp": datetime.now().isoformat()
            }
    
    def scan_folder(
        self,
        directory: str,
        recursive: bool = False,
        progress_callback=None
    ) -> List[Dict]:
        """
        Complete pipeline: scan folder, run OCR, analyze with LLM
        
        Args:
            directory: Directory path to scan
            recursive: Whether to scan subdirectories
            progress_callback: Optional callback function(current, total, message)
        
        Returns:
            List of analysis results for each image
        """
        results = []
        
        # Check if OCR is enabled
        if not self.enable_ocr:
            logger.warning("OCR is disabled - no image processing will be performed")
            if progress_callback:
                progress_callback(0, 100, "OCR is disabled, analyzing text files...")
            
            # Initialize LLM for text file analysis
            if progress_callback:
                progress_callback(10, 100, "Connecting to LLM server...")
            
            if not self.initialize_llm():
                logger.error("Failed to initialize LLM client")
                if progress_callback:
                    progress_callback(100, 100, "LLM initialization failed")
                return results
            
            # Analyze text/markdown files
            if progress_callback:
                progress_callback(20, 100, "Scanning for text/markdown files...")
            
            text_files = self.get_text_files(directory, recursive)
            
            if text_files:
                logger.info(f"Analyzing {len(text_files)} text/markdown file(s)...")
                total_text_files = len(text_files)
                
                for idx, text_file in enumerate(text_files, 1):
                    try:
                        progress = 20 + int((idx / total_text_files) * 60)
                        if progress_callback:
                            progress_callback(
                                progress,
                                100,
                                f"Analyzing text file {idx}/{total_text_files}: {Path(text_file).name}"
                            )
                        
                        analysis = self.analyze_text_file(text_file)
                        if analysis:
                            results.append(analysis)
                            
                    except Exception as e:
                        logger.error(f"Error processing {text_file}: {e}")
            
            # Encode documents to vector database if enabled
            encoding_stats = None
            if self.enable_encoding:
                if progress_callback:
                    progress_callback(85, 100, "Encoding documents to vector database...")
                
                try:
                    encoding_stats = self.encode_ocr_results(directory, progress_callback)
                except Exception as e:
                    logger.error(f"Error during encoding: {e}")
                    encoding_stats = {"error": str(e)}
            
            if progress_callback:
                progress_callback(98, 100, "Saving results...")
            
            # Save results summary
            self.save_results_summary(results, directory, encoding_stats)
            
            if progress_callback:
                progress_callback(100, 100, "Complete!")
            
            # Save summary even without scan results
            self.save_results_summary(results, directory, encoding_stats)
            return results
        
        # Step 1: Get image files
        if progress_callback:
            progress_callback(0, 100, "Scanning for images...")
        
        image_files = self.get_image_files(directory, recursive)
        
        if len(image_files) == 0:
            logger.warning("No images found in the specified directory")
            return results
        
        # Step 2: Initialize OCR
        if progress_callback:
            progress_callback(5, 100, "Loading OCR model...")
        
        if not self.initialize_ocr():
            logger.error("Failed to initialize OCR model")
            return results
        
        # Step 3: Initialize LLM
        if progress_callback:
            progress_callback(10, 100, "Connecting to LLM server...")
        
        if not self.initialize_llm():
            logger.error("Failed to initialize LLM client")
            self.unload_ocr()
            return results
        
        # Step 4: Process each image (OCR only - analysis happens later if enabled)
        total_images = len(image_files)
        for idx, image_path in enumerate(image_files, 1):
            try:
                progress = 10 + int((idx / total_images) * 80)
                
                # Run OCR to extract text
                if progress_callback:
                    progress_callback(
                        progress,
                        100,
                        f"Extracting text from image {idx}/{total_images}: {Path(image_path).name}"
                    )
                
                ocr_text, ocr_file = self.run_ocr_on_image(image_path)
                
                # Store basic info without LLM analysis (analysis done later via auto-detect if enabled)
                results.append({
                    "filename": Path(image_path).name,
                    "image_path": image_path,
                    "ocr_file": ocr_file,
                    "file_type": "image",
                    "ocr_text_length": len(ocr_text) if ocr_text else 0,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error processing {image_path}: {e}")
                results.append({
                    "filename": Path(image_path).name,
                    "image_path": image_path,
                    "file_type": "image",
                    "ocr_error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        # Step 5: Cleanup OCR model
        if progress_callback:
            progress_callback(75, 100, "Unloading OCR model...")
        
        self.unload_ocr()
        logger.info("OCR model unloaded, memory freed")
        
        # Step 6: Analyze text/markdown files (ALWAYS - these should only be analyzed once)
        if progress_callback:
            progress_callback(78, 100, "Scanning for text/markdown files...")
        
        text_files = self.get_text_files(directory, recursive)
        
        if text_files:
            logger.info(f"Analyzing {len(text_files)} text/markdown file(s)...")
            total_text_files = len(text_files)
            
            for idx, text_file in enumerate(text_files, 1):
                try:
                    progress = 78 + int((idx / total_text_files) * 10)
                    if progress_callback:
                        progress_callback(
                            progress,
                            100,
                            f"Analyzing text file {idx}/{total_text_files}: {Path(text_file).name}"
                        )
                    
                    analysis = self.analyze_text_file(text_file)
                    if analysis:
                        results.append(analysis)
                        
                except Exception as e:
                    logger.error(f"Error processing {text_file}: {e}")
        else:
            logger.info("No text/markdown files found")
        
        # Step 7: Encode OCR results and text files to vector database
        encoding_stats = None
        if self.enable_encoding:
            if progress_callback:
                progress_callback(90, 100, "Encoding all documents to vector database...")
            
            try:
                encoding_stats = self.encode_ocr_results(directory, progress_callback)
            except Exception as e:
                logger.error(f"Error during encoding: {e}")
                encoding_stats = {"error": str(e)}
        
        if progress_callback:
            progress_callback(98, 100, "Saving results...")
        
        # Save results summary
        self.save_results_summary(results, directory, encoding_stats)
        
        if progress_callback:
            progress_callback(100, 100, "Scan complete!")
        
        return results
    
    def save_results_summary(self, results: List[Dict], directory: str, encoding_stats: Dict = None):
        """Save scan results summary to JSON file"""
        summary_path = os.path.join(
            self.output_folder,
            f"privacy_scan_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        # Count file types
        image_count = sum(1 for r in results if r.get('file_type') != 'text/markdown')
        text_count = sum(1 for r in results if r.get('file_type') == 'text/markdown')
        
        summary = {
            "scan_timestamp": datetime.now().isoformat(),
            "scanned_directory": directory,
            "total_files": len(results),
            "image_files": image_count,
            "text_md_files": text_count,
            "high_risk_count": sum(1 for r in results if r.get('risk_level') == 'high' or r.get('risk_level') == 'critical'),
            "medium_risk_count": sum(1 for r in results if r.get('risk_level') == 'medium'),
            "low_risk_count": sum(1 for r in results if r.get('risk_level') == 'low'),
            "results": results
        }
        
        # Add encoding statistics if available
        if encoding_stats:
            summary["encoding_stats"] = encoding_stats
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results summary saved to: {summary_path}")


# CLI usage
def main():
    """Command-line interface for the privacy scanner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Scan images and text files for personal/secret information")
    parser.add_argument("directory", help="Directory to scan")
    parser.add_argument("-r", "--recursive", action="store_true", help="Scan subdirectories")
    parser.add_argument("--llm-url", default="http://localhost:8080", help="LLM server URL")
    parser.add_argument("-o", "--output", default="ocr_result", help="Output folder")
    parser.add_argument("--no-encoding", action="store_true", help="Disable vector database encoding")
    parser.add_argument("--db-path", default="./chroma_db", help="ChromaDB storage path")
    
    args = parser.parse_args()
    
    scanner = PrivacyScanner(
        llm_base_url=args.llm_url,
        output_folder=args.output,
        enable_encoding=not args.no_encoding,
        db_path=args.db_path
    )
    
    def progress_callback(current, total, message):
        print(f"[{current}/{total}] {message}")
    
    results = scanner.scan_folder(
        args.directory,
        recursive=args.recursive,
        progress_callback=progress_callback
    )
    
    print("\n" + "=" * 80)
    print("SCAN SUMMARY")
    print("=" * 80)
    
    # Count file types
    images = sum(1 for r in results if r.get('file_type') != 'text/markdown')
    text_files = sum(1 for r in results if r.get('file_type') == 'text/markdown')
    
    critical_high = [r for r in results if r.get('risk_level') in ['critical', 'high']]
    medium = [r for r in results if r.get('risk_level') == 'medium']
    low = [r for r in results if r.get('risk_level') == 'low']
    
    print(f"Total files scanned: {len(results)}")
    print(f"  Images: {images}")
    print(f"  Text/MD files: {text_files}")
    print(f"\nRisk distribution:")
    print(f"  Critical/High risk: {len(critical_high)}")
    print(f"  Medium risk: {len(medium)}")
    print(f"  Low risk: {len(low)}")
    
    if not args.no_encoding:
        print(f"\n✓ All documents (OCR + text/md files) encoded to: {args.db_path}")
    
    if critical_high:
        print("\n⚠️  HIGH RISK FILES:")
        for r in critical_high:
            print(f"  - {r.get('filename')} ({r.get('risk_level')})")
            if r.get('detected_categories'):
                print(f"    Categories: {', '.join(r.get('detected_categories'))}")


if __name__ == "__main__":
    main()
