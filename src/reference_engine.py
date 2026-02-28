import io
import re
from pathlib import Path

from pypdf import PdfReader

REFERENCE_DIR = Path(__file__).resolve().parent.parent / "data" / "references"


def _ensure_reference_dir() -> None:
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)


def _sanitize_name(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    return safe if safe.lower().endswith(".pdf") else f"{safe}.pdf"


def ingest_pdf_file(uploaded_file) -> dict:
    _ensure_reference_dir()
    filename = _sanitize_name(uploaded_file.name)
    pdf_path = REFERENCE_DIR / filename
    text_path = REFERENCE_DIR / f"{pdf_path.stem}.txt"

    raw_bytes = uploaded_file.getvalue()
    pdf_path.write_bytes(raw_bytes)

    reader = PdfReader(io.BytesIO(raw_bytes))
    pages = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        normalized = " ".join(page_text.split())
        if normalized:
            pages.append(normalized)

    joined_text = "\n\n".join(pages)
    text_path.write_text(joined_text, encoding="utf-8")

    return {
        "filename": filename,
        "pages": len(reader.pages),
        "chars": len(joined_text),
        "text_file": text_path.name,
    }


def get_reference_catalog() -> list[dict]:
    _ensure_reference_dir()
    items = []
    for txt_file in sorted(REFERENCE_DIR.glob("*.txt")):
        content = txt_file.read_text(encoding="utf-8", errors="ignore")
        items.append({"file": txt_file.name, "chars": len(content)})
    return items


def _keywords_for_tema(tema: str) -> list[str]:
    base = [
        "paciente",
        "conduta",
        "diagnóstico",
        "assinale",
        "respectivamente",
        "exame",
        "laboratoriais",
        "fisiologia",
        "fisiopatologia",
        "mecanismo",
    ]
    mapping = {
        "Ferropriva": ["ferro", "ferritina", "microcítica", "transferrina"],
        "Megaloblástica": ["b12", "folato", "macrocítica", "hipersegmentados"],
        "Doença crônica": ["inflamação", "hepcidina", "ferritina"],
        "Hemolítica": ["hemólise", "reticulócitos", "haptoglobina", "ldh"],
        "Aplásica": ["pancitopenia", "medula", "hipocelular"],
    }
    return base + mapping.get(tema, [])


def build_style_context(tema: str, max_chars: int = 1800) -> str:
    _ensure_reference_dir()
    txt_files = list(REFERENCE_DIR.glob("*.txt"))
    if not txt_files:
        return ""

    keywords = [word.lower() for word in _keywords_for_tema(tema)]
    ranked: list[tuple[int, str]] = []

    for txt_file in txt_files:
        content = txt_file.read_text(encoding="utf-8", errors="ignore")
        chunks = re.split(r"\n{2,}", content)
        for chunk in chunks:
            normalized = " ".join(chunk.split())
            if len(normalized) < 120:
                continue
            score = sum(1 for key in keywords if key in normalized.lower())
            if score > 0:
                ranked.append((score, normalized))

    if not ranked:
        return ""

    ranked.sort(key=lambda item: item[0], reverse=True)
    selected: list[str] = []
    used = 0
    for _, chunk in ranked[:20]:
        if used + len(chunk) > max_chars:
            break
        selected.append(chunk)
        used += len(chunk)

    return "\n\n".join(selected)
