"""Semantic search engine — ONNX embeddings + numpy cosine similarity."""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path

import numpy as np

from brain.config import (
    EMBEDDING_CHUNK_WORDS,
    EMBEDDING_DIM,
    EMBEDDING_INDEX_DIR,
    EMBEDDING_MODEL,
    VAULT_PATH,
)
from brain.vault import frontmatter

log = logging.getLogger(__name__)

# Index files
EMBEDDINGS_FILE = EMBEDDING_INDEX_DIR / "embeddings.npz"
METADATA_FILE = EMBEDDING_INDEX_DIR / "metadata.json"

# Skip these directories when scanning vault
_SKIP_DIRS = {".brain", ".obsidian", ".git", "templates"}

# Thread safety
_lock = threading.Lock()

# Lazy-loaded model state
_session = None  # onnxruntime.InferenceSession
_tokenizer = None  # tokenizers.Tokenizer

# In-memory index
_embeddings: np.ndarray | None = None  # (N, 384)
_metadata: dict | None = None  # {"version", "model", "chunks": [...]}


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def _ensure_model() -> None:
    """Lazy-load ONNX model and tokenizer on first use."""
    global _session, _tokenizer

    if _session is not None:
        return

    from huggingface_hub import hf_hub_download
    from tokenizers import Tokenizer
    import onnxruntime as ort

    log.info("Loading embedding model %s ...", EMBEDDING_MODEL)
    t0 = time.time()

    # Download ONNX model + tokenizer from HuggingFace cache
    model_path = hf_hub_download(EMBEDDING_MODEL, "onnx/model.onnx")
    tokenizer_path = hf_hub_download(EMBEDDING_MODEL, "tokenizer.json")

    _session = ort.InferenceSession(
        model_path,
        providers=["CPUExecutionProvider"],
    )
    _tokenizer = Tokenizer.from_file(tokenizer_path)
    _tokenizer.enable_padding(pad_id=0, pad_token="[PAD]", length=256)
    _tokenizer.enable_truncation(max_length=256)

    log.info("Model loaded in %.1fs", time.time() - t0)


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------

def _encode(texts: list[str]) -> np.ndarray:
    """Encode texts into normalized embeddings. Returns (N, 384) float32."""
    _ensure_model()

    encodings = _tokenizer.encode_batch(texts)

    input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
    attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
    token_type_ids = np.zeros_like(input_ids)

    outputs = _session.run(
        None,
        {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "token_type_ids": token_type_ids,
        },
    )

    # Mean pooling over token embeddings (output[0] = last_hidden_state)
    token_embeddings = outputs[0]  # (batch, seq_len, dim)
    mask_expanded = attention_mask[:, :, np.newaxis].astype(np.float32)
    sum_embeddings = (token_embeddings * mask_expanded).sum(axis=1)
    sum_mask = mask_expanded.sum(axis=1).clip(min=1e-9)
    embeddings = sum_embeddings / sum_mask

    # L2 normalize
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True).clip(min=1e-9)
    return (embeddings / norms).astype(np.float32)


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _chunk_document(text: str, meta: dict, rel_path: str) -> list[tuple[str, dict]]:
    """Split document into chunks of ~EMBEDDING_CHUNK_WORDS words.

    Returns list of (chunk_text, chunk_metadata).
    """
    # Strip frontmatter — we only embed the body
    _, body = frontmatter.parse(text)
    if not body.strip():
        return []

    paragraphs = body.split("\n\n")
    chunks: list[tuple[str, dict]] = []
    current_words: list[str] = []
    current_text_parts: list[str] = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        words = para.split()
        if current_words and len(current_words) + len(words) > EMBEDDING_CHUNK_WORDS:
            # Flush current chunk
            chunk_text = "\n\n".join(current_text_parts)
            chunks.append((chunk_text, {
                "path": rel_path,
                "chunk_index": len(chunks),
                "title": meta.get("title", ""),
                "tags": meta.get("tags", []),
                "mtime": 0.0,
                "preview": chunk_text[:150].replace("\n", " "),
            }))
            current_words = []
            current_text_parts = []
        current_words.extend(words)
        current_text_parts.append(para)

    # Flush remaining
    if current_text_parts:
        chunk_text = "\n\n".join(current_text_parts)
        chunks.append((chunk_text, {
            "path": rel_path,
            "chunk_index": len(chunks),
            "title": meta.get("title", ""),
            "tags": meta.get("tags", []),
            "mtime": 0.0,
            "preview": chunk_text[:150].replace("\n", " "),
        }))

    # Set total_chunks
    for _, cm in chunks:
        cm["total_chunks"] = len(chunks)

    return chunks


# ---------------------------------------------------------------------------
# Vault scanning
# ---------------------------------------------------------------------------

def _scan_vault() -> list[tuple[Path, float]]:
    """Walk vault for all .md files. Returns (path, mtime) pairs."""
    results = []
    for md in VAULT_PATH.rglob("*.md"):
        rel = md.relative_to(VAULT_PATH)
        if any(part in _SKIP_DIRS for part in rel.parts):
            continue
        try:
            results.append((md, md.stat().st_mtime))
        except OSError:
            continue
    return results


# ---------------------------------------------------------------------------
# Index persistence
# ---------------------------------------------------------------------------

def _load_index() -> bool:
    """Load index from disk into memory. Returns True if loaded."""
    global _embeddings, _metadata

    if not EMBEDDINGS_FILE.exists() or not METADATA_FILE.exists():
        return False

    try:
        data = np.load(str(EMBEDDINGS_FILE))
        _embeddings = data["embeddings"]
        _metadata = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
        return True
    except Exception as e:
        log.warning("Failed to load index: %s", e)
        _embeddings = None
        _metadata = None
        return False


def _save_index() -> None:
    """Persist current in-memory index to disk (atomic write)."""
    EMBEDDING_INDEX_DIR.mkdir(parents=True, exist_ok=True)

    # Atomic write — write to temp, then rename
    tmp_emb = EMBEDDINGS_FILE.with_suffix(".tmp.npz")
    tmp_meta = METADATA_FILE.with_suffix(".tmp.json")

    try:
        np.savez_compressed(str(tmp_emb), embeddings=_embeddings)
        tmp_meta.write_text(
            json.dumps(_metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_emb.rename(EMBEDDINGS_FILE)
        tmp_meta.rename(METADATA_FILE)
    except Exception as e:
        log.error("Failed to save index: %s", e)
        # Clean up temp files
        for f in (tmp_emb, tmp_meta):
            if f.exists():
                f.unlink()


# ---------------------------------------------------------------------------
# Index building
# ---------------------------------------------------------------------------

def build_index(force: bool = False) -> int:
    """Full index rebuild. Returns number of chunks indexed."""
    global _embeddings, _metadata

    with _lock:
        _ensure_model()

        vault_files = _scan_vault()
        all_texts: list[str] = []
        all_meta: list[dict] = []

        for path, mtime in vault_files:
            rel = str(path.relative_to(VAULT_PATH))
            try:
                content = path.read_text(encoding="utf-8")
            except Exception:
                continue

            meta, _ = frontmatter.parse(content)
            chunks = _chunk_document(content, meta or {}, rel)

            for chunk_text, chunk_meta in chunks:
                chunk_meta["mtime"] = mtime
                all_texts.append(chunk_text)
                all_meta.append(chunk_meta)

        if not all_texts:
            _embeddings = np.zeros((0, EMBEDDING_DIM), dtype=np.float32)
            _metadata = {"version": 1, "model": EMBEDDING_MODEL, "chunks": []}
            _save_index()
            return 0

        # Encode in batches to avoid OOM
        batch_size = 64
        encoded_parts = []
        for i in range(0, len(all_texts), batch_size):
            batch = all_texts[i : i + batch_size]
            encoded_parts.append(_encode(batch))

        _embeddings = np.vstack(encoded_parts)
        _metadata = {
            "version": 1,
            "model": EMBEDDING_MODEL,
            "chunks": all_meta,
        }

        _save_index()
        return len(all_texts)


def _check_staleness() -> list[str]:
    """Compare index mtimes against actual file mtimes. Return stale paths."""
    if _metadata is None:
        return []

    indexed: dict[str, float] = {}
    for chunk in _metadata["chunks"]:
        path = chunk["path"]
        if path not in indexed or chunk["mtime"] > indexed[path]:
            indexed[path] = chunk["mtime"]

    stale = []
    vault_files = _scan_vault()
    current_paths = set()

    for path, mtime in vault_files:
        rel = str(path.relative_to(VAULT_PATH))
        current_paths.add(rel)
        if rel not in indexed or indexed[rel] < mtime:
            stale.append(rel)

    # Detect deleted files
    for indexed_path in indexed:
        if indexed_path not in current_paths:
            stale.append(indexed_path)

    return stale


def _update_paths(stale_paths: list[str]) -> int:
    """Re-index specific paths. Returns number of chunks updated."""
    global _embeddings, _metadata

    if not stale_paths:
        return 0

    stale_set = set(stale_paths)

    # Remove old chunks for stale paths
    keep_indices = [
        i for i, c in enumerate(_metadata["chunks"])
        if c["path"] not in stale_set
    ]

    if keep_indices:
        new_embeddings = _embeddings[keep_indices]
        new_chunks = [_metadata["chunks"][i] for i in keep_indices]
    else:
        new_embeddings = np.zeros((0, EMBEDDING_DIM), dtype=np.float32)
        new_chunks = []

    # Add new chunks for paths that still exist
    new_texts: list[str] = []
    new_meta: list[dict] = []

    for rel_path in stale_paths:
        full_path = VAULT_PATH / rel_path
        if not full_path.exists():
            continue  # deleted file — just remove from index

        try:
            content = full_path.read_text(encoding="utf-8")
            mtime = full_path.stat().st_mtime
        except Exception:
            continue

        meta, _ = frontmatter.parse(content)
        chunks = _chunk_document(content, meta or {}, rel_path)

        for chunk_text, chunk_meta in chunks:
            chunk_meta["mtime"] = mtime
            new_texts.append(chunk_text)
            new_meta.append(chunk_meta)

    if new_texts:
        new_vecs = _encode(new_texts)
        _embeddings = np.vstack([new_embeddings, new_vecs]) if len(new_embeddings) > 0 else new_vecs
        _metadata["chunks"] = new_chunks + new_meta
    else:
        _embeddings = new_embeddings
        _metadata["chunks"] = new_chunks

    _save_index()
    return len(new_texts)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search(query: str, top_k: int = 10, folder: str = "", tags: str = "") -> str:
    """Semantic search over vault. Returns formatted results string."""
    global _embeddings, _metadata

    with _lock:
        _ensure_model()

        # Load or build index
        if _embeddings is None:
            if not _load_index():
                log.info("No index found, building...")
                count = build_index()
                if count == 0:
                    return "Vault is empty — nothing to search."

        # Check for stale entries and update
        stale = _check_staleness()
        if stale:
            _update_paths(stale)

    # Encode query (no lock needed — model is thread-safe for inference)
    query_vec = _encode([query])  # (1, 384)

    with _lock:
        if _embeddings is None or len(_embeddings) == 0:
            return "Index is empty."

        # Cosine similarity (embeddings are already normalized)
        scores = (_embeddings @ query_vec.T).squeeze()  # (N,)

        # Apply filters
        tag_filter = {t.strip() for t in tags.split(",") if t.strip()} if tags else set()
        folder_prefix = folder.rstrip("/") + "/" if folder else ""

        candidates = []
        for i, score in enumerate(scores):
            chunk = _metadata["chunks"][i]
            if folder_prefix and not chunk["path"].startswith(folder_prefix):
                continue
            if tag_filter and not (tag_filter & set(chunk.get("tags", []))):
                continue
            candidates.append((float(score), i))

    if not candidates:
        return f"No results for '{query}'" + (
            f" in folder '{folder}'" if folder else ""
        ) + (f" with tags [{tags}]" if tags else "")

    # Sort by score descending, take top_k
    candidates.sort(key=lambda x: x[0], reverse=True)
    top = candidates[:top_k]

    # Format output
    lines = [f"## Semantic Search: \"{query}\"\n"]
    for rank, (score, idx) in enumerate(top, 1):
        chunk = _metadata["chunks"][idx]
        chunk_info = ""
        if chunk.get("total_chunks", 1) > 1:
            chunk_info = f" (chunk {chunk['chunk_index']+1}/{chunk['total_chunks']})"
        lines.append(
            f"{rank}. [{score:.2f}] {chunk['path']}{chunk_info}\n"
            f"   {chunk.get('preview', '')}\n"
        )

    total_chunks = len(_metadata["chunks"])
    lines.append(f"({len(top)} results, {total_chunks} chunks indexed)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Single document update (called from write_vault hook)
# ---------------------------------------------------------------------------

def update_single_document(vault_path: str) -> None:
    """Re-index a single document after write. Thread-safe."""
    try:
        _ensure_model()

        with _lock:
            if _embeddings is None:
                if not _load_index():
                    # No index yet — skip, will build on first search
                    return

            _update_paths([vault_path])

    except Exception as e:
        log.warning("Embedding update failed for %s: %s", vault_path, e)
