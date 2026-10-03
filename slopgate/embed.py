PREFIX = "Represent this query for searching relevant code: "
model = None


def encode(texts: list[str], query: bool = False) -> list[list[float]]:
    global model
    if model is None:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("nomic-ai/CodeRankEmbed", trust_remote_code=True)
    if query:
        texts = [PREFIX + text for text in texts]
    return model.encode(texts, normalize_embeddings=True).tolist()
