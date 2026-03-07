import os
from pypdf import PdfReader
from docx import Document

def extract_text_from_file(file_path: str) -> str:
    """
    Extracts text from PDF, DOCX, TXT files.
    """
    ext = os.path.splitext(file_path)[1].lower()
    text = ""

    if ext == ".pdf":
        reader = PdfReader(file_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

    elif ext == ".docx":
        doc = Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"

    else:
        raise ValueError(f"Unsupported file format: {ext}")

    return text.strip()
