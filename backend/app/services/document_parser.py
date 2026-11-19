import re
import unicodedata
from pathlib import Path


def extract_text(file_path: str, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in {".txt", ".md", ".markdown"}:
        return Path(file_path).read_text(encoding="utf-8", errors="ignore")
    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(file_path)
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)
    if ext in {".docx", ".doc"}:
        from docx import Document as DocxDocument

        doc = DocxDocument(file_path)
        return "\n".join(p.text for p in doc.paragraphs)
    raise ValueError(f"不支持的文件类型: {ext}")


def clean_text(text: str) -> str:
    # NFKC：把 PDF 常见兼容字（如 ⼯→工、⽤→用）归一成正常汉字，避免检索对不上
    text = unicodedata.normalize("NFKC", text or "")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r"-\s*\d+\s*-", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
