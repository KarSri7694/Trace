import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
import sys
from pathlib import Path
from integrity_checker import check_integrity

# Check integrity before initializing the app
check_integrity()

# Try to import pipeline components
try:
    from pipeline import PrivacyScanner
    from llm import LlamaCppClient
    from encode_documents import DocumentEncoder
    from file_encryptor import FileEncryptor
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure all required files are present: pipeline.py, llm.py, glm_ocr.py, get_files.py, encode_documents.py, file_encryptor.py")
    sys.exit(1)

# Set appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class PrivacyScannerApp:
    def __init__(self):
        self.app = ctk.CTk()
        self.app.geometry("1920x1080")
        self.app.title("TRACE: Privacy Scanner - Local Intelligence")
        
        # Color scheme - Dark Theme
        self.colors = {
            'primary': '#14b8a6',      # Teal
            'primary_dark': '#0d9488',
            'secondary': '#06b6d4',    # Cyan
            'secondary_dark': '#0891b2',
            'success': '#10b981',      # Green
            'success_dark': '#059669',
            'danger': '#ef4444',       # Red
            'danger_dark': '#dc2626',
            'warning': '#f59e0b',      # Orange
            'background': '#0f172a',   # Very dark slate
            'card': '#1e293b',         # Dark slate
            'card_hover': '#334155',   # Slate
            'text': '#f1f5f9',         # Light slate
            'text_muted': '#94a3b8',   # Muted slate
            'border': '#475569'        # Border slate
        }
        
        # Scanner instance
        self.scanner = PrivacyScanner()
        self.document_encoder = None
        self.selected_folder = None
        self.is_scanning = False
        self.is_encoding = False
        self.scan_thread = None
        self.encode_thread = None
        self.stop_requested = False
        
        # Settings storage
        self.llm_url = "http://localhost:8080"
        self.output_folder = "ocr_result"
        self.db_path = "./chroma_db"
        
        # Store scan results for merging with OCR analysis
        self.last_scan_results = []
        
        # Initialize file encryptor
        self.file_encryptor = FileEncryptor()
        
        # Setup UI
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main container with gradient-like effect
        main_frame = ctk.CTkFrame(
            self.app,
            fg_color="transparent"
        )
        main_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Header Section with gradient background
        header_frame = ctk.CTkFrame(
            main_frame,
            fg_color=["#0f172a", "#1e293b"],
            corner_radius=0
        )
        header_frame.pack(fill="x", padx=0, pady=0)
        
        # Settings button in top right
        settings_btn = ctk.CTkButton(
            header_frame,
            text="Settings",
            command=self.open_settings,
            width=100,
            height=40,
            font=("Segoe UI", 13, "bold"),
            corner_radius=10,
            fg_color=self.colors['card'],
            hover_color=self.colors['card_hover']
        )
        settings_btn.place(relx=0.98, rely=0.5, anchor="e")
        
        # Main title
        title_label = ctk.CTkLabel(
            header_frame,
            text="🔍 TRACE",
            font=("Segoe UI", 48, "bold"),
            text_color="white"
        )
        title_label.pack(pady=(25, 5))
        
        # Subtitle
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Privacy Scanner - Digital Footprint Discovery",
            font=("Segoe UI", 16),
            text_color="#94a3b8"
        )
        subtitle_label.pack(pady=(0, 25))
        
        # Content container with padding
        content_frame = ctk.CTkScrollableFrame(
            main_frame,
            fg_color="transparent"
        )
        content_frame.pack(fill="both", expand=True, padx=25, pady=25)
        
        # Folder Selection Section - Modern Card Style
        folder_frame = ctk.CTkFrame(
            content_frame,
            fg_color=self.colors['card'],
            corner_radius=15,
            border_width=1,
            border_color=self.colors['border']
        )
        folder_frame.pack(fill="x", padx=5, pady=(0, 15))
        
        folder_label = ctk.CTkLabel(
            folder_frame,
            text="📁 Select Folder to Scan",
            font=("Segoe UI", 16, "bold"),
            text_color=self.colors['text']
        )
        folder_label.pack(anchor="w", padx=20, pady=(20, 10))
        
        # Folder path display and button
        folder_input_frame = ctk.CTkFrame(
            folder_frame,
            fg_color="transparent"
        )
        folder_input_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.folder_entry = ctk.CTkEntry(
            folder_input_frame,
            placeholder_text="No folder selected - Click Browse to choose",
            font=("Segoe UI", 13),
            state="readonly",
            height=45,
            corner_radius=10,
            border_width=2,
            border_color=self.colors['border']
        )
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 15))
        
        browse_btn = ctk.CTkButton(
            folder_input_frame,
            text="📂 Browse",
            command=self.select_folder,
            width=140,
            height=45,
            font=("Segoe UI", 13, "bold"),
            corner_radius=10,
            fg_color=self.colors['primary'],
            hover_color=self.colors['primary_dark']
        )
        browse_btn.pack(side="right")
        
        # Options Section - Card Style with two columns
        options_frame = ctk.CTkFrame(
            content_frame,
            fg_color=self.colors['card'],
            corner_radius=15,
            border_width=1,
            border_color=self.colors['border']
        )
        options_frame.pack(fill="x", padx=5, pady=(0, 15))
        
        options_label = ctk.CTkLabel(
            options_frame,
            text="⚙️ Scan Options",
            font=("Segoe UI", 16, "bold"),
            text_color=self.colors['text']
        )
        options_label.pack(anchor="w", padx=20, pady=(20, 15))
        
        # Two-column layout container
        two_column_frame = ctk.CTkFrame(
            options_frame,
            fg_color="transparent"
        )
        two_column_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # Left column: Checkboxes
        checkbox_frame = ctk.CTkFrame(
            two_column_frame,
            fg_color="transparent"
        )
        checkbox_frame.pack(side="left", fill="both", expand=True, padx=(0, 20))
        
        # Recursive checkbox
        self.recursive_var = ctk.BooleanVar(value=False)
        recursive_check = ctk.CTkCheckBox(
            checkbox_frame,
            text="🔄 Scan subdirectories recursively",
            variable=self.recursive_var,
            font=("Segoe UI", 13),
            checkbox_width=24,
            checkbox_height=24,
            corner_radius=6,
            fg_color=self.colors['primary'],
            hover_color=self.colors['primary_dark']
        )
        recursive_check.pack(anchor="w", pady=(0, 12))
        
        # Enable OCR checkbox
        self.enable_ocr_var = ctk.BooleanVar(value=True)
        ocr_check = ctk.CTkCheckBox(
            checkbox_frame,
            text="👁️Enable OCR on images (extract text from images)",
            variable=self.enable_ocr_var,
            font=("Segoe UI", 13),
            checkbox_width=24,
            checkbox_height=24,
            corner_radius=6,
            fg_color=self.colors['primary'],
            hover_color=self.colors['primary_dark']
        )
        ocr_check.pack(anchor="w", pady=(0, 12))
        
        # Enable encoding checkbox
        self.enable_encoding_var = ctk.BooleanVar(value=True)
        encoding_check = ctk.CTkCheckBox(
            checkbox_frame,
            text="💾 Encode documents to vector database (enables semantic search)",
            variable=self.enable_encoding_var,
            font=("Segoe UI", 13),
            checkbox_width=24,
            checkbox_height=24,
            corner_radius=6,
            fg_color=self.colors['primary'],
            hover_color=self.colors['primary_dark']
        )
        encoding_check.pack(anchor="w", pady=(0, 12))
        
        # Auto-detect sensitive files checkbox
        self.auto_detect_sensitive_var = ctk.BooleanVar(value=True)
        auto_detect_check = ctk.CTkCheckBox(
            checkbox_frame,
            text="🔍 Auto-analyze images for sensitive content (text files always analyzed)",
            variable=self.auto_detect_sensitive_var,
            font=("Segoe UI", 13),
            checkbox_width=24,
            checkbox_height=24,
            corner_radius=6,
            fg_color=self.colors['primary'],
            hover_color=self.colors['primary_dark']
        )
        auto_detect_check.pack(anchor="w", pady=(0, 0))
        
        # Right column: Scan Buttons
        scan_buttons_frame = ctk.CTkFrame(
            two_column_frame,
            fg_color="transparent"
        )
        scan_buttons_frame.pack(side="right", fill="y")
        
        self.scan_btn = ctk.CTkButton(
            scan_buttons_frame,
            text="🚀 Start Privacy Scan",
            command=self.start_scan,
            font=("Segoe UI", 16, "bold"),
            width=280,
            height=55,
            corner_radius=12,
            fg_color=self.colors['success'],
            hover_color=self.colors['success_dark'],
            border_width=0
        )
        self.scan_btn.pack(pady=(0, 12))
        
        self.stop_btn = ctk.CTkButton(
            scan_buttons_frame,
            text="⏹ Stop Scan",
            command=self.stop_scan,
            font=("Segoe UI", 14, "bold"),
            width=280,
            height=50,
            corner_radius=12,
            fg_color=self.colors['danger'],
            hover_color=self.colors['danger_dark'],
            state="disabled"
        )
        self.stop_btn.pack()
        
        # Progress Section - Modern Card
        progress_frame = ctk.CTkFrame(
            content_frame,
            fg_color=self.colors['card'],
            corner_radius=15,
            border_width=1,
            border_color=self.colors['border']
        )
        progress_frame.pack(fill="x", padx=5, pady=(0, 15))
        
        self.progress_label = ctk.CTkLabel(
            progress_frame,
            text="Ready to scan",
            font=("Segoe UI", 13),
            text_color=self.colors['text']
        )
        self.progress_label.pack(pady=(20, 12))
        
        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            height=20,
            corner_radius=10,
            progress_color=self.colors['primary']
        )
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 20))
        self.progress_bar.set(0)
        
        # Quick Query Section - Card Style
        query_frame = ctk.CTkFrame(
            content_frame,
            fg_color=self.colors['card'],
            corner_radius=15,
            border_width=1,
            border_color=self.colors['border']
        )
        query_frame.pack(fill="x", padx=5, pady=(0, 15))
        
        query_label = ctk.CTkLabel(
            query_frame,
            text="🔍 Quick Query Database",
            font=("Segoe UI", 16, "bold"),
            text_color=self.colors['text']
        )
        query_label.pack(anchor="w", padx=20, pady=(20, 15))
        
        # Query input row
        query_input_frame = ctk.CTkFrame(
            query_frame,
            fg_color="transparent"
        )
        query_input_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.query_entry = ctk.CTkEntry(
            query_input_frame,
            placeholder_text="Enter search query (e.g., personal information, passwords, financial data...)",
            font=("Segoe UI", 13),
            height=45,
            corner_radius=10,
            border_width=2,
            border_color=self.colors['border']
        )
        self.query_entry.pack(side="left", fill="x", expand=True, padx=(0, 15))
        
        # Bind Enter key to search
        self.query_entry.bind("<Return>", lambda e: self.quick_query_database())
        
        # Number of results
        results_label = ctk.CTkLabel(
            query_input_frame,
            text="Results:",
            font=("Segoe UI", 12),
            text_color=self.colors['text_muted']
        )
        results_label.pack(side="left", padx=(0, 8))
        
        self.n_results_var = ctk.StringVar(value="5")
        n_results_entry = ctk.CTkEntry(
            query_input_frame,
            textvariable=self.n_results_var,
            width=60,
            height=45,
            font=("Segoe UI", 12),
            corner_radius=8,
            border_width=2,
            border_color=self.colors['border'],
            justify="center"
        )
        n_results_entry.pack(side="left", padx=(0, 15))
        
        self.quick_search_btn = ctk.CTkButton(
            query_input_frame,
            text="🔍 Search",
            command=self.quick_query_database,
            width=140,
            height=45,
            font=("Segoe UI", 13, "bold"),
            corner_radius=10,
            fg_color=self.colors['primary'],
            hover_color=self.colors['primary_dark']
        )
        self.quick_search_btn.pack(side="left")
        
        # Results Section - Card Style
        results_container = ctk.CTkFrame(
            content_frame,
            fg_color=self.colors['card'],
            corner_radius=15,
            border_width=1,
            border_color=self.colors['border']
        )
        results_container.pack(fill="both", expand=True, padx=5, pady=(0, 15))
        
        results_label = ctk.CTkLabel(
            results_container,
            text="📄 Scan Results",
            font=("Segoe UI", 16, "bold"),
            text_color=self.colors['text']
        )
        results_label.pack(anchor="w", padx=20, pady=(20, 15))
        
        # Results text box
        self.results_text = ctk.CTkTextbox(
            results_container,
            font=("Consolas", 12),
            wrap="word",
            corner_radius=10,
            border_width=1,
            border_color=self.colors['border']
        )
        self.results_text.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Action Buttons Row - Modern Grid Layout
        action_container = ctk.CTkFrame(
            content_frame,
            fg_color="transparent"
        )
        action_container.pack(fill="x", padx=5, pady=(0, 20))
        
        # Top row - Basic actions
        action_row1 = ctk.CTkFrame(
            action_container,
            fg_color="transparent"
        )
        action_row1.pack(fill="x", pady=(0, 12))
        
        clear_btn = ctk.CTkButton(
            action_row1,
            text="🗑️ Clear Results",
            command=self.clear_results,
            width=180,
            height=42,
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            fg_color=self.colors['card'],
            hover_color=self.colors['card_hover'],
            border_width=2,
            border_color=self.colors['border']
        )
        clear_btn.pack(side="left", padx=(0, 10))
        
        export_btn = ctk.CTkButton(
            action_row1,
            text="📤 Export Results",
            command=self.export_results,
            width=180,
            height=42,
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            fg_color=self.colors['secondary'],
            hover_color=self.colors['secondary_dark']
        )
        export_btn.pack(side="left", padx=(0, 10))
        
        view_ocr_btn = ctk.CTkButton(
            action_row1,
            text="📂 View OCR Files",
            command=self.open_output_folder,
            width=180,
            height=42,
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            fg_color=self.colors['primary'],
            hover_color=self.colors['primary_dark']
        )
        view_ocr_btn.pack(side="left")
        
        # Vector Database Actions - Bottom row
        action_row2 = ctk.CTkFrame(
            action_container,
            fg_color="transparent"
        )
        action_row2.pack(fill="x")
        
        db_actions_label = ctk.CTkLabel(
            action_row2,
            text="💾 Vector Database:",
            font=("Segoe UI", 13, "bold"),
            text_color=self.colors['text']
        )
        db_actions_label.pack(side="left", padx=(0, 15))
        
        self.encode_btn = ctk.CTkButton(
            action_row2,
            text="📚 Encode Docs",
            command=self.encode_documents,
            width=160,
            height=42,
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            fg_color=self.colors['primary'],
            hover_color=self.colors['primary_dark']
        )
        self.encode_btn.pack(side="left", padx=(0, 10))
        
        search_btn = ctk.CTkButton(
            action_row2,
            text="🔎 Search DB",
            command=self.search_database,
            width=160,
            height=42,
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            fg_color=self.colors['secondary'],
            hover_color=self.colors['secondary_dark']
        )
        search_btn.pack(side="left", padx=(0, 10))
        
        stats_btn = ctk.CTkButton(
            action_row2,
            text="📊 DB Stats",
            command=self.show_db_stats,
            width=140,
            height=42,
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            fg_color=self.colors['card'],
            hover_color=self.colors['card_hover'],
            border_width=2,
            border_color=self.colors['border']
        )
        stats_btn.pack(side="left", padx=(0, 10))
        
        find_sensitive_btn = ctk.CTkButton(
            action_row2,
            text="🚨 Find Sensitive",
            command=self.find_sensitive_documents,
            width=170,
            height=42,
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            fg_color=self.colors['danger'],
            hover_color=self.colors['danger_dark']
        )
        find_sensitive_btn.pack(side="left", padx=(0, 10))
        
        vault_btn = ctk.CTkButton(
            action_row2,
            text="🔐 Manage Vault",
            command=self.manage_vault,
            width=160,
            height=42,
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            fg_color=self.colors['warning'],
            hover_color="#d97706"
        )
        vault_btn.pack(side="left")
        
        # Status bar - Modern footer
        status_frame = ctk.CTkFrame(
            self.app,
            fg_color=self.colors['card'],
            height=40,
            corner_radius=0
        )
        status_frame.pack(side="bottom", fill="x", padx=0, pady=0)
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="✓ Ready",
            font=("Segoe UI", 11),
            text_color=self.colors['text_muted'],
            anchor="w"
        )
        self.status_label.pack(side="left", padx=25, pady=10)
    
    def open_settings(self):
        """Open settings dialog"""
        # Create settings window
        settings_window = ctk.CTkToplevel(self.app)
        settings_window.title("⚙️ Settings")
        settings_window.geometry("700x500")
        
        # Make it modal
        settings_window.grab_set()
        settings_window.focus()
        
        # Header
        header_frame = ctk.CTkFrame(
            settings_window,
            fg_color=self.colors['card'],
            corner_radius=0
        )
        header_frame.pack(fill="x", padx=0, pady=0)
        
        header_label = ctk.CTkLabel(
            header_frame,
            text="⚙️ Application Settings",
            font=("Segoe UI", 24, "bold"),
            text_color=self.colors['text']
        )
        header_label.pack(pady=25)
        
        # Content frame
        content_frame = ctk.CTkFrame(
            settings_window,
            fg_color="transparent"
        )
        content_frame.pack(fill="both", expand=True, padx=30, pady=30)
        
        # LLM Server URL
        llm_label = ctk.CTkLabel(
            content_frame,
            text="🤖 LLM Server URL:",
            font=("Segoe UI", 14, "bold"),
            anchor="w"
        )
        llm_label.pack(anchor="w", pady=(0, 8))
        
        llm_frame = ctk.CTkFrame(
            content_frame,
            fg_color="transparent"
        )
        llm_frame.pack(fill="x", pady=(0, 20))
        
        llm_url_entry = ctk.CTkEntry(
            llm_frame,
            placeholder_text="http://localhost:8080",
            font=("Segoe UI", 12),
            height=42,
            corner_radius=8,
            border_width=2,
            border_color=self.colors['border']
        )
        llm_url_entry.insert(0, self.llm_url)
        llm_url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        test_btn = ctk.CTkButton(
            llm_frame,
            text="✓ Test",
            command=lambda: self.test_llm_connection_settings(llm_url_entry.get()),
            width=100,
            height=42,
            font=("Segoe UI", 12, "bold"),
            corner_radius=8,
            fg_color=self.colors['success'],
            hover_color=self.colors['success_dark']
        )
        test_btn.pack(side="left")
        
        # Output Folder
        output_label = ctk.CTkLabel(
            content_frame,
            text="📄 Output Folder:",
            font=("Segoe UI", 14, "bold"),
            anchor="w"
        )
        output_label.pack(anchor="w", pady=(0, 8))
        
        output_frame = ctk.CTkFrame(
            content_frame,
            fg_color="transparent"
        )
        output_frame.pack(fill="x", pady=(0, 20))
        
        output_folder_entry = ctk.CTkEntry(
            output_frame,
            placeholder_text="ocr_result",
            font=("Segoe UI", 12),
            height=42,
            corner_radius=8,
            border_width=2,
            border_color=self.colors['border']
        )
        output_folder_entry.insert(0, self.output_folder)
        output_folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        open_btn = ctk.CTkButton(
            output_frame,
            text="📂 Open",
            command=lambda: self.open_output_folder_settings(output_folder_entry.get()),
            width=100,
            height=42,
            font=("Segoe UI", 12, "bold"),
            corner_radius=8,
            fg_color=self.colors['secondary'],
            hover_color=self.colors['secondary_dark']
        )
        open_btn.pack(side="left")
        
        # Vector DB Path
        db_label = ctk.CTkLabel(
            content_frame,
            text="💾 Vector Database Path:",
            font=("Segoe UI", 14, "bold"),
            anchor="w"
        )
        db_label.pack(anchor="w", pady=(0, 8))
        
        db_path_entry = ctk.CTkEntry(
            content_frame,
            placeholder_text="./chroma_db",
            font=("Segoe UI", 12),
            height=42,
            corner_radius=8,
            border_width=2,
            border_color=self.colors['border']
        )
        db_path_entry.insert(0, self.db_path)
        db_path_entry.pack(fill="x", pady=(0, 30))
        
        # Buttons
        button_frame = ctk.CTkFrame(
            content_frame,
            fg_color="transparent"
        )
        button_frame.pack(fill="x")
        
        save_btn = ctk.CTkButton(
            button_frame,
            text="💾 Save Settings",
            command=lambda: self.save_settings(
                llm_url_entry.get(),
                output_folder_entry.get(),
                db_path_entry.get(),
                settings_window
            ),
            height=50,
            font=("Segoe UI", 14, "bold"),
            corner_radius=10,
            fg_color=self.colors['primary'],
            hover_color=self.colors['primary_dark']
        )
        save_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=settings_window.destroy,
            height=50,
            width=150,
            font=("Segoe UI", 14, "bold"),
            corner_radius=10,
            fg_color=self.colors['card'],
            hover_color=self.colors['card_hover']
        )
        cancel_btn.pack(side="left")
    
    def save_settings(self, llm_url, output_folder, db_path, window):
        """Save settings and close window"""
        self.llm_url = llm_url.strip() if llm_url.strip() else "http://localhost:8080"
        self.output_folder = output_folder.strip() if output_folder.strip() else "ocr_result"
        self.db_path = db_path.strip() if db_path.strip() else "./chroma_db"
        
        messagebox.showinfo("Settings Saved", "Settings have been updated successfully!")
        window.destroy()
    
    def test_llm_connection_settings(self, llm_url):
        """Test connection to LLM server from settings dialog"""
        if not llm_url:
            llm_url = "http://localhost:8080"
        
        def test_connection():
            try:
                test_client = LlamaCppClient(base_url=llm_url)
                if test_client.check_server_status():
                    self.app.after(0, lambda: messagebox.showinfo(
                        "Connection Successful",
                        f"✅ LLM server is running at {llm_url}\n\nYou're ready to scan!"
                    ))
                else:
                    self.app.after(0, lambda: messagebox.showerror(
                        "Connection Failed",
                        f"❌ Cannot connect to LLM server at {llm_url}\n\nPlease ensure llama.cpp server is running:\nllama-server -m models/your-model.gguf --port 8080"
                    ))
            except Exception as e:
                self.app.after(0, lambda: messagebox.showerror(
                    "Connection Error",
                    f"Error testing connection:\n{str(e)}"
                ))
        
        threading.Thread(target=test_connection, daemon=True).start()
    
    def open_output_folder_settings(self, output_folder):
        """Open the output folder in file explorer from settings dialog"""
        if not output_folder:
            output_folder = "ocr_result"
        
        # Create folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        
        # Open in file explorer
        abs_path = os.path.abspath(output_folder)
        if os.name == 'nt':  # Windows
            os.startfile(abs_path)
        elif os.name == 'posix':  # macOS/Linux
            import subprocess
            subprocess.Popen(['xdg-open', abs_path])
    
    def test_llm_connection(self):
        """Test connection to LLM server"""
        llm_url = self.llm_url
        if not llm_url:
            llm_url = "http://localhost:8080"
        
        self.status_label.configure(text="Testing LLM connection...")
        
        def test_connection():
            try:
                test_client = LlamaCppClient(base_url=llm_url)
                if test_client.check_server_status():
                    self.app.after(0, lambda: messagebox.showinfo(
                        "Connection Successful",
                        f"✅ LLM server is running at {llm_url}\n\nYou're ready to scan!"
                    ))
                    self.app.after(0, lambda: self.status_label.configure(text="LLM server connected ✓"))
                else:
                    self.app.after(0, lambda: messagebox.showerror(
                        "Connection Failed",
                        f"❌ Cannot connect to LLM server at {llm_url}\n\nPlease ensure llama.cpp server is running:\nllama-server -m models/your-model.gguf --port 8080"
                    ))
                    self.app.after(0, lambda: self.status_label.configure(text="LLM server not responding ✗"))
            except Exception as e:
                self.app.after(0, lambda: messagebox.showerror(
                    "Connection Error",
                    f"Error testing connection:\n{str(e)}"
                ))
                self.app.after(0, lambda: self.status_label.configure(text="Connection test failed"))
        
        threading.Thread(target=test_connection, daemon=True).start()
    
    def open_output_folder(self):
        """Open the output folder in file explorer"""
        output_folder = self.output_folder
        if not output_folder:
            output_folder = "ocr_result"
        
        # Create folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        
        # Open in file explorer
        abs_path = os.path.abspath(output_folder)
        if os.name == 'nt':  # Windows
            os.startfile(abs_path)
        elif os.name == 'posix':  # macOS/Linux
            import subprocess
            subprocess.Popen(['xdg-open', abs_path])
        
        self.status_label.configure(text=f"Opened folder: {abs_path}")
    
    def select_folder(self):
        """Open folder selection dialog"""
        folder = filedialog.askdirectory(title="Select Folder to Scan")
        if folder:
            self.selected_folder = folder
            self.folder_entry.configure(state="normal")
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, folder)
            self.folder_entry.configure(state="readonly")
            self.status_label.configure(text=f"Selected: {folder}")
    
    def start_scan(self):
        """Start the privacy scan in a separate thread"""
        if self.is_scanning:
            messagebox.showwarning("Scan in Progress", "A scan is already running!")
            return
        
        if not self.selected_folder:
            messagebox.showerror("No Folder Selected", "Please select a folder to scan first!")
            return
        
        if not os.path.exists(self.selected_folder):
            messagebox.showerror("Invalid Folder", "The selected folder does not exist!")
            return
        
        # Disable scan button, enable stop button
        self.is_scanning = True
        self.stop_requested = False
        self.scan_btn.configure(state="disabled", text="⏳ Scanning...")
        self.stop_btn.configure(state="normal")
        self.clear_results()
        
        # Update scanner with LLM URL and output folder
        llm_url = self.llm_url
        if not llm_url:
            llm_url = "http://localhost:8080"
        
        output_folder = self.output_folder
        if not output_folder:
            output_folder = "ocr_result"
        
        db_path = self.db_path
        if not db_path:
            db_path = "./chroma_db"
        
        enable_encoding = self.enable_encoding_var.get()
        enable_ocr = self.enable_ocr_var.get()
        
        self.scanner = PrivacyScanner(
            llm_base_url=llm_url,
            output_folder=output_folder,
            enable_encoding=enable_encoding,
            enable_ocr=enable_ocr,
            db_path=db_path
        )
        
        # Start scan in separate thread
        self.scan_thread = threading.Thread(target=self.run_scan, daemon=True)
        self.scan_thread.start()
    
    def stop_scan(self):
        """Request to stop the current scan"""
        if self.is_scanning:
            self.stop_requested = True
            self.stop_btn.configure(state="disabled")
            self.status_label.configure(text="Stopping scan... (processing current image)")
            messagebox.showinfo("Stopping Scan", "Scan will stop after completing the current image.")
    
    def run_scan(self):
        """Execute the scan (runs in separate thread)"""
        try:
            recursive = self.recursive_var.get()
            
            # Create a wrapper progress callback that checks for stop request
            def progress_wrapper(current, total, message):
                if self.stop_requested:
                    raise InterruptedError("Scan stopped by user")
                self.update_progress(current, total, message)
            
            results = self.scanner.scan_folder(
                self.selected_folder,
                recursive=recursive,
                progress_callback=progress_wrapper
            )
            
            # Store results for later merging with OCR analysis
            self.last_scan_results = results
            
            # Display results
            if not self.stop_requested:
                self.app.after(0, lambda: self.display_results(results))
                # Don't show popup yet if auto-detect is enabled - wait for OCR analysis to merge
                if not (self.enable_encoding_var.get() and self.auto_detect_sensitive_var.get()):
                    # Only show popup if not auto-detecting (otherwise will show combined results later)
                    sensitive_files = [r for r in results if r.get('risk_level') in ['critical', 'high', 'medium']]
                    if sensitive_files:
                        self.app.after(0, lambda: self.show_results_popup(sensitive_files))

            else:
                self.app.after(0, lambda: self.display_partial_results(results))
            
        except InterruptedError:
            self.app.after(0, lambda: messagebox.showinfo("Scan Stopped", "Scan was stopped by user."))
            self.app.after(0, lambda: self.progress_label.configure(text="Scan stopped by user"))
        except Exception as e:
            self.app.after(0, lambda: messagebox.showerror("Scan Error", f"An error occurred:\n{str(e)}"))
            self.app.after(0, lambda: self.progress_label.configure(text=f"Error: {str(e)}"))
        finally:
            self.app.after(0, self.scan_complete)
    
    def update_progress(self, current, total, message):
        """Update progress bar and label"""
        progress = current / total if total > 0 else 0
        self.app.after(0, lambda: self.progress_bar.set(progress))
        self.app.after(0, lambda: self.progress_label.configure(text=message))
        self.app.after(0, lambda: self.status_label.configure(text=message))
    
    def display_results(self, results):
        """Display scan results in the text widget"""
        self.results_text.delete("1.0", "end")
        
        if not results:
            self.results_text.insert("1.0", "No files found or scan failed.\n")
            return
        
        # Summary
        total = len(results)
        images = sum(1 for r in results if r.get('file_type') == 'image' or (r.get('file_type') != 'text/markdown' and r.get('image_path')))
        text_files = sum(1 for r in results if r.get('file_type') == 'text/markdown')
        critical = sum(1 for r in results if r.get('risk_level') == 'critical')
        high = sum(1 for r in results if r.get('risk_level') == 'high')
        medium = sum(1 for r in results if r.get('risk_level') == 'medium')
        low = sum(1 for r in results if r.get('risk_level') == 'low')
        none_found = sum(1 for r in results if r.get('risk_level') == 'none')
        pending_analysis = sum(1 for r in results if r.get('file_type') == 'image' and not r.get('risk_level'))
        
        summary = f"""
{'='*80}
PRIVACY SCAN SUMMARY
{'='*80}
Total Files Scanned: {total}
  Images: {images}
  Text/MD Files: {text_files}

Risk Distribution:
  Critical Risk: {critical}
  High Risk: {high}
  Medium Risk: {medium}
  Low Risk: {low}
  No Risk: {none_found}
  Pending Analysis: {pending_analysis} (images awaiting LLM analysis)
{'='*80}

"""
        self.results_text.insert("end", summary)
        
        # Note about pending analysis
        if pending_analysis > 0:
            note = f"""
📝 Note: {pending_analysis} image(s) have been OCR'd but not yet analyzed for sensitive content.
   Enable 'Auto-analyze images for sensitive content' checkbox to analyze them automatically,
   or use 'Find Sensitive Docs' button to analyze manually.

"""
            self.results_text.insert("end", note)
        
        # Detailed results
        displayed_idx = 0
        for idx, result in enumerate(results, 1):
            risk = result.get('risk_level', 'pending').upper()
            filename = result.get('filename', 'Unknown')
            contains_sensitive = result.get('contains_sensitive_info', False)
            file_type = result.get('file_type', 'image')
            
            # Skip displaying images that haven't been analyzed yet (they'll show in pending count)
            if file_type == 'image' and risk == 'PENDING':
                continue
            
            displayed_idx += 1
            
            # Color code based on risk
            risk_emoji = {
                'CRITICAL': '🔴',
                'HIGH': '🟠',
                'MEDIUM': '🟡',
                'LOW': '🟢',
                'NONE': '✅',
                'PENDING': '⏳',
                'UNKNOWN': '❓',
                'ERROR': '❌'
            }.get(risk, '❓')
            
            # File type indicator
            type_emoji = '📄' if file_type == 'text/markdown' else '🖼️'
            
            detail = f"\n{displayed_idx}. {risk_emoji} {type_emoji} {filename}\n"
            detail += f"   Risk Level: {risk}\n"
            detail += f"   Type: {file_type.title()}\n"
            
            if risk != 'PENDING':
                detail += f"   Contains Sensitive Info: {'Yes' if contains_sensitive else 'No'}\n"
            
            if result.get('detected_categories'):
                detail += f"   Categories: {', '.join(result.get('detected_categories'))}\n"
            
            if result.get('specific_findings'):
                detail += f"   Findings:\n"
                for finding in result.get('specific_findings', [])[:5]:  # Show up to 5
                    detail += f"      - {finding}\n"
                if len(result.get('specific_findings', [])) > 5:
                    detail += f"      ... and {len(result.get('specific_findings', [])) - 5} more\n"
            
            if result.get('recommendations'):
                detail += f"   Recommendations:\n"
                for rec in result.get('recommendations', []):  # Show all recommendations
                    detail += f"      - {rec}\n"
            
            # Display file path (handle both image_path and file_path)
            file_path = result.get('file_path') or result.get('image_path', 'N/A')
            detail += f"   File: {file_path}\n"
            
            # Show OCR info for images
            if file_type == 'image' and result.get('ocr_file'):
                detail += f"   OCR Result: {result.get('ocr_file')}\n"
            
            detail += "-" * 80 + "\n"
            
            self.results_text.insert("end", detail)
        
        # Add critical actions summary for high-risk files
        high_risk_files = [r for r in results if r.get('risk_level') in ['critical', 'high']]
        
        if high_risk_files:
            self.results_text.insert("end", f"\n{'='*80}\n")
            self.results_text.insert("end", f"⚠️  CRITICAL ACTIONS REQUIRED\n")
            self.results_text.insert("end", f"{'='*80}\n\n")
            self.results_text.insert("end", f"{len(high_risk_files)} file(s) require immediate attention:\n\n")
            
            for idx, result in enumerate(high_risk_files, 1):
                filename = result.get('filename', 'Unknown')
                file_path = result.get('file_path') or result.get('image_path', 'N/A')
                risk = result.get('risk_level', 'unknown').upper()
                categories = result.get('detected_categories', [])
                
                risk_icon = '🔴' if risk == 'CRITICAL' else '🟠'
                
                self.results_text.insert("end", f"{idx}. {risk_icon} {filename}\n")
                self.results_text.insert("end", f"   Path: {file_path}\n")
                
                if categories:
                    self.results_text.insert("end", f"   Sensitive Data Types: {', '.join(categories)}\n")
                
                if result.get('recommendations'):
                    self.results_text.insert("end", f"\n   ACTION ITEMS:\n")
                    for rec_idx, rec in enumerate(result.get('recommendations', []), 1):
                        self.results_text.insert("end", f"   {rec_idx}. {rec}\n")
                
                self.results_text.insert("end", "\n" + "-" * 80 + "\n\n")
        
        self.results_text.insert("end", f"\n{'='*80}\n")
        self.results_text.insert("end", f"Scan completed at: {Path(self.scanner.output_folder).absolute()}\n")
    
    
    def show_results_popup(self, sensitive_files):
        """Show scan results in a modern popup window with file actions"""
        # Create popup window
        popup = ctk.CTkToplevel(self.app)
        popup.title(f"Sensitive Files Found - {len(sensitive_files)} file(s)")
        popup.geometry("1500x900")
        
        # Make it modal
        popup.grab_set()
        popup.focus()
        
        # Header with gradient effect
        header_frame = ctk.CTkFrame(
            popup,
            fg_color=self.colors['danger'],
            corner_radius=0
        )
        header_frame.pack(fill="x", padx=0, pady=0)
        
        header_label = ctk.CTkLabel(
            header_frame,
            text=f"🚨 {len(sensitive_files)} SENSITIVE FILE(S) DETECTED",
            font=("Segoe UI", 24, "bold"),
            text_color="white"
        )
        header_label.pack(pady=(25, 10))
        
        subheader_label = ctk.CTkLabel(
            header_frame,
            text="Review and take action on files containing sensitive information",
            font=("Segoe UI", 13),
            text_color="#fecaca"
        )
        subheader_label.pack(pady=(0, 25))
        
        # Main content frame with scrollbar
        main_frame = ctk.CTkScrollableFrame(
            popup,
            fg_color="transparent"
        )
        main_frame.pack(fill="both", expand=True, padx=25, pady=25)
        
        # Display each sensitive file
        for idx, result in enumerate(sensitive_files, 1):
            self.create_file_card(main_frame, result, idx)
        
        # Bottom action bar
        bottom_frame = ctk.CTkFrame(
            popup,
            fg_color=self.colors['card'],
            corner_radius=0,
            height=70
        )
        bottom_frame.pack(fill="x", padx=0, pady=0)
        
        close_btn = ctk.CTkButton(
            bottom_frame,
            text="✕ Close",
            command=popup.destroy,
            width=200,
            height=45,
            font=("Segoe UI", 14, "bold"),
            corner_radius=10,
            fg_color=self.colors['primary'],
            hover_color=self.colors['primary_dark']
        )
        close_btn.pack(pady=12)
    
    def create_file_card(self, parent, result, idx):
        """Create a modern card for each sensitive file with path, recommendations, and actions"""
        filename = result.get('filename', 'Unknown')
        file_path = result.get('file_path') or result.get('image_path', 'N/A')
        risk_level = result.get('risk_level', 'low').upper()
        categories = result.get('detected_categories', [])
        recommendations = result.get('recommendations', [])
        
        # Risk colors - modern palette
        risk_colors = {
            'CRITICAL': '#dc2626',  # Red
            'HIGH': '#f97316',      # Orange
            'MEDIUM': '#f59e0b',    # Amber
            'LOW': '#84cc16'        # Lime
        }
        risk_color = risk_colors.get(risk_level, '#6b7280')
        
        # Risk icons
        risk_icons = {
            'CRITICAL': '🔴',
            'HIGH': '🟠',
            'MEDIUM': '🟡',
            'LOW': '🟢'
        }
        risk_icon = risk_icons.get(risk_level, '⚫')
        
        # Main card frame with shadow effect
        card_frame = ctk.CTkFrame(
            parent,
            fg_color=self.colors['card'],
            corner_radius=12,
            border_width=2,
            border_color=risk_color
        )
        card_frame.pack(fill="x", padx=5, pady=(0, 20))
        
        # Top section with risk indicator - colored header
        top_frame = ctk.CTkFrame(
            card_frame,
            fg_color=risk_color,
            corner_radius=10
        )
        top_frame.pack(fill="x", padx=3, pady=3)
        
        risk_label = ctk.CTkLabel(
            top_frame,
            text=f"{risk_icon} File #{idx} - {risk_level} RISK",
            font=("Segoe UI", 15, "bold"),
            text_color="white"
        )
        risk_label.pack(side="left", pady=12, padx=15)
        
        filename_label = ctk.CTkLabel(
            top_frame,
            text=filename,
            font=("Segoe UI", 14),
            text_color="#ffffff"
        )
        filename_label.pack(side="left", pady=12, padx=(0, 15))
        
        # Content frame with 3 columns - improved layout
        content_frame = ctk.CTkFrame(
            card_frame,
            fg_color="transparent"
        )
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Configure grid weights for responsive layout
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=2)
        content_frame.grid_columnconfigure(2, weight=1)
        
        # Left column - File Path
        left_frame = ctk.CTkFrame(
            content_frame,
            fg_color="transparent"
        )
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        
        path_label = ctk.CTkLabel(
            left_frame,
            text="📁 File Location",
            font=("Segoe UI", 13, "bold"),
            text_color=self.colors['text']
        )
        path_label.pack(anchor="w", pady=(0, 10))
        
        path_text = ctk.CTkTextbox(
            left_frame,
            height=100,
            font=("Consolas", 11),
            wrap="word",
            corner_radius=8,
            border_width=1,
            border_color=self.colors['border']
        )
        path_text.pack(fill="both", expand=True, pady=(0, 10))
        path_text.insert("1.0", file_path)
        path_text.configure(state="disabled")
        
        if categories:
            cat_label = ctk.CTkLabel(
                left_frame,
                text="🏷️ Categories",
                font=("Segoe UI", 12, "bold"),
                text_color=self.colors['text']
            )
            cat_label.pack(anchor="w", pady=(10, 8))
            
            cat_text = ctk.CTkTextbox(
                left_frame,
                height=80,
                font=("Segoe UI", 11),
                corner_radius=8,
                border_width=1,
                border_color=self.colors['border']
            )
            cat_text.pack(fill="both", expand=True)
            cat_text.insert("1.0", "\n".join([f"• {cat}" for cat in categories]))
            cat_text.configure(state="disabled")
        
        # Middle column - Recommendations
        middle_frame = ctk.CTkFrame(
            content_frame,
            fg_color="transparent"
        )
        middle_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 15))
        
        rec_label = ctk.CTkLabel(
            middle_frame,
            text="⚠️ RECOMMENDED ACTIONS",
            font=("Segoe UI", 13, "bold"),
            text_color=risk_color
        )
        rec_label.pack(anchor="w", pady=(0, 10))
        
        rec_text = ctk.CTkTextbox(
            middle_frame,
            font=("Segoe UI", 12),
            wrap="word",
            corner_radius=8,
            border_width=1,
            border_color=self.colors['border']
        )
        rec_text.pack(fill="both", expand=True)
        
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                rec_text.insert("end", f"{i}. {rec}\n\n")
        else:
            rec_text.insert("1.0", "No specific recommendations available.")
        
        rec_text.configure(state="disabled")
        
        # Right column - Action Buttons (modern vertical layout)
        right_frame = ctk.CTkFrame(
            content_frame,
            fg_color="transparent"
        )
        right_frame.grid(row=0, column=2, sticky="nsew")
        
        actions_label = ctk.CTkLabel(
            right_frame,
            text="🎯 Quick Actions",
            font=("Segoe UI", 13, "bold"),
            text_color=self.colors['text']
        )
        actions_label.pack(anchor="w", pady=(0, 15))
        
        # Delete button
        delete_btn = ctk.CTkButton(
            right_frame,
            text="🗑️ Delete File",
            command=lambda: self.delete_sensitive_file(file_path, card_frame),
            font=("Segoe UI", 12, "bold"),
            height=45,
            corner_radius=10,
            fg_color=self.colors['danger'],
            hover_color=self.colors['danger_dark']
        )
        delete_btn.pack(fill="x", pady=(0, 12))
        
        # Vault button (coming soon)
        vault_btn = ctk.CTkButton(
            right_frame,
            text="🔒 Secure Vault",
            command=lambda: self.store_in_vault(file_path, filename),
            font=("Segoe UI", 12, "bold"),
            height=45,
            corner_radius=10,
            fg_color=self.colors['secondary'],
            hover_color=self.colors['secondary_dark']
        )
        vault_btn.pack(fill="x", pady=(0, 12))
        
        # Open location button
        open_btn = ctk.CTkButton(
            right_frame,
            text="📂 Open Folder",
            command=lambda: self.open_file_location(file_path),
            font=("Segoe UI", 12, "bold"),
            height=45,
            corner_radius=10,
            fg_color=self.colors['primary'],
            hover_color=self.colors['primary_dark']
        )
        open_btn.pack(fill="x")
    
    def delete_sensitive_file(self, file_path, card_frame):
        """Delete a sensitive file after confirmation"""
        response = messagebox.askyesno(
            "Delete Sensitive File",
            f"Are you sure you want to permanently delete this file?\n\n{file_path}\n\nThis action cannot be undone!",
            icon="warning"
        )
        
        if response:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    messagebox.showinfo(
                        "File Deleted",
                        f"File successfully deleted:\n{file_path}"
                    )
                    # Grey out the card
                    card_frame.configure(fg_color="#2B2B2B", border_color="#555555")
                    # Update all children to show deleted state
                    for widget in card_frame.winfo_children():
                        if isinstance(widget, ctk.CTkFrame):
                            widget.configure(fg_color="#2B2B2B")
                else:
                    messagebox.showerror(
                        "File Not Found",
                        f"File not found:\n{file_path}"
                    )
            except Exception as e:
                messagebox.showerror(
                    "Delete Error",
                    f"Failed to delete file:\n{str(e)}"
                )
    
    def store_in_vault(self, file_path, filename):
        """Encrypt and store file in secure vault"""
        if not os.path.exists(file_path):
            messagebox.showerror("File Not Found", f"File not found:\n{file_path}")
            return
        
        # Show password dialog
        password_dialog = ctk.CTkToplevel(self.app)
        password_dialog.title("Encrypt File")
        password_dialog.geometry("500x350")
        password_dialog.grab_set()
        password_dialog.focus()
        
        # Header
        header_label = ctk.CTkLabel(
            password_dialog,
            text="🔒 Encrypt File",
            font=("Segoe UI", 20, "bold")
        )
        header_label.pack(pady=(20, 10))
        
        info_label = ctk.CTkLabel(
            password_dialog,
            text=f"Encrypting: {filename}",
            font=("Segoe UI", 12)
        )
        info_label.pack(pady=(0, 20))
        
        # Password fields
        pass_label = ctk.CTkLabel(
            password_dialog,
            text="Enter encryption password (min 8 characters):",
            font=("Segoe UI", 12)
        )
        pass_label.pack(pady=(10, 5))
        
        password_entry = ctk.CTkEntry(
            password_dialog,
            show="•",
            width=300,
            height=40,
            font=("Segoe UI", 12)
        )
        password_entry.pack(pady=(0, 15))
        password_entry.focus()
        
        confirm_label = ctk.CTkLabel(
            password_dialog,
            text="Confirm password:",
            font=("Segoe UI", 12)
        )
        confirm_label.pack(pady=(10, 5))
        
        confirm_entry = ctk.CTkEntry(
            password_dialog,
            show="•",
            width=300,
            height=40,
            font=("Segoe UI", 12)
        )
        confirm_entry.pack(pady=(0, 15))
        
        # Delete original checkbox
        delete_var = ctk.BooleanVar(value=True)
        delete_check = ctk.CTkCheckBox(
            password_dialog,
            text="Securely delete original file after encryption",
            variable=delete_var,
            font=("Segoe UI", 11)
        )
        delete_check.pack(pady=10)
        
        def do_encryption():
            password = password_entry.get()
            confirm = confirm_entry.get()
            
            if not password:
                messagebox.showwarning("Empty Password", "Please enter a password!")
                return
            
            if len(password) < 8:
                messagebox.showwarning("Weak Password", "Password must be at least 8 characters!")
                return
            
            if password != confirm:
                messagebox.showerror("Password Mismatch", "Passwords do not match!")
                return
            
            password_dialog.destroy()
            
            # Perform encryption
            success, encrypted_path, message = self.file_encryptor.encrypt_file(
                file_path,
                password,
                delete_original=delete_var.get()
            )
            
            if success:
                messagebox.showinfo(
                    "Encryption Successful",
                    f"✅ {message}\n\nEncrypted file saved to:\n{encrypted_path}\n\nKeep your password safe!"
                )
            else:
                messagebox.showerror("Encryption Failed", f"❌ {message}")
        
        # Buttons
        button_frame = ctk.CTkFrame(password_dialog, fg_color="transparent")
        button_frame.pack(pady=20)
        
        encrypt_btn = ctk.CTkButton(
            button_frame,
            text="🔒 Encrypt",
            command=do_encryption,
            width=140,
            height=40,
            font=("Segoe UI", 13, "bold"),
            fg_color=self.colors['success'],
            hover_color=self.colors['success_dark']
        )
        encrypt_btn.pack(side="left", padx=5)
        
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=password_dialog.destroy,
            width=140,
            height=40,
            font=("Segoe UI", 13, "bold"),
            fg_color=self.colors['card'],
            hover_color=self.colors['card_hover']
        )
        cancel_btn.pack(side="left", padx=5)
        
        # Bind Enter key
        password_dialog.bind('<Return>', lambda e: do_encryption())
    
    def manage_vault(self):
        """Manage encrypted vault - view and decrypt files"""
        # Get vault stats
        stats = self.file_encryptor.get_vault_stats()
        encrypted_files = self.file_encryptor.list_encrypted_files()
        
        # Create vault management window
        vault_window = ctk.CTkToplevel(self.app)
        vault_window.title("🔐 Secure Vault Manager")
        vault_window.geometry("900x700")
        vault_window.grab_set()
        vault_window.focus()
        
        # Header
        header_frame = ctk.CTkFrame(
            vault_window,
            fg_color=self.colors['warning'],
            corner_radius=0
        )
        header_frame.pack(fill="x", padx=0, pady=0)
        
        header_label = ctk.CTkLabel(
            header_frame,
            text="🔐 Secure Vault Manager",
            font=("Segoe UI", 24, "bold"),
            text_color="white"
        )
        header_label.pack(pady=20)
        
        # Stats section
        stats_frame = ctk.CTkFrame(
            vault_window,
            fg_color=self.colors['card'],
            corner_radius=10,
            border_width=1,
            border_color=self.colors['border']
        )
        stats_frame.pack(fill="x", padx=20, pady=20)
        
        stats_text = f"""📊 Vault Statistics
        
📁 Vault Location: {stats['vault_path']}
🔒 Encrypted Files: {stats['total_files']}
💾 Total Size: {stats['total_size_mb']} MB
"""
        
        stats_label = ctk.CTkLabel(
            stats_frame,
            text=stats_text,
            font=("Segoe UI", 12),
            justify="left"
        )
        stats_label.pack(padx=20, pady=15, anchor="w")
        
        # Files list section
        list_label = ctk.CTkLabel(
            vault_window,
            text="🔒 Encrypted Files",
            font=("Segoe UI", 16, "bold")
        )
        list_label.pack(anchor="w", padx=20, pady=(10, 10))
        
        # Scrollable frame for files
        files_frame = ctk.CTkScrollableFrame(
            vault_window,
            fg_color="transparent"
        )
        files_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        if not encrypted_files:
            no_files_label = ctk.CTkLabel(
                files_frame,
                text="📭 No encrypted files in vault\\n\\nEncrypt sensitive files using the '🔒 Secure Vault' button in scan results.",
                font=("Segoe UI", 13),
                text_color=self.colors['text_muted']
            )
            no_files_label.pack(pady=50)
        else:
            # Display each encrypted file
            for idx, file_path in enumerate(encrypted_files, 1):
                filename = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                file_size_mb = round(file_size / (1024 * 1024), 2)
                
                # File card
                file_card = ctk.CTkFrame(
                    files_frame,
                    fg_color=self.colors['card'],
                    corner_radius=10,
                    border_width=1,
                    border_color=self.colors['border']
                )
                file_card.pack(fill="x", pady=5)
                
                # File info
                info_frame = ctk.CTkFrame(file_card, fg_color="transparent")
                info_frame.pack(side="left", fill="both", expand=True, padx=15, pady=10)
                
                name_label = ctk.CTkLabel(
                    info_frame,
                    text=f"🔒 {filename}",
                    font=("Segoe UI", 12, "bold"),
                    anchor="w"
                )
                name_label.pack(anchor="w")
                
                size_label = ctk.CTkLabel(
                    info_frame,
                    text=f"Size: {file_size_mb} MB",
                    font=("Segoe UI", 10),
                    text_color=self.colors['text_muted'],
                    anchor="w"
                )
                size_label.pack(anchor="w")
                
                # Action buttons
                button_frame = ctk.CTkFrame(file_card, fg_color="transparent")
                button_frame.pack(side="right", padx=15, pady=10)
                
                decrypt_btn = ctk.CTkButton(
                    button_frame,
                    text="🔓 Decrypt",
                    command=lambda fp=file_path, fn=filename: self.decrypt_file_from_vault(fp, fn),
                    width=120,
                    height=35,
                    font=("Segoe UI", 11, "bold"),
                    fg_color=self.colors['success'],
                    hover_color=self.colors['success_dark']
                )
                decrypt_btn.pack(side="left", padx=5)
                
                delete_btn = ctk.CTkButton(
                    button_frame,
                    text="🗑️",
                    command=lambda fp=file_path, fc=file_card: self.delete_from_vault(fp, fc),
                    width=50,
                    height=35,
                    font=("Segoe UI", 11),
                    fg_color=self.colors['danger'],
                    hover_color=self.colors['danger_dark']
                )
                delete_btn.pack(side="left")
        
        # Close button
        close_btn = ctk.CTkButton(
            vault_window,
            text="Close",
            command=vault_window.destroy,
            width=150,
            height=40,
            font=("Segoe UI", 13, "bold"),
            fg_color=self.colors['card'],
            hover_color=self.colors['card_hover']
        )
        close_btn.pack(pady=(0, 20))
    
    def decrypt_file_from_vault(self, encrypted_path, filename):
        """Decrypt a file from the vault"""
        # Password dialog
        password_dialog = ctk.CTkToplevel(self.app)
        password_dialog.title("Decrypt File")
        password_dialog.geometry("500x300")
        password_dialog.grab_set()
        password_dialog.focus()
        
        # Header
        header_label = ctk.CTkLabel(
            password_dialog,
            text="🔓 Decrypt File",
            font=("Segoe UI", 20, "bold")
        )
        header_label.pack(pady=(20, 10))
        
        info_label = ctk.CTkLabel(
            password_dialog,
            text=f"Decrypting: {filename}",
            font=("Segoe UI", 12)
        )
        info_label.pack(pady=(0, 20))
        
        # Password field
        pass_label = ctk.CTkLabel(
            password_dialog,
            text="Enter decryption password:",
            font=("Segoe UI", 12)
        )
        pass_label.pack(pady=(10, 5))
        
        password_entry = ctk.CTkEntry(
            password_dialog,
            show="•",
            width=300,
            height=40,
            font=("Segoe UI", 12)
        )
        password_entry.pack(pady=(0, 15))
        password_entry.focus()
        
        # Delete encrypted file checkbox
        delete_var = ctk.BooleanVar(value=False)
        delete_check = ctk.CTkCheckBox(
            password_dialog,
            text="Delete encrypted file after decryption",
            variable=delete_var,
            font=("Segoe UI", 11)
        )
        delete_check.pack(pady=10)
        
        def do_decryption():
            password = password_entry.get()
            
            if not password:
                messagebox.showwarning("Empty Password", "Please enter the decryption password!")
                return
            
            password_dialog.destroy()
            
            # Perform decryption
            success, decrypted_path, message = self.file_encryptor.decrypt_file(
                encrypted_path,
                password,
                delete_encrypted=delete_var.get()
            )
            
            if success:
                messagebox.showinfo(
                    "Decryption Successful",
                    f"✅ {message}\\n\\nDecrypted file saved to:\\n{decrypted_path}"
                )
                # Refresh vault window if still open
            else:
                messagebox.showerror("Decryption Failed", f"❌ {message}")
        
        # Buttons
        button_frame = ctk.CTkFrame(password_dialog, fg_color="transparent")
        button_frame.pack(pady=20)
        
        decrypt_btn = ctk.CTkButton(
            button_frame,
            text="🔓 Decrypt",
            command=do_decryption,
            width=140,
            height=40,
            font=("Segoe UI", 13, "bold"),
            fg_color=self.colors['success'],
            hover_color=self.colors['success_dark']
        )
        decrypt_btn.pack(side="left", padx=5)
        
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=password_dialog.destroy,
            width=140,
            height=40,
            font=("Segoe UI", 13, "bold"),
            fg_color=self.colors['card'],
            hover_color=self.colors['card_hover']
        )
        cancel_btn.pack(side="left", padx=5)
        
        # Bind Enter key
        password_dialog.bind('<Return>', lambda e: do_decryption())
    
    def delete_from_vault(self, file_path, card_frame):
        """Delete an encrypted file from vault"""
        filename = os.path.basename(file_path)
        
        response = messagebox.askyesno(
            "Delete Encrypted File",
            f"Are you sure you want to delete this encrypted file?\\n\\n{filename}\\n\\nThis action cannot be undone!",
            icon="warning"
        )
        
        if response:
            try:
                os.remove(file_path)
                card_frame.destroy()
                messagebox.showinfo("Deleted", f"Encrypted file deleted:\\n{filename}")
            except Exception as e:
                messagebox.showerror("Delete Error", f"Failed to delete file:\\n{str(e)}")
    
    def open_file_location(self, file_path):
        """Open the folder containing the file"""
        try:
            folder_path = os.path.dirname(file_path)
            if os.path.exists(folder_path):
                if os.name == 'nt':  # Windows
                    os.startfile(folder_path)
                elif os.name == 'posix':  # macOS/Linux
                    import subprocess
                    subprocess.Popen(['xdg-open', folder_path])
            else:
                messagebox.showerror(
                    "Folder Not Found",
                    f"Folder not found:\n{folder_path}"
                )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to open folder:\n{str(e)}"
            )

    
    def display_partial_results(self, results):
        """Display partial results when scan is stopped"""
        self.display_results(results)
        # Add note about partial results
        self.results_text.insert("1.0", "⚠️  PARTIAL RESULTS - Scan was stopped by user\n\n")
    
    def scan_complete(self):
        """Reset UI after scan completion"""
        self.is_scanning = False
        self.stop_requested = False
        self.scan_btn.configure(state="normal", text="🚀 Start Privacy Scan")
        self.stop_btn.configure(state="disabled")
        self.progress_bar.set(1.0)
        
        if not self.stop_requested:
            self.progress_label.configure(text="Scan complete!")
            self.status_label.configure(text="Scan complete - Ready for next scan")
            
            # Auto-detect sensitive files if encoding was enabled and auto-detect is on
            if self.enable_encoding_var.get() and self.auto_detect_sensitive_var.get():
                self.app.after(500, self.find_sensitive_documents)  # Small delay for UI update
        else:
            self.progress_label.configure(text="Scan stopped")
            self.status_label.configure(text="Scan stopped - Ready for next scan")
    
    def clear_results(self):
        """Clear the results text box"""
        self.results_text.delete("1.0", "end")
        self.results_text.insert("1.0", "Results will appear here after scanning...\n")
    
    def export_results(self):
        """Export results to a file"""
        content = self.results_text.get("1.0", "end")
        if not content.strip() or "Results will appear here" in content:
            messagebox.showinfo("No Results", "No results to export!")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Results As"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("Export Successful", f"Results exported to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export results:\n{str(e)}")
    
    def encode_documents(self):
        """Encode all txt/md files and OCR results to vector database"""
        if self.is_encoding:
            messagebox.showwarning("Encoding in Progress", "Document encoding is already running!")
            return
        
        if self.is_scanning:
            messagebox.showwarning("Scan in Progress", "Please wait for the scan to complete first!")
            return
        
        # Get configuration
        db_path = self.db_path
        if not db_path:
            db_path = "./chroma_db"
        
        output_folder = self.output_folder
        if not output_folder:
            output_folder = "ocr_result"
        
        # Get folder to scan
        folder = self.folder_entry.get().strip()
        if not folder:
            folder = "."
        
        # Confirm action
        response = messagebox.askyesno(
            "Encode Documents",
            "This will encode all .txt and .md files (from file lists) and OCR results to the vector database.\n\nContinue?"
        )
        
        if not response:
            return
        
        # Disable encode button
        self.is_encoding = True
        self.encode_btn.configure(state="disabled", text="⏳ Encoding...")
        self.clear_results()
        
        # Start encoding in separate thread
        self.encode_thread = threading.Thread(
            target=self.run_encoding,
            args=(db_path, output_folder, folder),
            daemon=True
        )
        self.encode_thread.start()
    
    def run_encoding(self, db_path, output_folder, scan_directory):
        """Execute document encoding (runs in separate thread)"""
        try:
            self.app.after(0, lambda: self.progress_label.configure(text="Initializing encoder..."))
            self.app.after(0, lambda: self.progress_bar.set(0.1))
            
            # Create encoder
            encoder = DocumentEncoder(
                file_lists_folder="temp",
                ocr_result_folder=output_folder,
                db_path=db_path,
                scan_directory=scan_directory
            )
            
            self.app.after(0, lambda: self.progress_label.configure(text="Encoding documents..."))
            self.app.after(0, lambda: self.progress_bar.set(0.3))
            
            # Encode all documents
            stats = encoder.encode_all_documents(
                use_chunking=True,
                include_ocr=True
            )
            
            self.app.after(0, lambda: self.progress_bar.set(1.0))
            
            # Display results
            result_text = f"""{'='*80}
DOCUMENT ENCODING COMPLETE
{'='*80}
Total files: {stats['total_files']}
Successfully encoded: {stats['successful']}
Failed: {stats['failed']}
OCR files: {stats.get('ocr_files', 0)}
Text/MD files: {stats.get('text_files', 0)}

Database location: {db_path}
Total documents in database: {encoder.collection.count()}
{'='*80}
"""
            
            self.app.after(0, lambda: self.results_text.delete("1.0", "end"))
            self.app.after(0, lambda: self.results_text.insert("1.0", result_text))
            self.app.after(0, lambda: self.progress_label.configure(text="Encoding complete!"))
            
            self.app.after(0, lambda: messagebox.showinfo(
                "Encoding Complete",
                f"Successfully encoded {stats['successful']} out of {stats['total_files']} files to the vector database!"
            ))
            
            # Auto-detect sensitive files if enabled
            if self.auto_detect_sensitive_var.get():
                self.app.after(0, lambda: self.progress_label.configure(text="Searching for sensitive files..."))
                self.app.after(0, lambda: self.progress_bar.set(0.5))
                # Trigger sensitive document search
                self.app.after(500, self.find_sensitive_documents)  # Small delay for UI update
            
        except Exception as e:
            self.app.after(0, lambda: messagebox.showerror(
                "Encoding Error",
                f"An error occurred during encoding:\n{str(e)}"
            ))
            self.app.after(0, lambda: self.progress_label.configure(text=f"Encoding failed: {str(e)}"))
        finally:
            self.app.after(0, self.encoding_complete)
    
    def encoding_complete(self):
        """Reset UI after encoding completion"""
        self.is_encoding = False
        self.encode_btn.configure(state="normal", text="📚 Encode Documents")
    
    def search_database(self):
        """Search the vector database"""
        db_path = self.db_path
        if not db_path:
            db_path = "./chroma_db"
        
        # Check if database exists
        if not os.path.exists(db_path):
            messagebox.showwarning(
                "Database Not Found",
                f"Vector database not found at: {db_path}\n\nPlease encode documents first."
            )
            return
        
        # Create search dialog
        search_window = ctk.CTkToplevel(self.app)
        search_window.title("Search Vector Database")
        search_window.geometry("800x600")
        
        # Make it modal
        search_window.grab_set()
        search_window.focus()
        
        # Search input
        input_frame = ctk.CTkFrame(search_window)
        input_frame.pack(fill="x", padx=20, pady=20)
        
        search_label = ctk.CTkLabel(
            input_frame,
            text="Enter your search query:",
            font=("Arial", 14, "bold")
        )
        search_label.pack(pady=(0, 10))
        
        search_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="E.g., personal information, contact details, sensitive data...",
            font=("Arial", 12),
            width=600
        )
        search_entry.pack(pady=(0, 10))
        
        results_label = ctk.CTkLabel(
            input_frame,
            text="Number of results:",
            font=("Arial", 12)
        )
        results_label.pack(side="left", padx=(0, 10))
        
        n_results_var = ctk.IntVar(value=5)
        n_results_entry = ctk.CTkEntry(
            input_frame,
            textvariable=n_results_var,
            width=60,
            font=("Arial", 12)
        )
        n_results_entry.pack(side="left", padx=(0, 10))
        
        # Results display - create BEFORE the function that uses it
        search_results = ctk.CTkTextbox(
            search_window,
            font=("Consolas", 11),
            wrap="word"
        )
        search_results.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        search_results.insert("1.0", "Enter a query and click Search to find relevant documents...")
        
        def perform_search():
            query = search_entry.get().strip()
            if not query:
                messagebox.showwarning("Empty Query", "Please enter a search query!")
                return
            
            try:
                n_results = n_results_var.get()
                encoder = DocumentEncoder(db_path=db_path)
                results = encoder.search_similar(query, n_results=n_results)
                
                # Display results
                search_results.delete("1.0", "end")
                
                if results and results['documents'] and results['documents'][0]:
                    search_results.insert("end", f"Search Results for: '{query}'\n{'='*80}\n\n")
                    
                    for idx, (doc, metadata, distance) in enumerate(zip(
                        results['documents'][0],
                        results['metadatas'][0],
                        results['distances'][0]
                    ), 1):
                        search_results.insert("end", f"{idx}. {metadata.get('filename', 'Unknown')}\n")
                        search_results.insert("end", f"   Similarity: {1 - distance:.4f}\n")
                        search_results.insert("end", f"   Source: {'OCR' if metadata.get('is_ocr') else 'Text/MD'}\n")
                        search_results.insert("end", f"   Preview: {doc[:300]}...\n")
                        search_results.insert("end", "-" * 80 + "\n\n")
                else:
                    search_results.insert("end", "No results found.")
                    
            except Exception as e:
                messagebox.showerror("Search Error", f"Error searching database:\n{str(e)}")
        
        search_btn = ctk.CTkButton(
            input_frame,
            text="🔍 Search",
            command=perform_search,
            font=("Arial", 12, "bold")
        )
        search_btn.pack(side="left")
    
    def show_db_stats(self):
        """Show database statistics"""
        db_path = self.db_path
        if not db_path:
            db_path = "./chroma_db"
        
        if not os.path.exists(db_path):
            messagebox.showwarning(
                "Database Not Found",
                f"Vector database not found at: {db_path}\n\nPlease encode documents first."
            )
            return
        
        try:
            encoder = DocumentEncoder(db_path=db_path)
            stats = encoder.get_collection_stats()
            
            messagebox.showinfo(
                "Database Statistics",
                f"Vector Database Stats\n\nLocation: {db_path}\nCollection: documents\nTotal documents: {stats.get('count', 0)}\n\nEmbedding Model: google/embeddinggemma-300m"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Error getting database stats:\n{str(e)}")
    
    def find_sensitive_documents(self):
        """Analyze documents with LLM to find sensitive/critical information (reads directly from files)"""
        # Check LLM server
        llm_url = self.llm_url
        if not llm_url:
            llm_url = "http://localhost:8080"
        
        output_folder = self.output_folder
        if not output_folder:
            output_folder = "ocr_result"
        
        self.clear_results()
        self.results_text.insert("1.0", "🔍 Analyzing documents for sensitive information...\n\n")
        self.progress_bar.set(0.1)
        
        # Run analysis in background thread
        def analyze_sensitive():
            try:
                self.app.after(0, lambda: self.progress_label.configure(text="Initializing LLM..."))
                
                # Initialize LLM client
                llm_client = LlamaCppClient(base_url=llm_url)
                
                if not llm_client.check_server_status():
                    self.app.after(0, lambda: messagebox.showerror(
                        "LLM Server Not Found",
                        f"LLM server is not running at {llm_url}\n\nPlease start llama.cpp server first."
                    ))
                    self.app.after(0, lambda: self.progress_bar.set(0))
                    return
                
                self.app.after(0, lambda: self.progress_label.configure(text="Collecting files to analyze..."))
                self.app.after(0, lambda: self.progress_bar.set(0.15))
                
                # Collect OCR files to analyze (only from current scan - not all files in folder)
                all_files = []
                
                # Get OCR files from the last scan results only (newly created OCR files)
                if self.last_scan_results:
                    for result in self.last_scan_results:
                        # Only process images that have OCR files from this scan
                        if result.get('file_type') == 'image' and result.get('ocr_file'):
                            ocr_file_path = result.get('ocr_file')
                            if os.path.isfile(ocr_file_path):
                                all_files.append((ocr_file_path, True))  # (path, is_ocr)
                
                # Note: We do NOT analyze txt/md files here as they are already analyzed during initial scan
                # This prevents duplicate analysis of non-image text content
                
                if not all_files:
                    # Check if no scan was performed
                    if not self.last_scan_results:
                        self.app.after(0, lambda: messagebox.showinfo(
                            "No Scan Results",
                            "No scan has been performed yet.\n\nPlease run 'Start Privacy Scan' first to scan images."
                        ))
                    else:
                        self.app.after(0, lambda: messagebox.showinfo(
                            "No Images to Analyze",
                            "No images were found in the last scan.\n\nMake sure OCR is enabled and images exist in the selected folder."
                        ))
                    self.app.after(0, lambda: self.progress_bar.set(0))
                    return
                
                total_files = len(all_files)
                self.app.after(0, lambda: self.progress_label.configure(text=f"Analyzing {total_files} documents..."))
                
                # System prompt for LLM analysis
                system_prompt = """You are a privacy and security analyzer. Your task is to analyze document content and identify if it contains sensitive or critical information.

Sensitive information includes:
- Personal identification (SSN, passport, driver's license, ID numbers)
- Financial information (credit cards, bank accounts, financial records)
- Credentials (passwords, API keys, tokens, secrets)
- Medical/health records (diagnoses, prescriptions, medical history)
- Confidential business information (trade secrets, proprietary data)
- Personal contact information in sensitive contexts (addresses, phone, email with personal data)
- Biometric data (fingerprints, facial recognition, DNA)

Respond with a JSON object:
{
  "is_sensitive": true/false,
  "confidence": "high"/"medium"/"low",
  "categories": ["category1", "category2"],
  "risk_level": "critical"/"high"/"medium"/"low",
  "explanation": "Brief explanation",
  "specific_findings": ["finding1", "finding2"],
  "recommendations": ["recommendation1", "recommendation2"]
}"""
                
                sensitive_files = {}
                
                for idx, (filepath, is_ocr) in enumerate(all_files, 1):
                    progress = 0.15 + (idx / total_files) * 0.75
                    filename = Path(filepath).name
                    self.app.after(0, lambda p=progress, f=filename: (
                        self.progress_bar.set(p),
                        self.progress_label.configure(text=f"Analyzing: {f}...")
                    ))
                    
                    # Read file content
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                    except Exception as e:
                        import logging
                        logging.warning(f"Failed to read {filepath}: {e}")
                        continue
                    
                    # Skip empty files
                    if not content.strip():
                        continue
                    
                    # Truncate content if too long (max ~10000 chars)
                    content_truncated = content[:10000]
                    
                    query = f"""Analyze this document and determine if it contains sensitive information:

{content_truncated}

Respond ONLY with the JSON object, no other text."""
                    
                    try:
                        result = llm_client.query_with_json_response(
                            query=query,
                            system_prompt=system_prompt,
                            max_retries=2,
                            temperature=0.1,
                            max_tokens=300
                        )
                        
                        if result.get('is_sensitive', False):
                            sensitive_files[filepath] = {
                                'filename': filename,
                                'is_ocr': is_ocr,
                                'analysis': result,
                                'preview': content_truncated[:500]
                            }
                    
                    except Exception as e:
                        import logging
                        logging.warning(f"Failed to analyze {filename}: {e}")
                        continue
                
                self.app.after(0, lambda: self.progress_bar.set(0.95))
                self.app.after(0, lambda: self.progress_label.configure(text="Preparing results..."))
                
                # Sort by risk level
                risk_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
                sorted_results = sorted(
                    sensitive_files.items(),
                    key=lambda x: risk_order.get(x[1]['analysis'].get('risk_level', 'low'), 3)
                )
                
                # Display results
                self.app.after(0, lambda: self.progress_bar.set(1.0))
                self.app.after(0, lambda: self.progress_label.configure(text="Analysis complete!"))
                
                # Merge with stored scan results (text files)
                self.app.after(0, lambda: self.display_combined_results(sorted_results))
                
            except Exception as e:
                self.app.after(0, lambda: messagebox.showerror(
                    "Analysis Error",
                    f"Error analyzing documents:\n{str(e)}"
                ))
                self.app.after(0, lambda: self.progress_label.configure(text="Analysis failed"))
                self.app.after(0, lambda: self.progress_bar.set(0))
        
        threading.Thread(target=analyze_sensitive, daemon=True).start()
    
    def display_combined_results(self, ocr_analysis_results):
        """Display combined results from text file analysis and OCR analysis in one popup"""
        # Convert OCR analysis results to scan format
        ocr_results = []
        for filepath, data in ocr_analysis_results:
            analysis = data['analysis']
            
            # Get recommendations from analysis, fallback to generic if not provided
            recommendations = analysis.get('recommendations', [])
            if not recommendations:
                recommendations = ['Review and secure this file.']
            
            # Get specific findings from analysis
            specific_findings = analysis.get('specific_findings', [])
            if not specific_findings:
                specific_findings = [analysis.get('explanation', 'Sensitive content detected')]
            
            ocr_results.append({
                'filename': data['filename'],
                'file_path': filepath,
                'file_type': 'image',
                'risk_level': analysis.get('risk_level', 'low'),
                'contains_sensitive_info': True,
                'detected_categories': analysis.get('categories', []),
                'specific_findings': specific_findings,
                'recommendations': recommendations,
                'confidence': analysis.get('confidence', 'unknown')
            })
        
        # Get sensitive text files from stored scan results
        text_sensitive_files = [r for r in self.last_scan_results if r.get('risk_level') in ['critical', 'high', 'medium']]
        
        # Combine both
        all_sensitive_files = text_sensitive_files + ocr_results
        
        # Update main text area
        self.results_text.delete("1.0", "end")
        
        if not all_sensitive_files:
            self.results_text.insert("1.0", 
                "✅ No sensitive documents found!\n\n"
                "Your scanned documents appear to be safe.\n\n"
                "Note: All documents have been analyzed for sensitive information.\n"
                "Always manually review critical documents for complete security."
            )
            messagebox.showinfo(
                "Analysis Complete",
                "✅ No sensitive documents found!\n\nYour documents appear to be safe."
            )
            return
        
        # Count by type
        text_count = len(text_sensitive_files)
        image_count = len(ocr_results)
        
        summary = f"""{'='*80}
🚨 SENSITIVE DOCUMENTS FOUND: {len(all_sensitive_files)}
{'='*80}

Analysis Complete:
• Text/MD Files: {text_count} sensitive file(s)
• Images (OCR): {image_count} sensitive file(s)

A detailed review window has been opened showing:
• File locations
• Risk levels and categories
• Recommended actions
• Quick action buttons

Please review each file carefully and take appropriate action.
{'='*80}
"""
        self.results_text.insert("end", summary)
        
        # Show combined popup
        self.show_results_popup(all_sensitive_files)
    
    def display_sensitive_results(self, results):
        """Display LLM-analyzed sensitive documents in popup"""
        self.results_text.delete("1.0", "end")
        
        if not results:
            self.results_text.insert("1.0", 
                "✅ No sensitive documents found!\n\n"
                "Your scanned documents appear to be safe.\n\n"
                "Note: The LLM analyzed all documents for sensitive information.\n"
                "Always manually review critical documents for complete security."
            )
            messagebox.showinfo(
                "Analysis Complete",
                "✅ No sensitive documents found!\n\nYour documents appear to be safe."
            )
            return
        
        # Show summary in main text area
        summary = f"""{'='*80}
🚨 SENSITIVE DOCUMENTS FOUND: {len(results)}
{'='*80}

The LLM has analyzed all documents and found {len(results)} file(s) containing
sensitive or critical information.

A detailed review window has been opened showing:
• File locations
• Recommended actions
• Quick action buttons to delete or secure files

Please review each file carefully and take appropriate action.
{'='*80}
"""
        self.results_text.insert("end", summary)
        
        # Convert results to scan format and show popup
        converted_results = []
        for filepath, data in results:
            analysis = data['analysis']
            
            # Convert to scan result format
            converted = {
                'filename': data['filename'],
                'file_path': filepath,
                'file_type': 'text/markdown',
                'risk_level': analysis.get('risk_level', 'low'),
                'contains_sensitive_info': True,
                'detected_categories': analysis.get('detected_categories', []),
                'specific_findings': analysis.get('specific_findings', []),
                'recommendations': analysis.get('recommendations', ['Review and secure this file.']),
                'confidence': analysis.get('confidence', 'unknown')
            }
            
            converted_results.append(converted)
        
        # Show popup with results
        self.show_results_popup(converted_results)
    
    def quick_query_database(self):
        """Quick search of vector database from main UI"""
        query = self.query_entry.get().strip()
        
        if not query:
            messagebox.showwarning("Empty Query", "Please enter a search query!")
            return
        
        db_path = self.db_path
        if not db_path:
            db_path = "./chroma_db"
        
        if not os.path.exists(db_path):
            messagebox.showwarning(
                "Database Not Found",
                f"Vector database not found at: {db_path}\n\nPlease encode documents first.\n\nUse '📚 Encode Documents' button to create the database."
            )
            return
        
        # Get number of results
        try:
            n_results = int(self.n_results_var.get())
            if n_results < 1:
                n_results = 5
        except ValueError:
            n_results = 5
            self.n_results_var.set("5")
        
        # Clear results and show searching message
        self.clear_results()
        self.results_text.insert("1.0", f"🔍 Searching for: '{query}'...\n\n")
        self.progress_bar.set(0.3)
        self.progress_label.configure(text=f"Searching database...")
        
        # Disable search button
        self.quick_search_btn.configure(state="disabled", text="⏳ Searching...")
        
        # Search in background thread
        def perform_search():
            try:
                self.app.after(0, lambda: self.progress_bar.set(0.5))
                
                encoder = DocumentEncoder(db_path=db_path)
                results = encoder.search_similar(query, n_results=n_results)
                
                self.app.after(0, lambda: self.progress_bar.set(0.9))
                
                # Display results
                self.app.after(0, lambda: self.display_query_results(query, results, n_results))
                
            except Exception as e:
                self.app.after(0, lambda: messagebox.showerror(
                    "Search Error",
                    f"Error searching database:\n{str(e)}"
                ))
                self.app.after(0, lambda: self.clear_results())
            finally:
                self.app.after(0, lambda: self.quick_search_btn.configure(state="normal", text="🔍 Search"))
                self.app.after(0, lambda: self.progress_bar.set(0))
                self.app.after(0, lambda: self.progress_label.configure(text="Ready"))
        
        threading.Thread(target=perform_search, daemon=True).start()
    
    def display_query_results(self, query, results, n_results):
        """Display quick query search results"""
        self.results_text.delete("1.0", "end")
        
        if not results or not results['documents'] or not results['documents'][0]:
            self.results_text.insert("1.0",
                f"{'='*80}\n"
                f"SEARCH RESULTS\n"
                f"{'='*80}\n\n"
                f"Query: '{query}'\n\n"
                f"❌ No results found.\n\n"
                f"Try:\n"
                f"• Different keywords\n"
                f"• More general terms\n"
                f"• Check if documents are encoded (use '📚 Encode Documents')\n"
            )
            return
        
        # Header
        header = f"""{'='*80}
SEARCH RESULTS
{'='*80}

Query: '{query}'
Found: {len(results['documents'][0])} result(s)

"""
        self.results_text.insert("end", header)
        
        # Display each result
        for idx, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        ), 1):
            filename = metadata.get('filename', 'Unknown')
            filepath = metadata.get('filepath', 'N/A')
            is_ocr = metadata.get('is_ocr', False)
            file_ext = metadata.get('extension', '')
            similarity = 1 - distance
            
            # Similarity indicator
            if similarity > 0.85:
                sim_icon = "🟢 Excellent"
            elif similarity > 0.7:
                sim_icon = "🟡 Good"
            elif similarity > 0.5:
                sim_icon = "🟠 Fair"
            else:
                sim_icon = "🔴 Weak"
            
            result = f"""
{idx}. {filename}
   Similarity: {sim_icon} ({similarity:.2%})
   Source: {'OCR Result' if is_ocr else f'Document ({file_ext})'}
   Path: {filepath}
   
   Preview:
   {doc[:400]}{'...' if len(doc) > 400 else ''}

{'-'*80}
"""
            self.results_text.insert("end", result)
        
        # Footer
        footer = f"\n{'='*80}\n"
        if len(results['documents'][0]) >= n_results:
            footer += f"Showing top {n_results} results. Increase 'Results' number for more.\n"
        footer += f"{'='*80}\n"
        
        self.results_text.insert("end", footer)
        
        # Update status
        self.status_label.configure(text=f"Found {len(results['documents'][0])} result(s) for: {query}")
    
    def run(self):
        """Start the application"""
        self.app.mainloop()


# Run the application
if __name__ == "__main__":
    app = PrivacyScannerApp()
    app.run()