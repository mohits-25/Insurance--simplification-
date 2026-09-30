"""
Lightweight local RAG using Chroma with its bundled default embedding
function (ONNX MiniLM) — no extra heavy ML deps required.
One collection per document, keyed by document_id, stored in-memory
(ephemeral client) so restart clears state — fine for a 2-hour MVP.
"""
import chromadb
from chromadb.utils import embedding_functions

_client = chromadb.EphemeralClient()
_embed_fn = embedding_functions.DefaultEmbeddingFunction()

_CHUNK_SIZE = 800
_CHUNK_OVERLAP = 150


def _chunk_text(text: str, size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    if len(text) <= size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def index_document(document_id: str, clauses: list) -> int:
    """
    clauses: list of sections.Clause objects (section, page, text — all sanitized).
    Returns number of chunks indexed.
    """
    try:
        _client.delete_collection(document_id)
    except Exception:
        pass
    collection = _client.create_collection(name=document_id, embedding_function=_embed_fn)

    ids, docs, metadatas = [], [], []
    idx = 0
    for clause in clauses:
        for chunk in _chunk_text(clause.text):
            ids.append(f"{document_id}-{idx}")
            docs.append(chunk)
            metadatas.append({
                "page": clause.page,
                "section": clause.section,
                "clauseType": clause.section.lower().replace(" ", "_"),
            })
            idx += 1

    if not docs:
        return 0

    collection.add(ids=ids, documents=docs, metadatas=metadatas)
    return len(docs)


def query_document(document_id: str, query: str, top_k: int = 4) -> list[dict]:
    try:
        collection = _client.get_collection(name=document_id, embedding_function=_embed_fn)
    except Exception:
        return []

    results = collection.query(query_texts=[query], n_results=top_k)
    output = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    for doc, meta in zip(docs, metas):
        output.append({"text": doc, "page": meta.get("page"), "section": meta.get("section"), "clauseType": meta.get("clauseType")})
    return output
