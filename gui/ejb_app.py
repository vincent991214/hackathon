"""
EJB Analysis Tab Module

This module contains the EJB Analysis tab functionality for the DevMate AI application.
It provides a mixin class that can be used with the main application class.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import json

# Import shared components
from gui.common import (
    BG_COLOR, INPUT_BG, RichTextRenderer
)


class EJBTabMixin:
    """
    Mixin class that adds EJB Analysis tab functionality to the main application.

    This class provides all the EJB-related UI components and methods.
    To use, mix this class with your main application class:

        class DocGeneratorApp(EJBTabMixin):
            def __init__(self, root):
                # Initialize parent
                # Then call self._init_ejb_state()
                # And use self._build_tab_ejb() to build the tab
    """

    def _init_ejb_state(self):
        """Initialize EJB-related state variables."""
        self.ejb_interfaces = []
        self.ejb_selected_interface = None
        self.ejb_symbol_table = {}
        self.ejb_chroma_manager = None
        self.ejb_path_var = tk.StringVar()
        self.ejb_interface_combo_var = tk.StringVar()
        self.ejb_status_var = tk.StringVar(value="Status: Waiting for project")

    # ================= TAB 5: EJB ANALYSIS =================
    def _build_tab_ejb(self):
        """Build the EJB Analysis tab UI."""
        # Get the tab frame (should be defined in main app)
        if not hasattr(self, 'tab_ejb'):
            raise AttributeError("Main app must define 'tab_ejb' frame before calling _build_tab_ejb()")

        frame = ttk.Frame(self.tab_ejb)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Header
        header_frame = ttk.Frame(frame)
        header_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(header_frame, text="EJB Interface Analysis", style="Header.TLabel").pack(side="left")
        ttk.Label(header_frame, text="Upload ZIP or select folder to analyze EJB interfaces",
                 foreground="#888", font=("Segoe UI", 9)).pack(side="left", padx=(15, 0))

        # Main Content Area - Split into Left (Controls) and Right (Output)
        paned = tk.PanedWindow(frame, orient=tk.HORIZONTAL, bg=BG_COLOR, sashwidth=4)
        paned.pack(fill="both", expand=True)

        # Left Panel: Upload and Selection
        left_panel = ttk.Frame(paned)
        paned.add(left_panel, width=350)

        # Upload Section
        ttk.Label(left_panel, text="Upload Project", style="SubHeader.TLabel").pack(anchor="w", pady=(10, 5))

        upload_frame = ttk.Frame(left_panel)
        upload_frame.pack(fill="x", pady=5)

        entry = tk.Entry(upload_frame, textvariable=self.ejb_path_var, width=30,
                        font=("Segoe UI", 10), bg=INPUT_BG, fg="white", relief="flat")
        entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 5))

        ttk.Button(upload_frame, text="Browse", command=self.ejb_select_folder).pack(side="left")

        ttk.Button(left_panel, text="Upload ZIP", command=self.ejb_upload_zip).pack(fill="x", pady=5)

        ttk.Button(left_panel, text="ANALYZE EJB PROJECT", style="Green.TButton",
                  command=self.ejb_analyze_project).pack(fill="x", pady=15, ipady=8)

        ttk.Label(left_panel, textvariable=self.ejb_status_var, foreground="#888").pack(anchor="w", pady=(5, 15))

        # Interface Selection Section
        ttk.Label(left_panel, text="Select Interface", style="SubHeader.TLabel").pack(anchor="w", pady=(10, 5))

        self.ejb_interface_combo = ttk.Combobox(left_panel, textvariable=self.ejb_interface_combo_var,
                                                 state="readonly", font=("Segoe UI", 10))
        self.ejb_interface_combo.pack(fill="x", pady=5)

        ttk.Button(left_panel, text="GENERATE DOCUMENTATION", style="Green.TButton",
                  command=self.ejb_generate_docs).pack(fill="x", pady=15, ipady=8)

        # Options
        ttk.Label(left_panel, text="Options", style="SubHeader.TLabel").pack(anchor="w", pady=(15, 5))

        ttk.Button(left_panel, text="View Interface List", command=self.ejb_view_interfaces).pack(fill="x", pady=5)
        ttk.Button(left_panel, text="Export JSON Manifest", command=self.ejb_export_manifest).pack(fill="x", pady=5)

        # Right Panel: Documentation Output
        right_panel = ttk.Frame(paned)
        paned.add(right_panel)

        ttk.Label(right_panel, text="Generated Documentation", style="SubHeader.TLabel").pack(anchor="w", padx=10, pady=(10, 5))

        # Documentation Display with Scrollbar
        doc_container = ttk.Frame(right_panel)
        doc_container.pack(fill="both", expand=True, padx=10, pady=10)

        doc_scroll = ttk.Scrollbar(doc_container)
        self.ejb_doc_display = tk.Text(doc_container, bg=BG_COLOR, fg="#dcdcdc",
                                      font=("Segoe UI", 11), relief="flat", wrap="word",
                                      yscrollcommand=doc_scroll.set)
        doc_scroll.config(command=self.ejb_doc_display.yview)

        doc_scroll.pack(side="right", fill="y")
        self.ejb_doc_display.pack(side="left", fill="both", expand=True)

        self.ejb_doc_renderer = RichTextRenderer(self.ejb_doc_display, self.root)

        # Export Button
        ttk.Button(right_panel, text="Export to Word", command=self.ejb_export_to_word).pack(
            fill="x", padx=10, pady=10, ipady=5)

    def ejb_select_folder(self):
        """Handle folder selection for EJB project."""
        f = filedialog.askdirectory()
        if f:
            self.ejb_path_var.set(f)

    def ejb_upload_zip(self):
        """Handle ZIP file upload for EJB project."""
        f = filedialog.askopenfilename(
            title="Select EJB Project ZIP",
            filetypes=[("ZIP Files", "*.zip")]
        )
        if f:
            self.ejb_path_var.set(f)

    def ejb_analyze_project(self):
        """Analyze the EJB project and build RAG index."""
        project_input = self.ejb_path_var.get()
        if not project_input:
            messagebox.showerror("Error", "Please select a project folder or ZIP file.")
            return

        def task():
            self.root.after(0, lambda: self.ejb_status_var.set("Status: Analyzing..."))

            try:
                # Check if it's a ZIP file or directory
                if project_input.endswith('.zip'):
                    from utils.ejb_parser import extract_from_zip, validate_ejb_project
                    import tempfile

                    with tempfile.TemporaryDirectory() as temp_dir:
                        extracted_path = extract_from_zip(project_input, temp_dir)

                        # Validate EJB project
                        is_valid, message = validate_ejb_project(extracted_path)
                        if not is_valid:
                            self.root.after(0, lambda: messagebox.showerror(
                                "Invalid EJB Project", message))
                            self.root.after(0, lambda: self.ejb_status_var.set(f"Status: Error - {message}"))
                            return

                        # Parse the project
                        from utils.ejb_parser import EJBParser
                        parser = EJBParser(extracted_path)
                        symbol_table, interfaces = parser.parse()

                        self.ejb_symbol_table = symbol_table
                        self.ejb_interfaces = interfaces

                else:
                    # It's a directory
                    from utils.ejb_parser import EJBParser, validate_ejb_project

                    # Validate EJB project
                    is_valid, message = validate_ejb_project(project_input)
                    if not is_valid:
                        self.root.after(0, lambda: messagebox.showerror(
                            "Invalid EJB Project", message))
                        self.root.after(0, lambda: self.ejb_status_var.set(f"Status: Error - {message}"))
                        return

                    # Parse the project
                    parser = EJBParser(project_input)
                    symbol_table, interfaces = parser.parse()

                    self.ejb_symbol_table = symbol_table
                    self.ejb_interfaces = interfaces

                # Build RAG
                from utils.ejb_rag_builder import build_and_store_rag
                self.ejb_chroma_manager = build_and_store_rag(
                    project_input, self.ejb_symbol_table, self.ejb_interfaces
                )

                # Update UI
                interface_names = [iface.interface_name for iface in self.ejb_interfaces]
                self.root.after(0, lambda names=interface_names: self.ejb_interface_combo.configure(values=names))
                if interface_names:
                    self.root.after(0, lambda: self.ejb_interface_combo.current(0))

                self.root.after(0, lambda: self.ejb_status_var.set(
                    f"Status: Found {len(self.ejb_interfaces)} interfaces"))

                self.root.after(0, lambda: messagebox.showinfo(
                    "Analysis Complete", f"Found {len(self.ejb_interfaces)} EJB interfaces!"))

            except Exception as e:
                import traceback
                traceback.print_exc()
                self.root.after(0, lambda: self.ejb_status_var.set(f"Status: Error - {str(e)}"))
                self.root.after(0, lambda: messagebox.showerror("Error", f"Analysis failed: {str(e)}"))

        threading.Thread(target=task).start()

    def ejb_generate_docs(self):
        """Generate documentation for selected EJB interface."""
        interface_name = self.ejb_interface_combo_var.get()
        if not interface_name:
            messagebox.showerror("Error", "Please select an interface.")
            return

        if not self.ejb_chroma_manager:
            messagebox.showerror("Error", "Please analyze the project first.")
            return

        def task():
            self.root.after(0, lambda: self.ejb_doc_display.delete("1.0", tk.END))
            self.root.after(0, lambda: self.ejb_doc_display.insert(tk.END, "Generating documentation...\n\n"))

            try:
                # Get Super-Context from ChromaDB
                results = self.ejb_chroma_manager.query_by_interface_name(interface_name)

                if not results:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Error", f"Interface '{interface_name}' not found in database."))
                    return

                interface_context = results[0]['document']

                # Generate documentation (uses default model from config)
                from ai.ejb_llm import generate_ejb_template
                documentation = generate_ejb_template(interface_context, interface_name)

                # Update UI
                self.root.after(0, lambda: self._update_ejb_doc_display(documentation))

            except Exception as e:
                import traceback
                traceback.print_exc()
                self.root.after(0, lambda: messagebox.showerror("Error", f"Generation failed: {str(e)}"))

        threading.Thread(target=task).start()

    def _update_ejb_doc_display(self, documentation):
        """Update the EJB documentation display with generated content."""
        self.ejb_doc_display.delete("1.0", tk.END)
        self.ejb_doc_renderer.render_plain(documentation)
        self.ejb_doc_display.see("1.0")

    def ejb_view_interfaces(self):
        """Show a popup with all discovered EJB interfaces."""
        if not self.ejb_interfaces:
            messagebox.showinfo("Interface List", "No interfaces found. Please analyze a project first.")
            return

        # Create a popup window to show interfaces
        popup = tk.Toplevel(self.root)
        popup.title("EJB Interfaces")
        popup.geometry("600x400")
        popup.configure(bg=BG_COLOR)

        # Add a listbox with scrollbar
        container = ttk.Frame(popup)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(container)
        listbox = tk.Listbox(container, bg=INPUT_BG, fg="white", font=("Consolas", 10),
                            yscrollcommand=scrollbar.set)
        scrollbar.config(command=listbox.yview)

        scrollbar.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True)

        for iface in self.ejb_interfaces:
            info = f"{iface.interface_name} ({iface.interface_type}) - {len(iface.methods)} methods"
            listbox.insert(tk.END, info)

    def ejb_export_manifest(self):
        """Export EJB interfaces manifest to JSON file."""
        if not self.ejb_interfaces:
            messagebox.showinfo("Export", "No interfaces to export. Please analyze a project first.")
            return

        f = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
            title="Save JSON Manifest"
        )

        if f:
            try:
                from dataclasses import asdict

                manifest_data = {
                    "project_path": self.ejb_path_var.get(),
                    "total_interfaces": len(self.ejb_interfaces),
                    "interfaces": [asdict(iface) for iface in self.ejb_interfaces]
                }

                with open(f, 'w', encoding='utf-8') as file:
                    json.dump(manifest_data, file, indent=2, ensure_ascii=False)

                messagebox.showinfo("Export Complete", f"Manifest saved to {f}")

            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export manifest: {str(e)}")

    def ejb_export_to_word(self):
        """Export generated documentation to Word file."""
        documentation = self.ejb_doc_display.get("1.0", tk.END).strip()
        if not documentation or "Generating documentation" in documentation:
            messagebox.showerror("Error", "No documentation to export. Please generate documentation first.")
            return

        f = filedialog.asksaveasfilename(
            defaultextension=".docx",
            filetypes=[("Word Documents", "*.docx")],
            title="Save Documentation"
        )

        if f:
            try:
                from utils.doc_writer import save_to_docx
                save_to_docx(documentation, f)
                messagebox.showinfo("Export Complete", f"Documentation saved to {f}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export: {str(e)}")
