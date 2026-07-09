"""
Handles extracting raw text from uploaded files and splitting it into
overlapping chunks suitable for embedding. Overlap preserves context
across chunk boundaries so answers don't lose meaning mid-sentence.
"""
import os
from pypdf import PdfReader

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 800))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 100))


def extract_text(file_path: str, filename: str) -> str:
    """Extract raw text from a PDF or plain text file."""
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(file_path)
        text = ""
        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            # Tag each page so we can cite page numbers later
            text += f"\n[PAGE {page_num + 1}]\n{page_text}"
        return text
    else:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    """
    Split text into overlapping chunks by character count.
    Returns a list of dicts: {"text": chunk, "page": page_number}
    """
    # Split by page markers first so we can track which page each chunk came from
    pages = text.split("[PAGE ")
    chunks = []

    for part in pages:
        if not part.strip():
            continue
        if "]" in part[:6]:
            page_num_str, content = part.split("]", 1)
            try:
                page_num = int(page_num_str.strip())
            except ValueError:
                page_num = None
        else:
            page_num = None
            content = part

        content = content.strip()
        start = 0
        while start < len(content):
            end = start + chunk_size
            chunk = content[start:end].strip()
            if chunk:
                chunks.append({"text": chunk, "page": page_num})
            start += chunk_size - overlap

    return chunks
