import os
import logging
from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx
import pickle
import faiss
from sentence_transformers import SentenceTransformer
import numpy as np
from pdfminer.high_level import extract_text

# 1. Load your FAISS index + metadata at startup
with open("faiss_index.pkl", "rb") as f:
    index, docs = pickle.load(f)

# 2. Load a local embedding model once
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
# 1. Load environment
load_dotenv()

# 2. Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger("rag-backend")

# 3. FastAPI app
app = FastAPI(title="YourRAGBot Backend", version="0.1.0")



# --- load existing index + docs at startup ---
INDEX_PATH = "faiss_index.pkl"
if os.path.exists(INDEX_PATH):
    with open(INDEX_PATH, "rb") as f:
        index, docs = pickle.load(f)
else:
    # first run: empty index
    docs = []
    dim = 384  # sentence-transformers all-MiniLM-L6-v2 dim
    index = faiss.IndexFlatL2(dim)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

@app.post("/api/ingest")
async def ingest(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF uploads are supported.")
    
    # 1. Save upload
    dest = os.path.join(DATA_DIR, file.filename)
    with open(dest, "wb") as f:
        f.write(await file.read())

    # 2. Extract & chunk
    text = extract_text(dest)
    size, overlap = 1000, 200
    new_docs, new_embeddings = [], []
    for i in range(0, len(text), size - overlap):
        chunk = text[i : i + size].replace("\n", " ")
        doc_id = f"{file.filename}_{i}"
        new_docs.append({"id": doc_id, "text": chunk, "source": file.filename})

    # 3. Embed all new chunks
    texts = [d["text"] for d in new_docs]
    embs = embed_model.encode(texts, show_progress_bar=False)
    embs = np.array(embs, dtype="float32")

    # 4. Append to FAISS & metadata
    index.add(embs)
    docs.extend(new_docs)

    # 5. Persist updated index + docs
    with open(INDEX_PATH, "wb") as f:
        pickle.dump((index, docs), f)

    return {"status": "indexed", "file": file.filename, "chunks": len(new_docs)}


# 4. Request / Response models
class RagQueryRequest(BaseModel):
    query: str


class RagQueryResponse(BaseModel):
    answer: str
    sources: list[str] = []


class FeedbackRequest(BaseModel):
    messageId: str
    userId: str
    feedbackType: str  # "positive" | "negative"
    comments: str | None = None


class FeedbackResponse(BaseModel):
    status: str = "ok"


# 5. Stubbed RAG service integration
async def call_rag_service(query: str) -> RagQueryResponse:
    # — Embed the incoming query —
    qvec = embed_model.encode(query)
    D, I = index.search(np.array([qvec], dtype="float32"), k=3)

    # — Assemble context & sources —
    context = "\n\n".join(docs[i]["text"] for i in I[0])
    sources = [docs[i]["source"] for i in I[0]]

    # — Call Groq’s chat endpoint —
    api_key = os.getenv("GROQ_API_KEY")
    model  = os.getenv("GROQ_MODEL")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Use the context below to answer the question."},
            {"role": "user",   "content": f"Context:\n{context}\n\nQuestion: {query}"}
        ]
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload
        )
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail="LLM service error")
        data = r.json()

    # — Extract the answer and return —
    answer = data["choices"][0]["message"]["content"]
    # Deduplicate sources
    unique_sources = list(dict.fromkeys(sources))
    return RagQueryResponse(answer=answer, sources=unique_sources)

# 6. Endpoints
@app.post("/api/rag-query", response_model=RagQueryResponse)
async def rag_query(req: RagQueryRequest):
    logger.info(f"Received /rag-query: {req.query}")
    try:
        resp = await call_rag_service(req.query)
        logger.info("RAG service succeeded")
        return resp
    except Exception as e:
        logger.error(f"RAG service error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="RAG processing failed")


@app.post("/api/feedback", response_model=FeedbackResponse)
async def feedback(req: FeedbackRequest):
    logger.info(f"Feedback received: {req}")
    # TODO: persist to your feedback store (DB, analytics pipeline, etc.)
    # Example stub:
    try:
        # e.g., write to PostgreSQL, Kafka, etc.
        logger.debug("Persisting feedback (stub)")
        return FeedbackResponse()
    except Exception as e:
        logger.error(f"Feedback persistence error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not record feedback")


# 7. Health check (optional)
@app.get("/healthz")
def healthz():
    return {"status": "ok"}
