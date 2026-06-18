"""
Documentation indexer that reads markdown/text documents, splits them
into semantic sections, and creates embeddings for retrieval.
"""

import re
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

SUPPORTED_EXTENSIONS = {".md", ".txt", ".rst", ".adoc"}


class DocSection:
    def __init__(self, filepath: str, title: str, content: str):
        self.filepath = filepath
        self.title = title
        self.content = content

    def to_dict(self) -> dict:
        return {
            "filepath": self.filepath,
            "title": self.title,
            "content": self.content,
        }


class DocsIndex:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.sections: list[DocSection] = []
        self.embeddings: np.ndarray | None = None

    def index_directory(self, root_dir: str) -> int:
        """Walk the directory and index all documentation files."""
        root = Path(root_dir)
        if not root.exists():
            raise FileNotFoundError(f"Directory not found: {root_dir}")

        self.sections = []
        for filepath in sorted(root.rglob("*")):
            if not filepath.is_file():
                continue
            if filepath.suffix not in SUPPORTED_EXTENSIONS:
                continue
            rel_path = str(filepath.relative_to(root))
            if _should_skip(rel_path):
                continue
            try:
                content = filepath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            sections = _split_by_headings(rel_path, content)
            self.sections.extend(sections)

        if not self.sections:
            return 0

        texts = [f"Document: {s.filepath} | Section: {s.title}\n\n{s.content}" for s in self.sections]
        self.embeddings = self.model.encode(texts, normalize_embeddings=True)
        return len(self.sections)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Return top-k most relevant document sections for the query."""
        if self.embeddings is None or len(self.sections) == 0:
            return []

        query_embedding = self.model.encode([query], normalize_embeddings=True)
        similarities = np.dot(self.embeddings, query_embedding.T).flatten()
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score < 0.15:
                break
            section = self.sections[idx]
            results.append({**section.to_dict(), "score": round(score, 4)})
        return results

    def list_indexed_docs(self) -> list[dict]:
        """Return list of indexed documents with their section titles."""
        docs = {}
        for s in self.sections:
            if s.filepath not in docs:
                docs[s.filepath] = []
            docs[s.filepath].append(s.title)
        return [{"filepath": fp, "sections": titles} for fp, titles in docs.items()]


def _split_by_headings(filepath: str, content: str) -> list[DocSection]:
    """Split markdown content by headings into logical sections."""
    heading_pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)

    matches = list(heading_pattern.finditer(content))
    if not matches:
        title = Path(filepath).stem.replace("-", " ").replace("_", " ").title()
        return [DocSection(filepath, title, content.strip())]

    sections = []

    if matches[0].start() > 0:
        preamble = content[: matches[0].start()].strip()
        if preamble:
            sections.append(DocSection(filepath, "(Introduction)", preamble))

    for i, match in enumerate(matches):
        title = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[start:end].strip()
        if body:
            sections.append(DocSection(filepath, title, body))

    return sections


def _should_skip(rel_path: str) -> bool:
    skip_patterns = ["__pycache__", ".git", "node_modules", ".venv"]
    return any(p in rel_path for p in skip_patterns)
