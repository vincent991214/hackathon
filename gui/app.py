import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import re
import webbrowser
from datetime import datetime

# --- Import Logic ---
# Ensure you have these files in your project structure
from utils.file_reader import read_codebase, read_dox_pdf
from utils.doc_writer import save_to_docx
import ai.client as ai

# --- THEME CONSTANTS ---
BG_COLOR = "#1e1e1e"
SIDEBAR_COLOR = "#252526"
FG_COLOR = "#d4d4d4"
ACCENT_COLOR = "#007acc"
ACCENT_HOVER = "#005f9e"
INPUT_BG = "#3c3c3c"
CHAT_BG = "#2d2d30"

# Chat Specific Colors
USER_BUBBLE_BG = "#0e639c"
AI_BUBBLE_BG = "#3e3e42"
AI_TEXT_COLOR = "#ffffff"
USER_TEXT_COLOR = "#ffffff"

# Code Block Colors
CODE_BG = "#1e1e1e"
CODE_FG = "#d4d4d4"
KW_COLOR = "#569cd6"
STR_COLOR = "#ce9178"
COM_COLOR = "#6a9955"
NUM_COLOR = "#b5cea8"


class RichTextRenderer:
    """
    Helper to render Markdown-like text with Code Blocks and Copy Buttons
    into a Tkinter Text widget.
    """

    def __init__(self, text_widget, root_window):
        self.text_widget = text_widget
        self.root = root_window
        self._setup_tags()

    def _setup_tags(self):
        self.text_widget.tag_config("bold", font=("Segoe UI", 11, "bold"))
        self.text_widget.tag_config("header", font=("Segoe UI", 14, "bold"), foreground="white", spacing3=10)
        self.text_widget.tag_config("filepath", foreground="#4da6ff", underline=1)
        self.text_widget.tag_bind("filepath", "<Enter>", lambda e: self.text_widget.config(cursor="hand2"))
        self.text_widget.tag_bind("filepath", "<Leave>", lambda e: self.text_widget.config(cursor=""))

        self.text_widget.tag_config("ai_bubble", background=AI_BUBBLE_BG, foreground=AI_TEXT_COLOR,
                                    lmargin1=20, lmargin2=20, rmargin=100, spacing1=10, spacing3=10)
        self.text_widget.tag_config("ai_avatar", foreground="#cccccc", font=("Segoe UI", 9, "bold"), lmargin1=20)

        self.text_widget.tag_config("user_bubble", background=USER_BUBBLE_BG, foreground=USER_TEXT_COLOR,
                                    lmargin1=200, lmargin2=200, rmargin=20, spacing1=10, spacing3=10, justify='right')
        self.text_widget.tag_config("user_avatar", foreground="#cccccc", font=("Segoe UI", 9, "bold"), justify='right',
                                    rmargin=20)

        self.text_widget.tag_config("code_block", background=CODE_BG, font=("Consolas", 10), lmargin1=40, lmargin2=40,
                                    rmargin=120)
        self.text_widget.tag_config("token_keyword", foreground=KW_COLOR)
        self.text_widget.tag_config("token_string", foreground=STR_COLOR)
        self.text_widget.tag_config("token_comment", foreground=COM_COLOR)
        self.text_widget.tag_config("token_number", foreground=NUM_COLOR)

    def render_ai_message(self, content):
        self.text_widget.insert(tk.END, "\nAI ASSISTANT\n", "ai_avatar")
        self._parse_and_render(content, "ai_bubble", is_chat=True)
        self.text_widget.insert(tk.END, "\n")

    def render_user_message(self, content):
        self.text_widget.insert(tk.END, "\nYOU\n", "user_avatar")
        self.text_widget.insert(tk.END, f" {content} \n", "user_bubble")
        self.text_widget.insert(tk.END, "\n")

    def render_plain(self, content):
        self._parse_and_render(content, None, is_chat=False)

    def _parse_and_render(self, content, bubble_tag, is_chat):
        parts = re.split(r'(```\w*\n.*?```)', content, flags=re.DOTALL)
        for part in parts:
            if part.startswith("```"):
                self._render_code_block(part, is_chat=is_chat)
            else:
                self._render_markdown_text(part, bubble_tag)

    def _render_markdown_text(self, text, bubble_tag):
        lines = text.split('\n')
        for line in lines:
            if not line.strip():
                self.text_widget.insert(tk.END, "\n", bubble_tag if bubble_tag else None)
                continue

            if line.startswith("### "):
                header_tags = ("header", bubble_tag) if bubble_tag else ("header",)
                self.text_widget.insert(tk.END, "\n" + line.replace("### ", "") + "\n", header_tags)
                continue

            segments = re.split(r'(\*\*.*?\*\*)', line)
            for seg in segments:
                tags = [bubble_tag] if bubble_tag else []
                clean_text = seg

                if seg.startswith("**") and seg.endswith("**"):
                    tags.append("bold")
                    clean_text = seg[2:-2]

                self._insert_text_with_links(clean_text, tags)

            self.text_widget.insert(tk.END, "\n", bubble_tag if bubble_tag else None)

    def _insert_text_with_links(self, text, base_tags):
        path_pattern = r'([\w\-\.]+(?:/|\\)[\w\-\.]+\.\w+|[\w\-\.]+\.\w{2,4})'
        parts = re.split(path_pattern, text)

        for part in parts:
            valid_tags = tuple([t for t in base_tags if t])
            if re.match(path_pattern, part):
                tag_name = f"link_{part}"
                combined_tags = valid_tags + ("filepath", tag_name)
                self.text_widget.insert(tk.END, part, combined_tags)
                self.text_widget.tag_bind(tag_name, "<Button-1>", lambda e, p=part: webbrowser.open(os.getcwd()))
            else:
                self.text_widget.insert(tk.END, part, valid_tags)

    def _render_code_block(self, block_text, is_chat=True):
        lines = block_text.strip().split('\n')
        lang = lines[0].replace("```", "").strip()
        code_content = "\n".join(lines[1:-1])

        self.text_widget.insert(tk.END, "\n")

        # --- Button Container (FIXED HEIGHT) ---
        # We use pack_propagate(False) to ensure the frame stays exactly this size
        # This prevents the Text widget from getting confused about line heights
        btn_frame = tk.Frame(self.text_widget, bg=SIDEBAR_COLOR, height=28, width=500)
        btn_frame.pack_propagate(False)

        lbl = tk.Label(btn_frame, text=f" {lang.upper() if lang else 'CODE'} ", bg=SIDEBAR_COLOR, fg="#888",
                       font=("Segoe UI", 8, "bold"))
        lbl.pack(side="left", fill="y")

        copy_btn = tk.Button(btn_frame, text="📋 Copy Snippet", bg="#333", fg="white",
                             font=("Segoe UI", 8), borderwidth=0, cursor="hand2",
                             activebackground="#444", activeforeground="white",
                             command=lambda c=code_content: self._copy_to_clipboard(c))
        copy_btn.pack(side="right", padx=5, pady=2)

        # Insert the window
        self.text_widget.window_create(tk.END, window=btn_frame, stretch=1, padx=40 if is_chat else 0)
        self.text_widget.insert(tk.END, "\n")

        # --- Code Content ---
        start_index = self.text_widget.index(tk.END)
        self.text_widget.insert(tk.END, code_content, "code_block")
        self._highlight_syntax(start_index, code_content)
        self.text_widget.insert(tk.END, "\n\n")

    def _highlight_syntax(self, start_index, code):
        keywords = r"\b(def|class|import|from|return|if|else|elif|try|except|while|for|in|with|as|pass|print|self|const|let|var|function)\b"
        self._apply_regex_color(keywords, "token_keyword", start_index, code)

        strings = r"(['\"])(?:(?=(\\?))\2.)*?\1"
        self._apply_regex_color(strings, "token_string", start_index, code)

        comments = r"(#.*|//.*)"
        self._apply_regex_color(comments, "token_comment", start_index, code)

        numbers = r"\b\d+\b"
        self._apply_regex_color(numbers, "token_number", start_index, code)

    def _apply_regex_color(self, pattern, tag, start_index, code):
        for match in re.finditer(pattern, code):
            count = tk.IntVar()
            self.text_widget.mark_set("matchStart", start_index)
            self.text_widget.mark_set("matchEnd", start_index)
            while True:
                pos = self.text_widget.search(pattern, "matchEnd", stopindex=tk.END, count=count, regexp=True)
                if not pos: break
                self.text_widget.mark_set("matchStart", pos)
                self.text_widget.mark_set("matchEnd", f"{pos}+{count.get()}c")
                self.text_widget.tag_add(tag, "matchStart", "matchEnd")

    def _copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("Copied", "Code snippet copied to clipboard!")


class DocGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DevMate AI - Enterprise Edition")
        self.root.geometry("1100x800")
        self.root.configure(bg=BG_COLOR)

        self.loaded_code = ""
        self.project_path = ""
        self.chat_history = ""
        self.template_md = ""

        # EJB Analysis state
        self.ejb_interfaces = []
        self.ejb_selected_interface = None
        self.ejb_symbol_table = {}
        self.ejb_chroma_manager = None

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
        self.tab_ejb = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_setup, text="Project Setup")
        self.notebook.add(self.tab_template_editor, text="Template Editor")
        self.notebook.add(self.tab_chat, text="AI Assistant")
        self.notebook.add(self.tab_refactor, text="Code Refactor")
        self.notebook.add(self.tab_ejb, text="EJB Analysis")

        self._build_tab_setup()
        self._build_tab_template_editor()
        self._build_tab_chat()
        self._build_tab_refactor()
        self._build_tab_ejb()

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

        self.load_btn = ttk.Button(center_frame, text="INITIALIZE PROJECT", command=self.load_project,
                                   style="Green.TButton")
        self.load_btn.pack(pady=30, ipadx=30, ipady=8)

        self.status_lbl = ttk.Label(center_frame, text="Waiting for input...", foreground="#666")
        self.status_lbl.pack()

    def select_folder(self):
        f = filedialog.askdirectory()
        if f: self.path_var.set(f)

    def load_project(self):
        folder = self.path_var.get()
        if folder:
            self.status_lbl.config(text="Scanning...", foreground=ACCENT_COLOR)
            self.root.update()
            try:
                self.loaded_code = read_codebase(folder)
                self.project_path = folder
                self.status_lbl.config(text=f"Ready. {len(self.loaded_code)} chars indexed.", foreground="#2da44e")
                messagebox.showinfo("Success", "Project Loaded!")
            except Exception as e:
                self.status_lbl.config(text=f"Error: {e}", foreground="red")

    # ================= TAB 2: TEMPLATE EDITOR =================
    def _build_tab_template_editor(self):
        frame = ttk.Frame(self.tab_template_editor)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        paned = tk.PanedWindow(frame, orient=tk.HORIZONTAL, bg=BG_COLOR, sashwidth=4)
        paned.pack(fill="both", expand=True)

        # Left Panel: Configuration
        left_panel = ttk.Frame(paned)
        paned.add(left_panel, width=350)

        # ttk.Label(left_panel, text="Configuration", style="Header.TLabel").pack(anchor="w", pady=(0, 20))
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

    # ================= TASK 3: Upload Template to Editor =================
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

    # ================= TASK 4: Helper Methods for File Naming =================
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
        project_name = re.sub(r'[^\w\-]', '_', project_name)
        return f"./template/Template_{project_name}_{timestamp}.docx"

    def _get_final_docx_filename(self):
        """Generate final docx filename with project name and timestamp."""
        project_name = self._extract_project_name()
        timestamp = self._get_timestamp()
        # Clean project name for filename
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
            # TASK 4: Ensure directories exist and generate filenames
            self._ensure_directories()
            template_filename = self._get_template_filename()
            final_docx_filename = self._get_final_docx_filename()

            # Save the edited template with new naming convention
            self.doc_log.insert(tk.END, f"[INFO] Saving edited template to '{template_filename}'...\n")
            save_to_docx(edited_template, template_filename)
            self.doc_log.insert(tk.END, f"[SUCCESS] Edited template saved to '{template_filename}'\n")

            # Generate final documentation from edited template
            self.doc_log.insert(tk.END, "[INFO] Generating final documentation from edited template...\n")
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

    # ================= TAB 4: REFACTOR (MANUAL SCROLLBAR FIX) =================
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

    # ================= TAB 5: EJB ANALYSIS =================
    def _build_tab_ejb(self):
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

        self.ejb_path_var = tk.StringVar()
        entry = tk.Entry(upload_frame, textvariable=self.ejb_path_var, width=30,
                        font=("Segoe UI", 10), bg=INPUT_BG, fg="white", relief="flat")
        entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 5))

        ttk.Button(upload_frame, text="Browse", command=self.ejb_select_folder).pack(side="left")

        ttk.Button(left_panel, text="Upload ZIP", command=self.ejb_upload_zip).pack(fill="x", pady=5)

        ttk.Button(left_panel, text="ANALYZE EJB PROJECT", style="Green.TButton",
                  command=self.ejb_analyze_project).pack(fill="x", pady=15, ipady=8)

        self.ejb_status_var = tk.StringVar(value="Status: Waiting for project")
        ttk.Label(left_panel, textvariable=self.ejb_status_var, foreground="#888").pack(anchor="w", pady=(5, 15))

        # Interface Selection Section
        ttk.Label(left_panel, text="Select Interface", style="SubHeader.TLabel").pack(anchor="w", pady=(10, 5))

        self.ejb_interface_combo_var = tk.StringVar()
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
        f = filedialog.askdirectory()
        if f:
            self.ejb_path_var.set(f)

    def ejb_upload_zip(self):
        f = filedialog.askopenfilename(
            title="Select EJB Project ZIP",
            filetypes=[("ZIP Files", "*.zip")]
        )
        if f:
            self.ejb_path_var.set(f)

    def ejb_analyze_project(self):
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
                from ai.client import generate_ejb_template
                documentation = generate_ejb_template(interface_context, interface_name)

                # Update UI
                self.root.after(0, lambda: self._update_ejb_doc_display(documentation))

            except Exception as e:
                import traceback
                traceback.print_exc()
                self.root.after(0, lambda: messagebox.showerror("Error", f"Generation failed: {str(e)}"))

        threading.Thread(target=task).start()

    def _update_ejb_doc_display(self, documentation):
        self.ejb_doc_display.delete("1.0", tk.END)
        self.ejb_doc_renderer.render_plain(documentation)
        self.ejb_doc_display.see("1.0")

    def ejb_view_interfaces(self):
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
                import json
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


if __name__ == "__main__":
    root = tk.Tk()
    app = DocGeneratorApp(root)
    root.mainloop()