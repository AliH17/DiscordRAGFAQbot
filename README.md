# DiscordRAGFAQbot
Discord RAG FAQ Bot: PDFs are ingested, chunked, and indexed (Sentence-Transformers + FAISS) in a FastAPI backend. On /ask, relevant passages are retrieved, sent to Groq LLM, and returned as Discord embeds with source citations. Users give 👍/👎 feedback (with modal comments). Entire stack is Dockerized for cloud deployment.
