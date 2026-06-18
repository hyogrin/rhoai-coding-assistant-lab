"""
Code indexer that reads source files, splits them into chunks,
and creates embeddings using sentence-transformers.
"""

import os
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

SUPPORTED_EXTENSIONS = {".py", ".yaml", ".yml", ".json", ".toml", ".md", ".txt", ".sh"}
MAX_CHUNK_LINES = 40
OVERLAP_LINES = 5


class CodeChunk:
    def __init__(self, filepath: str, start_line: int, end_line: int, content: str):
        self.filepath = filepath
        self.start_line = start_line
        self.end_line = end_line
        self.content = content

    def to_dict(self) -> dict:
        return {
            "filepath": self.filepath,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "content": self.content,
        }


class CodeIndex:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.chunks: list[CodeChunk] = []
        self.embeddings: np.ndarray | None = None

    def index_directory(self, root_dir: str) -> int:
        """Walk the directory and index all supported source files."""
        root = Path(root_dir)
        if not root.exists():
            raise FileNotFoundError(f"Directory not found: {root_dir}")

        self.chunks = []
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
            chunks = _split_into_chunks(rel_path, content)
            self.chunks.extend(chunks)

        if not self.chunks:
            return 0

        texts = [f"File: {c.filepath}\n{c.content}" for c in self.chunks]
        self.embeddings = self.model.encode(texts, normalize_embeddings=True)
        return len(self.chunks)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Return top-k most relevant code chunks for the query."""
        if self.embeddings is None or len(self.chunks) == 0:
            return []

        query_embedding = self.model.encode([query], normalize_embeddings=True)
        similarities = np.dot(self.embeddings, query_embedding.T).flatten()
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score < 0.1:
                break
            chunk = self.chunks[idx]
            results.append({**chunk.to_dict(), "score": round(score, 4)})
        return results

    def get_file_content(self, root_dir: str, filepath: str) -> str | None:
        """Read a specific file from the indexed directory."""
        target = Path(root_dir) / filepath
        if not target.exists() or not target.is_file():
            return None
        return target.read_text(encoding="utf-8", errors="replace")

    def list_indexed_files(self) -> list[str]:
        """Return sorted list of all indexed file paths."""
        return sorted(set(c.filepath for c in self.chunks))


def _split_into_chunks(filepath: str, content: str) -> list[CodeChunk]:
    """Split file content into overlapping chunks."""
    lines = content.splitlines()
    if len(lines) <= MAX_CHUNK_LINES:
        return [CodeChunk(filepath, 1, len(lines), content)]

    chunks = []
    start = 0
    while start < len(lines):
        end = min(start + MAX_CHUNK_LINES, len(lines))
        chunk_lines = lines[start:end]
        chunk_content = "\n".join(chunk_lines)
        chunks.append(CodeChunk(filepath, start + 1, end, chunk_content))
        start += MAX_CHUNK_LINES - OVERLAP_LINES
    return chunks


def _should_skip(rel_path: str) -> bool:
    """Skip generated files, caches, and virtual environments."""
    skip_patterns = [
        "__pycache__",
        ".git",
        "node_modules",
        ".venv",
        "venv",
        ".egg-info",
        "dist/",
        "build/",
    ]
    return any(p in rel_path for p in skip_patterns)
