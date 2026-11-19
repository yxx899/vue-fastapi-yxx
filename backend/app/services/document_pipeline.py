import uuid
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.orm import Session

from app.config import settings
from app.models.entities import Document, DocumentChunk, DocumentStatus
from app.services.document_parser import clean_text, extract_text
from app.services.embedding import embed_texts
from app.services.vector_store import add_chunks, delete_by_ids


def process_document(db: Session, document_id: int) -> None:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        return
    try:
        _clear_vectors(db, doc)
        raw = extract_text(doc.file_path, doc.filename)
        text = clean_text(raw)
        if not text:
            raise ValueError("文档无有效文本内容")
        chunk_size = doc.chunk_size or settings.chunk_size
        chunk_overlap = doc.chunk_overlap or settings.chunk_overlap
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", " ", ""],
        )
        chunks = splitter.split_text(text)
        if not chunks:
            raise ValueError("分块结果为空")

        vector_ids: list[str] = []
        metadatas: list[dict] = []
        documents: list[str] = []
        for idx, chunk in enumerate(chunks):
            vid = f"t{doc.tenant_id}_d{doc.id}_c{idx}_{uuid.uuid4().hex[:8]}"
            vector_ids.append(vid)
            documents.append(chunk)
            metadatas.append(
                {
                    "tenant_id": doc.tenant_id,
                    "kb_id": doc.kb_id,
                    "document_id": doc.id,
                    "document_name": doc.filename,
                    "chunk_index": idx,
                }
            )
            db.add(
                DocumentChunk(
                    tenant_id=doc.tenant_id,
                    document_id=doc.id,
                    chunk_index=idx,
                    content=chunk,
                    vector_id=vid,
                )
            )

        embeddings = embed_texts(documents)
        add_chunks(ids=vector_ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

        doc.status = DocumentStatus.SUCCESS
        doc.error_message = None
        db.commit()
    except Exception as e:
        db.rollback()
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)[:2000]
            db.commit()


def _clear_vectors(db: Session, doc: Document) -> None:
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).all()
    delete_by_ids([c.vector_id for c in chunks])
    for c in chunks:
        db.delete(c)
    db.commit()


def delete_document_vectors(db: Session, doc: Document) -> None:
    _clear_vectors(db, doc)
