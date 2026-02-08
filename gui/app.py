import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
from datetime import datetime

# --- Import Logic ---
# Ensure you have these files in your project structure
from utils.file_reader import read_codebase, read_dox_pdf
from utils.doc_writer import save_to_docx
import ai.doc_gen_llm as ai

# Import tools for project analysis
from tools import get_parser, ProjectDetector, ToolConfig, ProjectAnalysis

# --- Import Shared GUI Components ---
from gui.common import (
    BG_COLOR, FG_COLOR, ACCENT_COLOR, ACCENT_HOVER, INPUT_BG, CHAT_BG,
    SIDEBAR_COLOR, RichTextRenderer
)

# # --- Import EJB Tab Mixin ---
# from gui.ejb_app import EJBTabMixin


class DocGeneratorApp():#EJBTabMixin):
    def __init__(self, root):
        self.root = root
        self.root.title("DevMate AI - Enterprise Edition")
        self.root.geometry("1100x800")
        self.root.configure(bg=BG_COLOR)

        self.loaded_code = ""
        self.project_path = ""
        self.chat_history = ""
        self.template_md = ""
        self.project_analysis = None  # New: ProjectAnalysis from parser

        # Initialize EJB state (from mixin)
        # self._init_ejb_state()

        self._setup_styles()
        self._build_ui()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background=BG_COLOR)
        style.configure("TLabel", background=BG_COLOR, foreground=FG_COLOR, font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="white")
        style.configure("SubHeader.TLabel", font=("Segoe UI", 11, "bold"), foreground="#cccccc")
        style.configure("TNotebook", background=BG_COLOR, borderwidth=0)
        style.configure("TNotebook.Tab", background=SIDEBAR_COLOR, foreground=FG_COLOR, padding=[20, 10])
        style.map("TNotebook.Tab", background=[("selected", BG_COLOR)], foreground=[("selected", ACCENT_COLOR)])
        style.configure("TButton", background=ACCENT_COLOR, foreground="white", borderwidth=0,
                        font=("Segoe UI", 10, "bold"))
        style.map("TButton", background=[("active", ACCENT_HOVER)])
        style.configure("Green.TButton", background="#2da44e", foreground="white")
        style.map("Green.TButton", background=[("active", "#2c974b")])

    def _build_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        self.tab_setup = ttk.Frame(self.notebook)
        self.tab_template_editor = ttk.Frame(self.notebook)
        self.tab_chat = ttk.Frame(self.notebook)
        self.tab_refactor = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_setup, text="Project Setup")
        self.notebook.add(self.tab_template_editor, text="Template Editor")
        self.notebook.add(self.tab_chat, text="AI Assistant")
        self.notebook.add(self.tab_refactor, text="Code Refactor")
        # self.notebook.add(self.tab_ejb, text="EJB Analysis")

        self._build_tab_setup()
        self._build_tab_template_editor()
        self._build_tab_chat()
        self._build_tab_refactor()
        # self._build_tab_ejb()  # Built from mixin

    # ================= TAB 1: SETUP =================
    def _build_tab_setup(self):
        frame = ttk.Frame(self.tab_setup)
        frame.pack(fill="both", expand=True, padx=50, pady=50)

        center_frame = ttk.Frame(frame)
        center_frame.pack(fill="x", pady=20)

        ttk.Label(center_frame, text="Welcome to DevMate", style="Header.TLabel").pack(anchor="center", pady=(0, 10))
        ttk.Label(center_frame, text="Load your codebase to begin analysis.", foreground="#888").pack(anchor="center",
                                                                                                      pady=(0, 30))

        sel_frame = ttk.Frame(center_frame)
        sel_frame.pack(fill="x", padx=100)

        self.path_var = tk.StringVar()
        entry = tk.Entry(sel_frame, textvariable=self.path_var, width=50, font=("Segoe UI", 11), bg=INPUT_BG,
                         fg="white", insertbackground="white", relief="flat")
        entry.pack(side="left", fill="x", expand=True, ipady=10, padx=(0, 10))
        ttk.Button(sel_frame, text="Browse...", command=self.select_folder).pack(side="right")

        # Add project type detection indicator
        self.project_type_var = tk.StringVar(value="")
        self.project_type_label = ttk.Label(
            sel_frame,
            textvariable=self.project_type_var,
            foreground=FG_COLOR,
            background=BG_COLOR
        )
        self.project_type_label.pack(anchor="center", pady=(10, 0))

        self.load_btn = ttk.Button(center_frame, text="INITIALIZE PROJECT", command=self.load_project,
                                   style="Green.TButton")
        self.load_btn.pack(pady=30, ipadx=30, ipady=8)

        self.status_lbl = ttk.Label(center_frame, text="Waiting for input...", foreground="#666")
        self.status_lbl.pack()

    def select_folder(self):
        f = filedialog.askdirectory()
        if f:
            self.path_var.set(f)
            # Trigger project type detection
            self._detect_and_update_project_type()

    def _detect_and_update_project_type(self):
        """Detect project type and update UI accordingly."""
        folder_path = self.path_var.get()

        if not folder_path:
            return

        # Run detection in background to avoid UI freeze
        def detect_task():
            try:
                detector = ProjectDetector(ToolConfig())
                result = detector.run(project_path=folder_path)

                # Update UI from main thread
                if result.success:
                    project_info = result.data
                    self.root.after(0, lambda: self._update_project_type_ui(project_info))
                else:
                    self.root.after(0, lambda: self._show_detection_error(result.error))
            except Exception as e:
                self.root.after(0, lambda: self._show_detection_error(str(e)))

        threading.Thread(target=detect_task, daemon=True).start()

    def _update_project_type_ui(self, project_info):
        """Update UI based on detected project type."""
        # Update project type label
        if project_info.is_java_project:
            type_text = f"Detected: Java Project ({project_info.build_tool})"

            if project_info.frameworks:
                frameworks_str = ", ".join(project_info.frameworks)
                type_text += f"\nFrameworks: {frameworks_str}"

            if project_info.java_version:
                type_text += f"\nJava Version: {project_info.java_version}"

            self.project_type_var.set(type_text)

        elif project_info.is_python_project:
            type_text = f"Detected: Python Project ({project_info.build_tool})"
            if project_info.frameworks:
                frameworks_str = ", ".join(project_info.frameworks)
                type_text += f"\nFrameworks: {frameworks_str}"
            self.project_type_var.set(type_text)

        elif project_info.is_js_project:
            type_text = f"Detected: JavaScript/TypeScript Project ({project_info.build_tool})"
            if project_info.frameworks:
                frameworks_str = ", ".join(project_info.frameworks)
                type_text += f"\nFrameworks: {frameworks_str}"
            self.project_type_var.set(type_text)

        else:
            self.project_type_var.set(f"Detected: General Project")

    def _show_detection_error(self, error):
        """Show detection error"""
        self.project_type_var.set(f"Detection Error: {error}")

    def load_project(self):
        folder = self.path_var.get()
        if folder:
            self.status_lbl.config(text="Scanning...", foreground=ACCENT_COLOR)
            self.root.update()

            def load_task():
                try:
                    # Detect project type
                    detector = ProjectDetector(ToolConfig())
                    detection_result = detector.run(project_path=folder)

                    if not detection_result.success:
                        raise Exception(detection_result.error)

                    project_info = detection_result.data

                    # Get appropriate parser
                    parser = get_parser(
                        project_info=project_info,
                        enable_deep=False  # Deep parse not yet implemented
                    )

                    # Parse project
                    analysis: ProjectAnalysis = parser.parse_project(folder)

                    # Store for later use
                    self.project_info = project_info
                    self.project_analysis = analysis

                    # Convert to string for backward compatibility
                    file_count = len(analysis.files)

                    # Show detected docs status
                    doc_status = ""
                    if analysis.has_readme or analysis.has_claude_md:
                        found_docs = []
                        if analysis.has_readme:
                            found_docs.append("README.md")
                        if analysis.has_claude_md:
                            found_docs.append("CLAUDE.md")
                        doc_status = f" | Docs found: {', '.join(found_docs)}"

                    # Update UI from main thread
                    self.root.after(0, lambda: self._on_project_loaded(file_count, doc_status))

                except Exception as e:
                    self.root.after(0, lambda: self._on_project_error(str(e)))

            threading.Thread(target=load_task, daemon=True).start()

    def _on_project_loaded(self, file_count, doc_status=""):
        """Handle successful project load"""
        self.loaded_code = str(self.project_analysis)  # For backward compatibility
        self.project_path = self.path_var.get()
        self.status_lbl.config(
            text=f"Ready. {file_count} files indexed.{doc_status}",
            foreground="#2da44e"
        )
        messagebox.showinfo("Success", "Project Loaded!")

    def _on_project_error(self, error: str):
        """Handle project load error"""
        self.status_lbl.config(text=f"Error: {error}", foreground="red")
        messagebox.showerror("Error", f"Failed to load project:\n{error}")

    # ================= TAB 2: TEMPLATE EDITOR =================
    def _build_tab_template_editor(self):
        frame = ttk.Frame(self.tab_template_editor)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        paned = tk.PanedWindow(frame, orient=tk.HORIZONTAL, bg=BG_COLOR, sashwidth=4)
        paned.pack(fill="both", expand=True)

        # Left Panel: Configuration
        left_panel = ttk.Frame(paned)
        paned.add(left_panel, width=350)

        ttk.Label(left_panel, text="Extract the template from:", style="SubHeader.TLabel").pack(anchor="w", pady=(10, 5))
        self.template_var = tk.StringVar()
        tk.Entry(left_panel, textvariable=self.template_var, bg=INPUT_BG, fg="white", relief="flat").pack(fill="x", ipady=5)
        ttk.Button(left_panel, text="Example Document", command=self.select_template).pack(anchor="w", pady=5)

        ttk.Label(left_panel, text="OR", style="SubHeader.TLabel").pack(anchor="w", pady=(10, 5))
        ttk.Button(left_panel, text="Upload Template (.docx)", command=self.upload_template_to_editor).pack(anchor="w", pady=5)

        ttk.Label(left_panel, text="Specific Instructions:", style="SubHeader.TLabel").pack(anchor="w", pady=(20, 5))
        self.doc_instr = tk.Text(left_panel, height=8, bg=INPUT_BG, fg="white", relief="flat", font=("Segoe UI", 10))
        self.doc_instr.pack(fill="x", pady=5)

        ttk.Button(left_panel, text="GENERATE TEMPLATE", style="Green.TButton",
                   command=self.generate_template_handler).pack(fill="x", pady=20, ipady=8)

        # State indicator
        self.template_status_var = tk.StringVar(value="Status: No template generated")
        ttk.Label(left_panel, textvariable=self.template_status_var, foreground="#888").pack(anchor="w", pady=(10, 5))

        self.confirm_btn = ttk.Button(left_panel, text="CONFIRM & GENERATE DOCS",
                                      command=self.confirm_and_generate_docs, state="disabled")
        self.confirm_btn.pack(fill="x", pady=(10, 30), ipady=8)

        # Right Panel: Template Editor
        right_panel = ttk.Frame(paned)
        paned.add(right_panel)
        ttk.Label(right_panel, text="Template Editor", style="SubHeader.TLabel").pack(anchor="w", padx=20)

        editor_container = ttk.Frame(right_panel)
        editor_container.pack(fill="both", expand=True, padx=(20, 0), pady=10)

        editor_scroll = ttk.Scrollbar(editor_container)
        self.template_editor = tk.Text(editor_container, bg=INPUT_BG, fg="white", font=("Consolas", 11),
                                       relief="flat", yscrollcommand=editor_scroll.set, wrap="word")
        editor_scroll.config(command=self.template_editor.yview)

        editor_scroll.pack(side="right", fill="y")
        self.template_editor.pack(side="left", fill="both", expand=True)

        # Activity Log at bottom
        ttk.Label(right_panel, text="Activity Log", style="SubHeader.TLabel").pack(anchor="w", padx=20, pady=(10, 0))
        log_container = ttk.Frame(right_panel)
        log_container.pack(fill="both", expand=False, padx=(20, 0), pady=10)

        log_scroll = ttk.Scrollbar(log_container)
        self.doc_log = tk.Text(log_container, bg=CHAT_BG, fg="#d4d4d4", font=("Consolas", 10),
                               relief="flat", yscrollcommand=log_scroll.set, height=6)
        log_scroll.config(command=self.doc_log.yview)

        log_scroll.pack(side="right", fill="y")
        self.doc_log.pack(side="left", fill="both", expand=True)

    def select_template(self):
        f = filedialog.askopenfilename(filetypes=[("Docs", "*.docx *.pdf")])
        if f: self.template_var.set(f)

    def upload_template_to_editor(self):
        """Upload a .docx template file directly to the editor, bypassing AI generation."""
        f = filedialog.askopenfilename(
            title="Select Template File",
            filetypes=[("Word Documents", "*.docx")]
        )
        if not f:
            return

        try:
            # Read the uploaded file content
            content = read_dox_pdf(f)
            if content is None:
                messagebox.showerror("Error", "Failed to read the template file.")
                return

            # Display content in the editor
            self.template_editor.delete("1.0", tk.END)
            self.template_editor.insert(tk.END, content)
            self.template_md = content

            # Update status and enable confirm button
            filename = os.path.basename(f)
            self.template_status_var.set(f"Status: Template loaded from {filename}")
            self.confirm_btn.config(state="normal")

            self.doc_log.insert(tk.END, f"[INFO] Template loaded from {filename}\n")
            self.doc_log.see(tk.END)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to upload template: {e}")

    def _extract_project_name(self):
        """Extract project name from the project path."""
        if not self.project_path:
            return "unnamed_project"
        # Get the last folder name from the path
        return os.path.basename(os.path.normpath(self.project_path))

    def _get_timestamp(self):
        """Generate timestamp in YYYYMMDDHHMMSS format."""
        return datetime.now().strftime("%Y%m%d%H%M%S")

    def _ensure_directories(self):
        """Create output directories if they don't exist."""
        os.makedirs("./template", exist_ok=True)
        os.makedirs("./final_docx", exist_ok=True)

    def _get_template_filename(self):
        """Generate template filename with project name and timestamp."""
        project_name = self._extract_project_name()
        timestamp = self._get_timestamp()
        # Clean project name for filename
        import re
        project_name = re.sub(r'[^\w\-]', '_', project_name)
        return f"./template/Template_{project_name}_{timestamp}.docx"

    def _get_final_docx_filename(self):
        """Generate final docx filename with project name and timestamp."""
        project_name = self._extract_project_name()
        timestamp = self._get_timestamp()
        # Clean project name for filename
        import re
        project_name = re.sub(r'[^\w\-]', '_', project_name)
        return f"./final_docx/{project_name}_{timestamp}.docx"

    def generate_template_handler(self):
        if not self.loaded_code:
            messagebox.showerror("Error", "No project loaded.")
            return

        def task():
            self.doc_log.insert(tk.END, "[INFO] Reading template...\n")
            example_path = self.template_var.get()
            example_content = read_dox_pdf(example_path) if example_path else None
            self.doc_log.insert(tk.END, "[INFO] Sending to AI Engine...\n")

            template_md = ai.generate_template(example_content, self.doc_instr.get("1.0", tk.END))

            # Update UI with generated template
            self.root.after(0, lambda: self._update_template_editor(template_md))

        threading.Thread(target=task).start()

    def _update_template_editor(self, template_md):
        self.template_md = template_md
        self.template_editor.delete("1.0", tk.END)
        self.template_editor.insert(tk.END, template_md)
        self.template_status_var.set("Status: Template ready for editing")
        self.confirm_btn.config(state="normal")
        self.doc_log.see(tk.END)

    def confirm_and_generate_docs(self):
        if not self.loaded_code:
            messagebox.showerror("Error", "No project loaded.")
            return

        # Get the edited template from the editor
        edited_template = self.template_editor.get("1.0", tk.END)

        def task():
            # Ensure directories exist and generate filenames
            self._ensure_directories()
            template_filename = self._get_template_filename()
            final_docx_filename = self._get_final_docx_filename()

            # Save the edited template with new naming convention
            self.doc_log.insert(tk.END, f"[INFO] Saving edited template to '{template_filename}'...\n")
            save_to_docx(edited_template, template_filename)
            self.doc_log.insert(tk.END, f"[SUCCESS] Edited template saved to '{template_filename}'\n")

            # Generate final documentation from edited template
            self.doc_log.insert(tk.END, "[INFO] Generating final documentation from edited template...\n")

            # Use project_analysis if available (new mode), otherwise use loaded_code (legacy mode)
            if hasattr(self, 'project_analysis'):
                final_doc_md = ai.generate_docs(edited_template, self.project_analysis, self.doc_instr.get("1.0", tk.END))
            else:
                final_doc_md = ai.generate_docs(edited_template, self.loaded_code, self.doc_instr.get("1.0", tk.END))

            self.doc_log.insert(tk.END, "[INFO] Formatting Word Document...\n")
            save_to_docx(final_doc_md, final_docx_filename)
            self.doc_log.insert(tk.END, f"[SUCCESS] Saved to '{final_docx_filename}'\n")
            self.doc_log.see(tk.END)

        threading.Thread(target=task).start()

    # ================= TAB 3: CHAT =================
    def _build_tab_chat(self):
        frame = ttk.Frame(self.tab_chat)
        frame.pack(fill="both", expand=True)

        chat_container = ttk.Frame(frame)
        chat_container.pack(fill="both", expand=True, pady=(0, 2))

        # Manual Scrollbar for Chat
        chat_scroll = ttk.Scrollbar(chat_container)
        self.chat_display = tk.Text(chat_container, bg=CHAT_BG, fg="white", font=("Segoe UI", 11),
                                    state='disabled', relief="flat", padx=20, pady=20, wrap="word",
                                    yscrollcommand=chat_scroll.set)
        chat_scroll.config(command=self.chat_display.yview)

        chat_scroll.pack(side="right", fill="y")
        self.chat_display.pack(side="left", fill="both", expand=True)

        self.chat_renderer = RichTextRenderer(self.chat_display, self.root)

        input_wrapper = tk.Frame(frame, bg=BG_COLOR, pady=15, padx=20)
        input_wrapper.pack(fill="x")
        input_container = tk.Frame(input_wrapper, bg=INPUT_BG, bd=0)
        input_container.pack(fill="x", ipady=5)
        self.chat_input = tk.Entry(input_container, bg=INPUT_BG, fg="white", font=("Segoe UI", 12), relief="flat",
                                   insertbackground="white")
        self.chat_input.pack(side="left", fill="x", expand=True, padx=15)
        self.chat_input.bind("<Return>", self.send_chat)
        send_btn = tk.Button(input_container, text="➤", command=self.send_chat, bg=INPUT_BG, fg=ACCENT_COLOR,
                             font=("Segoe UI", 16), bd=0, activebackground=INPUT_BG, activeforeground="white",
                             cursor="hand2")
        send_btn.pack(side="right", padx=10)

    def send_chat(self, event=None):
        if not self.loaded_code:
            messagebox.showerror("Error", "Load project first.")
            return
        question = self.chat_input.get()
        if not question: return
        self.chat_input.delete(0, tk.END)

        self.chat_display.config(state='normal')
        self.chat_renderer.render_user_message(question)
        self.chat_display.see(tk.END)
        self.chat_display.config(state='disabled')

        def task():
            response = ai.chat_with_code(self.loaded_code, question, self.chat_history)
            self.chat_history += f"\nUser: {question}\nAI: {response}"
            self.root.after(0, lambda: self._append_ai_response(response))

        threading.Thread(target=task).start()

    def _append_ai_response(self, text):
        self.chat_display.config(state='normal')
        self.chat_renderer.render_ai_message(text)
        self.chat_display.see(tk.END)
        self.chat_display.config(state='disabled')

    # ================= TAB 4: REFACTOR =================
    def _build_tab_refactor(self):
        frame = ttk.Frame(self.tab_refactor)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        top_bar = ttk.Frame(frame)
        top_bar.pack(fill="x", pady=(0, 10))
        ttk.Label(top_bar, text="Code Analysis", style="Header.TLabel").pack(side="left")
        ttk.Button(top_bar, text="RUN ANALYSIS", style="Green.TButton", command=self.run_refactor).pack(side="right")

        # Container for Text + Scrollbar
        text_container = ttk.Frame(frame)
        text_container.pack(fill="both", expand=True)

        # 1. Create Scrollbar
        scrollbar = ttk.Scrollbar(text_container, orient="vertical")

        # 2. Create Text Widget linked to scrollbar
        self.refactor_display = tk.Text(text_container, bg=BG_COLOR, fg="#dcdcdc",
                                        font=("Segoe UI", 11), relief="flat", wrap="word",
                                        yscrollcommand=scrollbar.set)

        # 3. Link Scrollbar back to Text
        scrollbar.config(command=self.refactor_display.yview)

        # 4. Pack them (Scrollbar Right, Text Left)
        scrollbar.pack(side="right", fill="y")
        self.refactor_display.pack(side="left", fill="both", expand=True)

        self.refactor_renderer = RichTextRenderer(self.refactor_display, self.root)

    def run_refactor(self):
        if not self.loaded_code:
            messagebox.showerror("Error", "Load project first.")
            return

        self.refactor_display.delete("1.0", tk.END)
        self.refactor_display.insert(tk.END, "Analyzing codebase... please wait...\n")

        def task():
            response = ai.suggest_refactor(self.loaded_code)
            self.root.after(0, lambda: self._update_refactor_ui(response))

        threading.Thread(target=task).start()

    def _update_refactor_ui(self, text):
        self.refactor_display.delete("1.0", tk.END)
        self.refactor_renderer.render_plain(text)
        # Force scroll to bottom then top to trigger geometry recalc
        self.refactor_display.see(tk.END)
        self.refactor_display.see("1.0")


if __name__ == "__main__":
    root = tk.Tk()
    app = DocGeneratorApp(root)
    root.mainloop()
