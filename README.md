# 🔍 TRACE: Localized Intelligence for Digital Footprint Discovery

<div align="center">

**TRACE is a local-first security tool designed to turn unsearchable "Dark Data" into actionable security insights.**

Unlike standard file search, TRACE "sees" inside your images and documents to identify Personally Identifiable Information (PII) before malware does.

</div>

---

## 🛡️ The Problem: The Digital Iceberg

Most users have a **"Digital Iceberg"**: organized files they know about, and a massive amount of **"Dark Data"** (forgotten PDFs, screenshots, and temp files) containing sensitive PII. 

Information-stealing malware doesn't need to crack a vault; it simply scrapes your unmanaged Downloads and Pictures folders for:
- Screenshots containing passwords or API keys
- Bank statements and financial documents
- Government IDs and passport photos
- Medical records and health insurance cards
- Confidential business documents

**TRACE finds these hidden vulnerabilities before attackers do.**

---

## ✨ Key Features

### 🔎 Visibility Layer
- **OCR-Powered Vision**: Uses GLM-OCR Vision-Language Model to extract text from "nameless" screenshots and images where traditional keyword search fails
- **Intelligent Text Analysis**: Analyzes text/markdown files alongside images for comprehensive coverage
- **Semantic Search**: Vector database enables finding documents by meaning, not just keywords (find "Tax Info" regardless of filename)

### 🔒 Local-First Intelligence
Built on the principle that **"The Auditor must be Trustworthy"**:
- All processing happens on-device using local llama.cpp server
- Zero cloud API calls or data leaks
- Your sensitive data never leaves your machine
- Privacy-preserving by design

### ⚠️ Risk Categorization
Automatic file tagging based on PII density and sensitivity:
- **🔴 Critical**: Immediate security threats (passwords, SSNs, credit cards)
- **🟠 High**: Serious privacy concerns (passport numbers, medical records, financial data)
- **🟡 Medium**: Moderate risks (full name + address, employee IDs)
- **🟢 Low**: Minor concerns (just first name, generic email)

### 🎯 Privacy Detection Categories
- **Personal Identifiers**: Names, addresses, phone numbers, emails, dates of birth
- **Government/Official IDs**: SSN, Tax IDs, Passport numbers, Driver's licenses, National IDs
- **Financial Information**: Credit/debit cards, bank accounts, transaction details, salary info
- **Authentication Credentials**: Passwords, API keys, tokens, security codes, PINs
- **Medical/Health Data**: Medical records, prescriptions, health insurance, test results
- **Biometric Data**: Fingerprints, facial recognition data, retinal scans
- **Confidential/Proprietary**: Trade secrets, business plans, internal documents

### 🚀 Active Hygiene
Transition from passive storage to active cleanup:
- **Interactive Results Viewer**: Modal popup showing all sensitive files with risk-colored indicators
- **File Path Display**: Exact location of each sensitive file
- **Detailed Recommendations**: Specific actions for each detected risk
- **Quick Actions**: 
  - ✅ **Delete**: Immediately remove sensitive files with confirmation
  - 🔐 **Vault** (Planned): Move to encrypted storage
  - 📂 **Open Location**: Quickly navigate to file for manual review

---

## 🏗️ Technical Stack & Architecture

TRACE utilizes a modular, Python-based architecture focused on **performance**, **privacy**, and **accuracy**:

### Core Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Ingestion** | `pathlib`, `os` | Recursive directory scanning for images and text files |
| **Vision (OCR/VLM)** | GLM-OCR (`zai-org/GLM-OCR`) | Vision-Language Model for image-to-text conversion |
| **Intelligence (LLM)** | llama.cpp + Qwen 3 4B | Local LLM for privacy analysis and PII detection |
| **Memory (Vector DB)** | ChromaDB + EmbeddingGemma | Persistent vector index for semantic search |
| **Embedding** | `google/embeddinggemma-300m` | Sentence embeddings for semantic chunking |
| **UI Framework** | CustomTkinter | Modern dark-themed desktop interface |

### Architecture Highlights

```
┌─────────────────────────────────────────────────────────┐
│                    CustomTkinter GUI                    │
│                         (ui.py)                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Privacy Scanner Pipeline                   │
│                   (pipeline.py)                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │ 1. Directory Scan → 2. OCR Images → 3. LLM       │   │
│  │    Analysis → 4. Unload OCR → 5. Encode to DB    │   │
│  └──────────────────────────────────────────────────┘   │
└────┬─────────────────┬─────────────────┬─────────────── ┘
     │                 │                 │
     ▼                 ▼                 ▼
┌──────────┐   ┌──────────────┐   ┌─────────────────┐
│ GLM-OCR  │   │ llama.cpp    │   │ ChromaDB +      │
│ Processor│   │ LLM Client   │   │ Document Encoder│
│(glm_ocr) │   │   (llm.py)   │   │(encode_docs.py) │
└──────────┘   └──────────────┘   └─────────────────┘
```

### Memory Optimization
- **Lazy Loading**: Models loaded only when needed
- **Sequential Unloading**: OCR model freed before embedding to reduce peak RAM
- **Efficient Chunking**: Semantic paragraph-based splitting with 2-sentence overlap

---

## 🚀 Getting Started

### Prerequisites

- **Python**: 3.9+ (developed with 3.11.9)
- **GPU**: Recommended for OCR/LLM (works on CPU but slower)
- **RAM**: 8GB minimum, 16GB recommended
- **llama.cpp server**: Required for LLM-based privacy analysis

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-repo/trace.git
   cd trace
   ```

2. **Install Python dependencies**
   ```bash
   pip install chromadb sentence-transformers customtkinter transformers torch pillow requests openai pathlib
   ```

3. **Download GLM-OCR model** (automatic on first run)
   - Model: `zai-org/GLM-OCR`
   - Stored in: `model_folder/models--zai-org--GLM-OCR/`

4. **Set up llama.cpp server**
   ```bash
   # Download llama.cpp from: https://github.com/ggerganov/llama.cpp
   # Download Qwen 3 4B GGUF model
   
   # Start the server:
   llama-server -m path/to/qwen-3-4b.gguf --port 8080
   ```

### Project Structure

```
igdtuw_hackathon/
├── ui.py                    # CustomTkinter GUI (main entry point)
├── pipeline.py              # Privacy scanning orchestration
├── llm.py                   # LlamaCpp client for privacy analysis
├── glm_ocr.py              # GLM-OCR processor for images
├── vectordb.py             # ChromaDB utilities
├── encode_documents.py     # Document encoding with semantic chunking
├── get_files.py            # File discovery utilities
├── embedding_creator.py    # Embedding generation helpers
├── models_preset.ini       # Model configuration
├── model_folder/           # Downloaded models (GLM-OCR)
├── ocr_result/             # OCR output text files
├── temp/                   # Temporary file lists
└── chroma_db/              # Persistent vector database
```

---

## 📖 Usage Guide

### 1. Launch the Application

```bash
python ui.py
```

### 2. Privacy Scan Workflow

1. **Select Folder**: Click "Browse" to choose a directory to scan
2. **Configure Options**:
   - ✅ **Recursive Scan**: Include subdirectories
   - ✅ **Enable OCR**: Extract text from images (requires GLM-OCR)
   - ✅ **Enable Encoding**: Save to vector database for semantic search
3. **Start Scan**: Click "Start Privacy Scan"
4. **Review Results**: 
   - Summary statistics in main window
   - Automatic popup for sensitive files (Critical/High/Medium risk)
5. **Take Action**:
   - Delete sensitive files immediately
   - Open file location for manual review
   - (Future) Move to encrypted vault

### 3. Find Sensitive Documents (Vector DB Search)

Use the "Find Sensitive Docs" feature to search encoded documents:
- Analyzes all documents in vector database with LLM
- Identifies files containing PII across your entire scan history
- Shows comprehensive results in interactive popup

### 4. Encode Documents

Manually trigger document encoding:
- Select directory to scan for `.txt` and `.md` files
- Uses semantic chunking (paragraph boundaries, ~1000 chars)
- Stores in ChromaDB for future semantic search

---

## 🎯 How It Works

### Privacy Analysis Pipeline

```
Image/Document → OCR/Read → LLM Analysis → Risk Categorization → Action
```

1. **Text Extraction**
   - Images: GLM-OCR Vision-Language Model
   - Text files: Direct file reading

2. **Privacy Analysis** (LLM-Powered)
   - Analyzes content using local Qwen 3 4B model via llama.cpp
   - Detects 7 categories of sensitive information
   - Assigns risk level based on sensitivity and exposure

3. **Results Processing**
   - Generates actionable recommendations
   - Displays in risk-colored cards (red/orange/yellow/green)
   - Provides file paths and detected categories

4. **Optional Encoding**
   - Semantic chunking with sentence/paragraph boundaries
   - Vector embeddings using EmbeddingGemma-300m
   - Stored in ChromaDB for semantic search

---

## 🔧 Configuration

### Model Settings

Edit `models_preset.ini` or modify in code:

```python
# In pipeline.py
scanner = PrivacyScanner(
    llm_base_url="http://localhost:8080",      # llama.cpp server
    ocr_model_path="zai-org/GLM-OCR",          # GLM-OCR model
    enable_encoding=True,                       # Vector DB encoding
    enable_ocr=True,                           # Image OCR
    db_path="./chroma_db"                      # ChromaDB storage
)
```

### LLM Analysis Customization

The privacy analysis prompt in `llm.py` can be customized to:
- Add new PII categories
- Adjust risk level thresholds
- Modify detection sensitivity
- Change recommendation templates

---

## 🎨 UI Features

### Main Dashboard
- **Folder Selection**: Easy directory picker with path display
- **Scan Options**: Toggles for recursive scan, OCR, and encoding
- **Progress Tracking**: Real-time progress bar and status updates
- **Results Summary**: Statistics on files analyzed, risk levels, and findings

### Sensitive Files Popup
- **Modal Window**: 1400x800 scrollable results viewer
- **Risk-Colored Headers**: Visual priority indication (red/orange/yellow/green)
- **3-Column Layout**:
  - 📁 **Left**: File path and detected categories
  - ⚠️ **Middle**: Detailed recommendations (expandable text area)
  - 🎛️ **Right**: Action buttons (Delete, Vault, Open Location)

### Interactive Actions
- **Delete Button**: Confirmation dialog → file removal → UI update
- **Vault Button**: Placeholder for future encrypted storage feature
- **Open Location**: Opens file explorer at file location (Windows/Linux compatible)

---

## 👥 Team Jalebi Rabdi

| Member | Role |
|--------|------|
| **Priyhal Jain** | Team Lead |
| **Yeshika Dhingra** | Developer |
| **Kartikeya Srivastava** | Developer |
| **Vaibhav Singh** | Developer |

---

## 🛣️ Roadmap

### Current Features (v1.0)
- ✅ Local LLM-based privacy analysis
- ✅ GLM-OCR image text extraction
- ✅ Risk categorization and recommendations
- ✅ Interactive results popup with actions
- ✅ Vector database semantic search
- ✅ Text/Markdown file analysis

### Planned Features (v2.0)
- 🔜 **Automated Redaction**: OpenCV-powered privacy masks
- 🔜 **Encrypted Vault**: AES-256 secure file storage
- 🔜 **Incremental Scanning**: Delta scans for large directories
- 🔜 **PDF Support**: Native PDF text extraction
- 🔜 **Batch Operations**: Multi-file actions
- 🔜 **Export Reports**: PDF/HTML privacy audit reports

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.

---

## 🙏 Acknowledgments

- **GLM-OCR**: [zai-org/GLM-OCR](https://huggingface.co/zai-org/GLM-OCR) for vision-language OCR
- **llama.cpp**: [ggerganov/llama.cpp](https://github.com/ggerganov/llama.cpp) for local LLM inference
- **ChromaDB**: [chroma-core/chroma](https://github.com/chroma-core/chroma) for vector database
- **CustomTkinter**: [TomSchimansky/CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) for modern UI

---

<div align="center">

**Your data has a trail. TRACE helps you clear it.**

</div>
