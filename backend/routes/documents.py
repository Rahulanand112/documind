import os
import uuid
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException

from services.document_processor import extract_text, chunk_text
from services.vector_store import add_chunks, list_documents, delete_document

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    doc_id = str(uuid.uuid4())
    saved_path = os.path.join(UPLOAD_DIR, f"{doc_id}{ext}")

    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        raw_text = extract_text(saved_path, file.filename)
        if not raw_text.strip():
            raise HTTPException(status_code=422, detail="No extractable text found in file.")

        chunks = chunk_text(raw_text)
        count = add_chunks(doc_id, file.filename, chunks)

        return {
            "doc_id": doc_id,
            "filename": file.filename,
            "chunks_indexed": count,
            "message": "Document uploaded and indexed successfully.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")


@router.get("/documents")
async def get_documents():
    return {"documents": list_documents()}


@router.delete("/documents/{doc_id}")
async def remove_document(doc_id: str):
    delete_document(doc_id)
    return {"message": "Document deleted."}
