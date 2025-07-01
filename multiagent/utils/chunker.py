def chunk_text(text, max_tokens=500, overlap=100):
    tokens = text.split()
    chunks = []
    i = 0
    while i < len(tokens):
        chunks.append(" ".join(tokens[i : i + max_tokens]))
        i += max_tokens - overlap
    return chunks
