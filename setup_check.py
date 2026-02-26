# TRACE Setup Script
# This script helps verify your environment and guides you through setup

import sys
import subprocess
import os
from pathlib import Path

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def check_python_version():
    """Check if Python version is compatible"""
    print_header("Checking Python Version")
    
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor >= 9:
        print("✅ Python version is compatible (3.9+)")
        return True
    else:
        print("❌ Python 3.9 or higher required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        return False

def check_dependencies():
    """Check if required packages are installed"""
    print_header("Checking Dependencies")
    
    required_packages = {
        'chromadb': 'chromadb',
        'sentence_transformers': 'sentence-transformers',
        'transformers': 'transformers',
        'torch': 'torch',
        'customtkinter': 'customtkinter',
        'PIL': 'pillow',
        'requests': 'requests',
        'openai': 'openai'
    }
    
    missing = []
    installed = []
    
    for module, package in required_packages.items():
        try:
            __import__(module)
            installed.append(package)
            print(f"✅ {package}")
        except ImportError:
            missing.append(package)
            print(f"❌ {package} - NOT INSTALLED")
    
    print(f"\nInstalled: {len(installed)}/{len(required_packages)}")
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("\nTo install missing packages, run:")
        print(f"   pip install {' '.join(missing)}")
        return False
    else:
        print("\n✅ All dependencies are installed!")
        return True

def check_llm_server():
    """Check if llama.cpp server is running"""
    print_header("Checking llama.cpp Server")
    
    try:
        import requests
        response = requests.get("http://localhost:8080/health", timeout=3)
        
        if response.status_code == 200:
            print("✅ llama.cpp server is running on http://localhost:8080")
            return True
        else:
            print(f"⚠️  Server responded with status code: {response.status_code}")
            return False
    except Exception as e:
        print("❌ llama.cpp server is NOT running")
        print("\nTo start the server:")
        print("   llama-server -m path/to/model.gguf --port 8080")
        print("\nNote: LLM server is required for privacy analysis")
        return False

def check_directories():
    """Check if required directories exist"""
    print_header("Checking Directories")
    
    directories = {
        'ocr_result': 'OCR output storage',
        'temp': 'Temporary files',
        'chroma_db': 'Vector database',
        'model_folder': 'Downloaded models'
    }
    
    for dir_name, description in directories.items():
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"✅ {dir_name}/ - {description}")
        else:
            print(f"⚠️  {dir_name}/ - Creating... ({description})")
            dir_path.mkdir(parents=True, exist_ok=True)
    
    return True

def check_files():
    """Check if required Python files exist"""
    print_header("Checking Core Files")
    
    required_files = [
        'ui.py',
        'pipeline.py',
        'llm.py',
        'glm_ocr.py',
        'vectordb.py',
        'encode_documents.py',
        'get_files.py',
        'embedding_creator.py'
    ]
    
    missing_files = []
    
    for file_name in required_files:
        file_path = Path(file_name)
        if file_path.exists():
            print(f"✅ {file_name}")
        else:
            missing_files.append(file_name)
            print(f"❌ {file_name} - MISSING")
    
    if missing_files:
        print(f"\n⚠️  Missing files: {', '.join(missing_files)}")
        print("Please ensure all project files are present")
        return False
    else:
        print("\n✅ All core files are present!")
        return True

def install_dependencies():
    """Install dependencies from requirements.txt"""
    print_header("Installing Dependencies")
    
    if not Path('requirements.txt').exists():
        print("❌ requirements.txt not found")
        return False
    
    print("Installing packages from requirements.txt...")
    print("This may take several minutes...\n")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("\n✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Installation failed: {e}")
        return False

def main():
    """Main setup verification"""
    print("\n" + "🔍 TRACE - Setup Verification Tool")
    print("="*60)
    
    results = {
        'python': False,
        'files': False,
        'dependencies': False,
        'directories': False,
        'llm_server': False
    }
    
    # Check Python version
    results['python'] = check_python_version()
    if not results['python']:
        print("\n❌ Setup incomplete: Python version incompatible")
        return
    
    # Check core files
    results['files'] = check_files()
    if not results['files']:
        print("\n❌ Setup incomplete: Missing core files")
        return
    
    # Check dependencies
    results['dependencies'] = check_dependencies()
    
    # Offer to install if missing
    if not results['dependencies']:
        response = input("\nWould you like to install missing dependencies now? (y/n): ")
        if response.lower() == 'y':
            if install_dependencies():
                results['dependencies'] = True
    
    # Check directories
    results['directories'] = check_directories()
    
    # Check LLM server
    results['llm_server'] = check_llm_server()
    
    # Summary
    print_header("Setup Summary")
    
    all_ready = all([
        results['python'],
        results['files'],
        results['dependencies'],
        results['directories']
    ])
    
    if all_ready:
        print("✅ Core setup complete!")
        print("\nYou can now run TRACE:")
        print("   python ui.py")
        
        if not results['llm_server']:
            print("\n⚠️  Note: llama.cpp server is not running")
            print("   Privacy analysis features will not work until server is started")
            print("   Start server with:")
            print("   llama-server -m path/to/model.gguf --port 8080")
    else:
        print("❌ Setup incomplete - please fix the issues above")
    
    print("\n" + "="*60)
    print("For more information, see:")
    print("  - README.md - Full documentation")
    print("  - QUICKSTART.md - Quick start guide")
    print("  - CONTRIBUTING.md - Development guidelines")
    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup verification cancelled by user")
    except Exception as e:
        print(f"\n❌ Error during setup verification: {e}")
        print("Please check your installation and try again")
