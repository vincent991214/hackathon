import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import re
import webbrowser

# --- Import Logic ---
# Ensure you have these files in your project structure
from utils.file_reader import read_codebase, read_template
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
        self.tab_docs = ttk.Frame(self.notebook)
        self.tab_chat = ttk.Frame(self.notebook)
        self.tab_refactor = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_setup, text="Project Setup")
        self.notebook.add(self.tab_docs, text="Documentation")
        self.notebook.add(self.tab_chat, text="AI Assistant")
        self.notebook.add(self.tab_refactor, text="Code Refactor")

        self._build_tab_setup()
        self._build_tab_docs()
        self._build_tab_chat()
        self._build_tab_refactor()

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

    # ================= TAB 2: DOCUMENTATION =================
    def _build_tab_docs(self):
        frame = ttk.Frame(self.tab_docs)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        paned = tk.PanedWindow(frame, orient=tk.HORIZONTAL, bg=BG_COLOR, sashwidth=4)
        paned.pack(fill="both", expand=True)

        left_panel = ttk.Frame(paned)
        paned.add(left_panel, width=350)

        ttk.Label(left_panel, text="Configuration", style="Header.TLabel").pack(anchor="w", pady=(0, 20))
        ttk.Label(left_panel, text="Template Source:", style="SubHeader.TLabel").pack(anchor="w", pady=(10, 5))
        self.template_var = tk.StringVar()
        tk.Entry(left_panel, textvariable=self.template_var, bg=INPUT_BG, fg="white", relief="flat").pack(fill="x",
                                                                                                          ipady=5)
        ttk.Button(left_panel, text="Choose File (Optional)", command=self.select_template).pack(anchor="w", pady=5)

        ttk.Label(left_panel, text="Specific Instructions:", style="SubHeader.TLabel").pack(anchor="w", pady=(20, 5))
        self.doc_instr = tk.Text(left_panel, height=8, bg=INPUT_BG, fg="white", relief="flat", font=("Segoe UI", 10))
        self.doc_instr.pack(fill="x", pady=5)

        ttk.Button(left_panel, text="GENERATE DOCUMENTATION", style="Green.TButton", command=self.run_doc_gen).pack(
            fill="x", pady=30, ipady=8)

        right_panel = ttk.Frame(paned)
        paned.add(right_panel)
        ttk.Label(right_panel, text="Activity Log", style="SubHeader.TLabel").pack(anchor="w", padx=20)

        # Manual Scrollbar for Logs
        log_container = ttk.Frame(right_panel)
        log_container.pack(fill="both", expand=True, padx=(20, 0), pady=10)

        log_scroll = ttk.Scrollbar(log_container)
        self.doc_log = tk.Text(log_container, bg=CHAT_BG, fg="#d4d4d4", font=("Consolas", 10),
                               relief="flat", yscrollcommand=log_scroll.set)
        log_scroll.config(command=self.doc_log.yview)

        log_scroll.pack(side="right", fill="y")
        self.doc_log.pack(side="left", fill="both", expand=True)

    def select_template(self):
        f = filedialog.askopenfilename(filetypes=[("Docs", "*.docx *.pdf")])
        if f: self.template_var.set(f)

    def run_doc_gen(self):
        if not self.loaded_code:
            messagebox.showerror("Error", "No project loaded.")
            return

        def task():
            self.doc_log.insert(tk.END, "[INFO] Reading template...\n")
            template_path = self.template_var.get()
            template_content = read_template(template_path) if template_path else None
            self.doc_log.insert(tk.END, "[INFO] Sending to AI Engine...\n")
            response = ai.generate_docs(self.loaded_code, template_content, self.doc_instr.get("1.0", tk.END))
            self.doc_log.insert(tk.END, "[INFO] Formatting Word Document...\n")
            save_to_docx(response, "Project_Docs.docx")
            self.doc_log.insert(tk.END, "[SUCCESS] Saved to 'Project_Docs.docx'\n")
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


if __name__ == "__main__":
    root = tk.Tk()
    app = DocGeneratorApp(root)
    root.mainloop()