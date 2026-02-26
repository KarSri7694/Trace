import os
import logging
from pathlib import Path
from typing import List, Union
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_files_by_extension(
    directory: Union[str, Path],
    extensions: List[str],
    recursive: bool = False
) -> List[str]:
    """
    Retrieve a list of files from a directory based on given file extensions.
    
    Args:
        directory: Path to the directory to search
        extensions: List of file extensions (e.g., ['.py', '.txt', '.jpg'])
                   Extensions can be with or without the leading dot
        recursive: If True, search subdirectories as well (default: True)
    
    Returns:
        List of absolute file paths matching the given extensions
    
    Example:
        files = get_files_by_extension('/path/to/dir', ['.py', '.txt'])
        files = get_files_by_extension('C:\\folder', ['py', 'txt'], recursive=False)
    """
    directory = Path(directory)
    
    logger.debug(f"Searching for files in: {directory}")
    logger.debug(f"Extensions: {extensions}, Recursive: {recursive}")
    
    if not directory.exists():
        logger.error(f"Directory does not exist: {directory}")
        raise ValueError(f"Directory does not exist: {directory}")
    
    if not directory.is_dir():
        logger.error(f"Path is not a directory: {directory}")
        raise ValueError(f"Path is not a directory: {directory}")
    
    # Normalize extensions to include the leading dot
    normalized_extensions = []
    for ext in extensions:
        if not ext.startswith('.'):
            ext = '.' + ext
        normalized_extensions.append(ext.lower())
    
    logger.debug(f"Normalized extensions: {normalized_extensions}")
    
    matching_files = []
    
    if recursive:
        # Walk through directory tree
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in normalized_extensions:
                    matching_files.append(str(file_path.absolute()))
    else:
        # Only search top-level directory
        for item in directory.iterdir():
            if item.is_file() and item.suffix.lower() in normalized_extensions:
                matching_files.append(str(item.absolute()))
    
    logger.info(f"Found {len(matching_files)} matching file(s)")
    return matching_files


def get_files_by_extension_grouped(
    directory: Union[str, Path],
    extensions: List[str],
    recursive: bool = True
) -> dict:
    """
    Retrieve files grouped by extension.
    
    Args:
        directory: Path to the directory to search
        extensions: List of file extensions
        recursive: If True, search subdirectories as well
    
    Returns:
        Dictionary with extensions as keys and lists of file paths as values
    
    Example:
        files = get_files_by_extension_grouped('/path/to/dir', ['.py', '.txt'])
        # Returns: {'.py': ['file1.py', 'file2.py'], '.txt': ['notes.txt']}
    """
    logger.debug(f"Grouping files by extension for directory: {directory}")
    
    all_files = get_files_by_extension(directory, extensions, recursive)
    
    grouped = {ext if ext.startswith('.') else '.' + ext: [] for ext in extensions}
    
    for file_path in all_files:
        ext = Path(file_path).suffix.lower()
        if ext in grouped:
            grouped[ext].append(file_path)
    
    logger.info(f"Grouped {len(all_files)} files into {len([g for g in grouped.values() if g])} extension category(ies)")
    return grouped


def save_file_lists(
    directory: Union[str, Path],
    extensions: List[str],
    output_folder: str = "temp",
    recursive: bool = False
) -> dict:
    """
    Scan directory for files and save lists grouped by extension.
    
    Args:
        directory: Path to the directory to search
        extensions: List of file extensions (e.g., ['.txt', '.md'])
        output_folder: Folder to save file lists (default: 'temp')
        recursive: If True, search subdirectories as well
    
    Returns:
        Dictionary with extension counts and saved file paths
    
    Example:
        result = save_file_lists('/path/to/dir', ['.txt', '.md'])
    """
    logger.info(f"Scanning {directory} for extensions: {extensions}")
    
    # Get files grouped by extension
    files_grouped = get_files_by_extension_grouped(directory, extensions, recursive)
    
    # Create output folder
    os.makedirs(output_folder, exist_ok=True)
    
    result = {
        'total_files': 0,
        'saved_lists': []
    }
    
    for ext, files in files_grouped.items():
        if files:  # Only create file if there are files with this extension
            # Remove the dot from extension for filename
            ext_name = ext.lstrip('.')
            output_filename = f"file_list_{ext_name}.txt"
            output_path = os.path.join(output_folder, output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"File List - Extension: {ext}\n")
                f.write(f"Directory: {directory}\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total files: {len(files)}\n")
                f.write("=" * 80 + "\n\n")
                for file in files:
                    f.write(f"{file}\n")
            
            result['total_files'] += len(files)
            result['saved_lists'].append(output_path)
            logger.info(f"Saved {len(files)} {ext} files to {output_filename}")
    
    logger.info(f"Total: {result['total_files']} file(s) saved to {len(result['saved_lists'])} list(s)")
    return result


if __name__ == "__main__":
    # Example usage
    import sys
    
    # Set logging level to INFO for demo
    logger.setLevel(logging.INFO)
    
    # Get all files with specified extension
    current_dir = "C:\\Users\\Kartikeya Srivastava\\Downloads"
    logger.info(f"Searching in: {current_dir}")
    
    # Get files grouped by extension
    extensions = ['.md', '.txt', '.jpg', '.png', '.pdf']
    files_grouped = get_files_by_extension_grouped(current_dir, extensions, recursive=False)
    
    # Save output to separate text files for each extension
    output_folder = "temp"
    os.makedirs(output_folder, exist_ok=True)
    
    total_files = 0
    saved_files = []
    
    for ext, files in files_grouped.items():
        if files:  # Only create file if there are files with this extension
            # Remove the dot from extension for filename
            ext_name = ext.lstrip('.')
            output_filename = f"file_list_{ext_name}.txt"
            output_path = os.path.join(output_folder, output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"File List - Extension: {ext}\n")
                f.write(f"Directory: {current_dir}\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total files: {len(files)}\n")
                f.write("=" * 80 + "\n\n")
                for file in files:
                    f.write(f"{file}\n")
            
            total_files += len(files)
            saved_files.append(output_filename)
            print(f"\n{ext}: {len(files)} file(s)")
            for file in files[:5]:
                print(f"  - {file}")
            if len(files) > 5:
                print(f"  ... and {len(files) - 5} more")
            print(f"  Saved to: {output_filename}")
    
    print(f"\n{'='*80}")
    print(f"Total: {total_files} file(s) across {len(saved_files)} extension(s)")
    print(f"Output files saved in: {output_folder}/")
