from docx import Document
from pypdf import PdfReader

def read_dox_pdf(file_path):
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