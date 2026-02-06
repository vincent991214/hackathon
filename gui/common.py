"""
GUI Common Module

Shared components for the DevMate AI application.
This module contains theme constants and the RichTextRenderer class
used across different parts of the application.
"""

import tkinter as tk
import re
import webbrowser
import os


# ==================== THEME CONSTANTS ====================
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


# ==================== RICH TEXT RENDERER ====================
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
        from tkinter import messagebox
        messagebox.showinfo("Copied", "Code snippet copied to clipboard!")
