import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk, font
import threading
import os
import re
import webbrowser

# Import logic
from utils.file_reader import read_codebase, read_template
from utils.doc_writer import save_to_docx
import ai.client as ai

# --- COMMERCIAL THEME CONSTANTS ---
BG_COLOR = "#1e1e1e"  # Main Window Background
SIDEBAR_COLOR = "#252526"  # Tab Bar
FG_COLOR = "#d4d4d4"  # Standard Text
ACCENT_COLOR = "#007acc"  # Brand Blue
ACCENT_HOVER = "#005f9e"
INPUT_BG = "#3c3c3c"  # Input fields
CHAT_BG = "#2d2d30"  # Chat area background

# Chat Bubble Colors
USER_BUBBLE_BG = "#0e639c"  # Blue
AI_BUBBLE_BG = "#3c3c3c"  # Dark Gray
TIMESTAMP_COLOR = "#858585"


class DocGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DevMate AI - Enterprise Edition")
        self.root.geometry("1000x750")
        self.root.configure(bg=BG_COLOR)

        # Application State
        self.loaded_code = ""
        self.project_path = ""
        self.chat_history = ""

        self._setup_styles()
        self._build_ui()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        # General
        style.configure("TFrame", background=BG_COLOR)
        style.configure("TLabel", background=BG_COLOR, foreground=FG_COLOR, font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="white")
        style.configure("SubHeader.TLabel", font=("Segoe UI", 11, "bold"), foreground="#cccccc")

        # Tabs (Modern Flat Look)
        style.configure("TNotebook", background=BG_COLOR, borderwidth=0)
        style.configure("TNotebook.Tab", background=SIDEBAR_COLOR, foreground=FG_COLOR, padding=[20, 10],
                        font=("Segoe UI", 10))
        style.map("TNotebook.Tab", background=[("selected", BG_COLOR)], foreground=[("selected", ACCENT_COLOR)])

        # Buttons (Rounded/Flat)
        style.configure("TButton", background=ACCENT_COLOR, foreground="white", borderwidth=0,
                        font=("Segoe UI", 10, "bold"))
        style.map("TButton", background=[("active", ACCENT_HOVER)])

        # Success Button
        style.configure("Green.TButton", background="#2da44e", foreground="white")  # GitHub Green
        style.map("Green.TButton", background=[("active", "#2c974b")])

    def _build_ui(self):
        # Notebook (Tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=0, pady=0)

        # Tab Frames
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

        # Center Container
        center_frame = ttk.Frame(frame)
        center_frame.pack(fill="x", pady=20)

        ttk.Label(center_frame, text="Welcome to DevMate", style="Header.TLabel").pack(anchor="center", pady=(0, 10))
        ttk.Label(center_frame, text="Load your codebase to begin analysis.", foreground="#888").pack(anchor="center",
                                                                                                      pady=(0, 30))

        # Folder Selection
        sel_frame = ttk.Frame(center_frame)
        sel_frame.pack(fill="x", padx=100)

        self.path_var = tk.StringVar()
        entry = tk.Entry(sel_frame, textvariable=self.path_var, bg=INPUT_BG, fg="white", insertbackground="white",
                         relief="flat", font=("Segoe UI", 11))
        entry.pack(side="left", fill="x", expand=True, ipady=10, padx=(0, 10))

        ttk.Button(sel_frame, text="Browse...", command=self.select_folder).pack(side="right")

        # Load Button
        self.load_btn = ttk.Button(center_frame, text="INITIALIZE PROJECT", command=self.load_project,
                                   style="Green.TButton")
        self.load_btn.pack(pady=30, ipadx=30, ipady=8)

        # Status
        self.status_lbl = ttk.Label(center_frame, text="Waiting for input...", foreground="#666")
        self.status_lbl.pack()

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder: self.path_var.set(folder)

    def load_project(self):
        folder = self.path_var.get()
        if not folder: return

        self.status_lbl.config(text="Scanning project files...", foreground=ACCENT_COLOR)
        self.root.update()

        try:
            self.loaded_code = read_codebase(folder)
            self.project_path = folder
            count = len(self.loaded_code)
            self.status_lbl.config(text=f"Ready. {count} characters indexed.", foreground="#2da44e")
            messagebox.showinfo("Success", "Project indexed successfully.")
        except Exception as e:
            self.status_lbl.config(text=f"Error: {str(e)}", foreground="red")

    # ================= TAB 2: DOCS =================
    def _build_tab_docs(self):
        frame = ttk.Frame(self.tab_docs)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Split Pane
        paned = tk.PanedWindow(frame, orient=tk.HORIZONTAL, bg=BG_COLOR, sashwidth=4)
        paned.pack(fill="both", expand=True)

        # Left: Config
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

        # Right: Log
        right_panel = ttk.Frame(paned)
        paned.add(right_panel)

        ttk.Label(right_panel, text="Activity Log", style="SubHeader.TLabel").pack(anchor="w", padx=20)
        self.doc_log = scrolledtext.ScrolledText(right_panel, bg=CHAT_BG, fg="#d4d4d4", font=("Consolas", 10),
                                                 relief="flat")
        self.doc_log.pack(fill="both", expand=True, padx=(20, 0), pady=10)

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

    # ================= TAB 3: CHAT (MODERN BUBBLES) =================
    def _build_tab_chat(self):
        frame = ttk.Frame(self.tab_chat)
        frame.pack(fill="both", expand=True)

        # Chat Area (Using Text widget with tags for formatting)
        self.chat_display = scrolledtext.ScrolledText(frame, bg=CHAT_BG, fg="white", font=("Segoe UI", 11),
                                                      state='disabled', relief="flat", padx=20, pady=20)
        self.chat_display.pack(fill="both", expand=True, pady=(0, 2))

        # Tag Configurations for Bubbles
        self.chat_display.tag_config("user", justify='right', background=USER_BUBBLE_BG, foreground="white",
                                     lmargin1=100, lmargin2=100, rmargin=10, spacing1=10, spacing3=10)
        self.chat_display.tag_config("ai", justify='left', background=AI_BUBBLE_BG, foreground="white", lmargin1=10,
                                     lmargin2=10, rmargin=100, spacing1=10, spacing3=10)
        self.chat_display.tag_config("filepath", foreground="#4da6ff", underline=1)
        self.chat_display.tag_bind("filepath", "<Button-1>", self.on_file_click)

        # Input Area
        input_container = ttk.Frame(frame)
        input_container.pack(fill="x", padx=20, pady=20)

        self.chat_input = tk.Entry(input_container, bg=INPUT_BG, fg="white", font=("Segoe UI", 12), relief="flat",
                                   insertbackground="white")
        self.chat_input.pack(side="left", fill="x", expand=True, ipady=10, padx=(0, 10))
        self.chat_input.bind("<Return>", self.send_chat)

        ttk.Button(input_container, text="SEND", command=self.send_chat).pack(side="right", ipady=2)

    def send_chat(self, event=None):
        if not self.loaded_code:
            messagebox.showerror("Error", "Load project first.")
            return

        question = self.chat_input.get()
        if not question: return

        self.chat_input.delete(0, tk.END)
        self._append_bubble(question, "user")

        def task():
            response = ai.chat_with_code(self.loaded_code, question, self.chat_history)
            self.chat_history += f"\nUser: {question}\nAI: {response}"
            self.root.after(0, lambda: self._append_bubble(response, "ai"))

        threading.Thread(target=task).start()

    def _append_bubble(self, message, sender):
        self.chat_display.config(state='normal')

        # Add a newline for spacing
        self.chat_display.insert(tk.END, "\n")

        # Insert text with specific tag
        start_index = self.chat_display.index(tk.END)

        if sender == "ai":
            # Parse links for AI
            parts = re.split(r'([\w\-\./\\]+\.\w+)', message)
            for part in parts:
                if re.match(r'[\w\-\./\\]+\.\w+', part) and ("/" in part or "\\" in part):
                    self.chat_display.insert(tk.END, f" {part} ", ("ai", "filepath"))
                else:
                    self.chat_display.insert(tk.END, part, "ai")
        else:
            self.chat_display.insert(tk.END, f" {message} ", "user")

        self.chat_display.insert(tk.END, "\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state='disabled')

    def on_file_click(self, event):
        # Simplified file opening logic
        webbrowser.open(self.project_path)

        # ================= TAB 4: REFACTOR =================

    def _build_tab_refactor(self):
        frame = ttk.Frame(self.tab_refactor)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        top_bar = ttk.Frame(frame)
        top_bar.pack(fill="x", pady=(0, 10))

        ttk.Label(top_bar, text="Code Analysis & Recommendations", style="Header.TLabel").pack(side="left")
        ttk.Button(top_bar, text="RUN ANALYSIS", style="Green.TButton", command=self.run_refactor).pack(side="right")

        # Code Editor Look
        self.refactor_text = scrolledtext.ScrolledText(frame, bg="#1e1e1e", fg="#dcdcdc", font=("Consolas", 11),
                                                       relief="flat", insertbackground="white")
        self.refactor_text.pack(fill="both", expand=True)

        # Copy Button
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="Copy Report to Clipboard", command=self.copy_refactor).pack(side="right")

    def run_refactor(self):
        if not self.loaded_code:
            messagebox.showerror("Error", "Load project first.")
            return

        self.refactor_text.delete("1.0", tk.END)
        self.refactor_text.insert(tk.END, "// Analyzing codebase... please wait...\n")

        def task():
            response = ai.suggest_refactor(self.loaded_code)
            self.root.after(0, lambda: self._update_refactor_ui(response))

        threading.Thread(target=task).start()

    def _update_refactor_ui(self, text):
        self.refactor_text.delete("1.0", tk.END)
        self.refactor_text.insert(tk.END, text)

    def copy_refactor(self):
        content = self.refactor_text.get("1.0", tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        messagebox.showinfo("Copied", "Analysis copied to clipboard!")