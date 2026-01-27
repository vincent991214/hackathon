import os
import fnmatch
from docx import Document
from pypdf import PdfReader


def read_codebase(folder_path, file_pattern="*"):
    """
    Scans folder and returns a single string of code.
    Supports filtering by pattern (e.g., '*.py', 'main.py').
    """
    code_content = ""
    # Default extensions if no specific pattern is provided or if pattern is generic
    default_extensions = ['.py', '.js', '.html', '.css', '.java', '.cpp']

    # If user provided a specific extension like "*.py", we use that.
    # If they left it as "*", we use our safe default list.
    use_defaults = file_pattern.strip() == "*" or file_pattern.strip() == ""

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            # Check if file matches the user's pattern
            if fnmatch.fnmatch(file, file_pattern) or (
                    use_defaults and any(file.endswith(ext) for ext in default_extensions)):

                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        code_content += f"\n\n--- FILE: {file} ---\n"
                        code_content += f.read()
                except Exception:
                    pass

    return code_content


def read_template(file_path):
    """Reads text from .docx or .pdf templates."""
    text = ""
    try:
        if file_path.endswith('.docx'):
            doc = Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif file_path.endswith('.pdf'):
            reader = PdfReader(file_path)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error reading template: {e}")
        return None