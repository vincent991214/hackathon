# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**DevMate AI - Enterprise Edition** is a Python-based GUI application for AI-powered documentation generation and code analysis. It uses Tkinter for the interface and integrates with the GLM-4.7 model via OpenAI-compatible API to generate technical documentation from codebases.

## Development Setup

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Architecture

The application follows a three-layer architecture:

### GUI Layer (`gui/app.py`)
- Entry point: `main.py` launches `DocGeneratorApp`
- 4-tab interface using `ttk.Notebook`:
  1. **Project Setup**: Folder selection and codebase scanning
  2. **Documentation**: Template configuration and documentation generation
  3. **AI Assistant**: Chat interface with codebase context
  4. **Code Refactor**: Automated refactoring suggestions
- `RichTextRenderer` class handles markdown rendering with syntax highlighting for code blocks
- All AI operations run in separate threads to prevent GUI freezing

### AI Layer (`ai/client.py`)
- Uses `openai==0.28` library with GLM-4.7 model (hosted on open.bigmodel.cn)
- Four main functions:
  - `generate_template()`: Reverse-engineers documentation into reusable templates with intent instructions
  - `generate_docs()`: Generates documentation from code using template structure
  - `chat_with_code()`: AI assistant for code questions with chat history
  - `suggest_refactor()`: Provides 3 specific code improvement suggestions
- `_clean_response()` removes "Thinking..." blocks from AI responses

### Utilities Layer (`utils/`)
- `file_reader.py`:
  - `read_codebase()`: Scans folders for code files (.py, .js, .html, .css, .java, .cpp by default)
  - `read_dox_pdf()`: Extracts text from .docx or .pdf files
- `doc_writer.py`:
  - `save_to_docx()`: Converts markdown to formatted Word documents with headers, tables, and formatting
  - Custom markdown parser supporting tables, headers, bullet points, and bold text

## Key Design Patterns

1. **Threaded AI Operations**: All AI API calls are wrapped in `threading.Thread()` to maintain UI responsiveness
2. **Template-Based Generation**: Documentation uses a two-step process: generate template structure, then fill with code content
3. **Markdown to Word Conversion**: Custom parser in `doc_writer.py` handles tables, headers, and formatting
4. **Regex-Based Syntax Highlighting**: `RichTextRenderer` uses regex patterns for keyword, string, comment, and number highlighting
5. **Manual Scrollbar Management**: Text widgets use explicit scrollbar configuration for consistent styling

## Important Configuration Notes

- **API Key**: Currently hardcoded in `ai/client.py` line 5 (TODO: move to .env file per TASKS.md)
- **Base URL**: `https://open.bigmodel.cn/api/coding/paas/v4`
- **Model**: GLM-4.7
- **Theme**: Dark VS Code-inspired theme with constants at top of `gui/app.py`
- **Output Files**: Generated documents are saved as `Template.docx` and `Project_Docs.docx`

## Code Truncation Limits

- `generate_docs()` truncates code to 15,000 characters
- `chat_with_code()` and `suggest_refactor()` truncate code to 20,000 characters
- Chat history is limited to 2,000 most recent characters

## TODO Items (from TASKS.md)

1. Move environment variables (API key, base URL) from `ai/client.py` to `.env` file
2. Add UI tab for editing `template_md` before calling `generate_docs()`
