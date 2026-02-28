import io
import json
import os
import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader

REFERENCE_DIR = Path(__file__).resolve().parent.parent / "data" / "references"
CATALOG_PATH = REFERENCE_DIR / "catalog.json"
DEFAULT_LOCAL_REFERENCE_DIR = Path(__file__).resolve().parent.parent / "data" / "private_references"


def _ensure_reference_dir() -> None:
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_local_reference_dir() -> None:
    DEFAULT_LOCAL_REFERENCE_DIR.mkdir(parents=True, exist_ok=True)


def _sanitize_name(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    return safe if safe.lower().endswith(".pdf") else f"{safe}.pdf"


def _load_catalog() -> list[dict[str, Any]]:
    _ensure_reference_dir()
    if not CATALOG_PATH.exists():
        return []
    try:
        return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_catalog(entries: list[dict[str, Any]]) -> None:
    _ensure_reference_dir()
    CATALOG_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def _infer_category_and_version(filename: str) -> tuple[str, str]:
    lower = filename.lower()
    category = "geral"
    if "guyton" in lower or "fisiologia" in lower:
        category = "fisiologia"
    elif "diretriz" in lower or "guideline" in lower or "manual" in lower:
        category = "diretriz"
    elif "prova" in lower or "quest" in lower or "enamed" in lower:
        category = "questoes"

    version = ""
    match = re.search(r"(\d{1,2})\s*(?:a|ª)?\s*(?:ed|edi|edição|edicao)", lower)
    if match:
        version = f"{match.group(1)}ª edição"
    elif "guyton" in lower:
        numeric = re.search(r"(\d{1,2})", lower)
        if numeric:
            version = f"{numeric.group(1)}ª edição"

    return category, version


def ingest_pdf_file(uploaded_file, category: str = "geral", version_label: str = "") -> dict[str, Any]:
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

    inferred_category, inferred_version = _infer_category_and_version(filename)
    final_category = category or inferred_category
    final_version = version_label.strip() or inferred_version

    _upsert_catalog_entry(
        source_file=filename,
        text_file=text_path.name,
        category=final_category,
        version=final_version,
        pages=len(reader.pages),
        chars=len(joined_text),
    )

    return {
        "filename": filename,
        "pages": len(reader.pages),
        "chars": len(joined_text),
        "text_file": text_path.name,
        "category": final_category,
        "version": final_version,
    }


def _upsert_catalog_entry(
    source_file: str,
    text_file: str,
    category: str,
    version: str,
    pages: int,
    chars: int,
) -> None:
    catalog = _load_catalog()
    updated = False
    for item in catalog:
        if item.get("text_file") == text_file:
            item.update(
                {
                    "source_file": source_file,
                    "text_file": text_file,
                    "category": category,
                    "version": version,
                    "pages": pages,
                    "chars": chars,
                }
            )
            updated = True
            break

    if not updated:
        catalog.append(
            {
                "source_file": source_file,
                "text_file": text_file,
                "category": category,
                "version": version,
                "pages": pages,
                "chars": chars,
            }
        )

    _save_catalog(catalog)


def _ingest_pdf_path(pdf_path: Path) -> None:
    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        return

    filename = _sanitize_name(pdf_path.name)
    target_pdf = REFERENCE_DIR / filename
    text_file = REFERENCE_DIR / f"{Path(filename).stem}.txt"

    if target_pdf.exists() and text_file.exists():
        if text_file.name in {item.get("text_file") for item in _load_catalog()}:
            return

    try:
        raw_bytes = pdf_path.read_bytes()
        target_pdf.write_bytes(raw_bytes)

        reader = PdfReader(io.BytesIO(raw_bytes))
        pages = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            normalized = " ".join(page_text.split())
            if normalized:
                pages.append(normalized)

        joined_text = "\n\n".join(pages)
        text_file.write_text(joined_text, encoding="utf-8")

        category, version = _infer_category_and_version(filename)
        _upsert_catalog_entry(
            source_file=filename,
            text_file=text_file.name,
            category=category,
            version=version,
            pages=len(reader.pages),
            chars=len(joined_text),
        )
    except Exception:
        return


def auto_ingest_local_references() -> None:
    _ensure_reference_dir()
    _ensure_local_reference_dir()

    for pdf_path in REFERENCE_DIR.glob("*.pdf"):
        _ingest_pdf_path(pdf_path)

    local_path_str = os.getenv("HEMATOQUEST_LOCAL_REFERENCE_DIR", "").strip()
    local_dir = Path(local_path_str) if local_path_str else DEFAULT_LOCAL_REFERENCE_DIR
    if not local_dir.exists() or not local_dir.is_dir():
        return

    for pdf_path in local_dir.glob("*.pdf"):
        _ingest_pdf_path(pdf_path)


def get_reference_catalog() -> list[dict[str, Any]]:
    catalog = _load_catalog()
    txt_names = {item.get("text_file", "") for item in catalog}

    for txt_file in sorted(REFERENCE_DIR.glob("*.txt")):
        if txt_file.name not in txt_names:
            content = txt_file.read_text(encoding="utf-8", errors="ignore")
            category, version = _infer_category_and_version(txt_file.name)
            catalog.append(
                {
                    "source_file": txt_file.with_suffix(".pdf").name,
                    "text_file": txt_file.name,
                    "category": category,
                    "version": version,
                    "pages": 0,
                    "chars": len(content),
                }
            )

    _save_catalog(catalog)
    return catalog


def get_default_reference_files() -> tuple[list[str], list[str]]:
    catalog = get_reference_catalog()
    preferred_version = os.getenv("HEMATOQUEST_GUYTON_VERSION", "").strip().lower()

    style_files = [
        item["text_file"]
        for item in catalog
        if item.get("category") in {"questoes", "diretriz", "geral"} and item.get("text_file")
    ]

    physiology_items = [item for item in catalog if item.get("category") == "fisiologia" and item.get("text_file")]
    if preferred_version:
        preferred = [
            item for item in physiology_items if preferred_version in item.get("version", "").lower() or preferred_version in item.get("source_file", "").lower()
        ]
        explanation_files = [item["text_file"] for item in preferred] if preferred else [item["text_file"] for item in physiology_items]
    else:
        explanation_files = [item["text_file"] for item in physiology_items]

    return style_files, explanation_files


def get_reference_labels(text_files: list[str]) -> list[str]:
    catalog = get_reference_catalog()
    label_by_text = {}
    for item in catalog:
        text_file = item.get("text_file", "")
        if not text_file:
            continue
        source = item.get("source_file", text_file)
        version = item.get("version", "")
        label_by_text[text_file] = f"{source} ({version})" if version else source

    labels: list[str] = []
    for text_file in text_files:
        if text_file in label_by_text:
            labels.append(label_by_text[text_file])
    return labels


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


def _build_context(
    tema: str,
    allowed_text_files: list[str] | None = None,
    max_chars: int = 1800,
    preferred_categories: list[str] | None = None,
) -> str:
    catalog = get_reference_catalog()
    if not catalog:
        return ""

    allowed_set = set(allowed_text_files or [])
    preferred_set = set(preferred_categories or [])
    keywords = [word.lower() for word in _keywords_for_tema(tema)]
    ranked: list[tuple[int, str]] = []

    for item in catalog:
        text_file = item.get("text_file", "")
        category = item.get("category", "geral")
        if not text_file:
            continue
        if allowed_set and text_file not in allowed_set:
            continue

        txt_path = REFERENCE_DIR / text_file
        if not txt_path.exists():
            continue

        content = txt_path.read_text(encoding="utf-8", errors="ignore")
        chunks = re.split(r"\n{2,}", content)
        category_bonus = 2 if preferred_set and category in preferred_set else 0

        for chunk in chunks:
            normalized = " ".join(chunk.split())
            if len(normalized) < 120:
                continue
            score = sum(1 for key in keywords if key in normalized.lower()) + category_bonus
            if score > 0:
                ranked.append((score, normalized))

    if not ranked:
        return ""

    ranked.sort(key=lambda entry: entry[0], reverse=True)
    selected: list[str] = []
    used = 0
    for _, chunk in ranked[:40]:
        if used + len(chunk) > max_chars:
            break
        selected.append(chunk)
        used += len(chunk)

    return "\n\n".join(selected)


def build_style_context(
    tema: str,
    selected_text_files: list[str] | None = None,
    max_chars: int = 1800,
) -> str:
    return _build_context(
        tema=tema,
        allowed_text_files=selected_text_files,
        max_chars=max_chars,
        preferred_categories=["questoes", "geral", "diretriz"],
    )


def build_explanation_context(
    tema: str,
    selected_text_files: list[str] | None = None,
    max_chars: int = 1800,
) -> str:
    return _build_context(
        tema=tema,
        allowed_text_files=selected_text_files,
        max_chars=max_chars,
        preferred_categories=["fisiologia", "diretriz", "geral"],
    )
