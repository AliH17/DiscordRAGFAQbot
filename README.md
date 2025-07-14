# DiscordRAGFAQbot
Discord RAG FAQ Bot: PDFs are ingested, chunked, and indexed (Sentence-Transformers + FAISS) in a FastAPI backend. On /ask, relevant passages are retrieved, sent to Groq LLM, and returned as Discord embeds with source citations. Users give 👍/👎 feedback (with modal comments). Entire stack is Dockerized for cloud deployment.

# Discord RAG FAQ Bot

## Features
- `/ask` command in Discord with RAG‐powered answers
- PDF ingestion via `/api/ingest`
- Feedback collection (👍/👎 + modal)
- Metrics at `/metrics`

## Quickstart

1. **Clone**  
   ```bash
   git clone https://github.com/<YOU>/faqbot.git
   cd faqbot

2. Environment
Copy .env.example → .env and fill in:

DISCORD_TOKEN=…
CLIENT_ID=…
GUILD_ID=…
GROQ_API_KEY=…
GROQ_MODEL=…

3. Run locally with Docker

docker build -t faq-backend:latest ./backend
docker run -d -p 8000:8000 --name faq-backend \
  -e GROQ_API_KEY=$GROQ_API_KEY \
  -e GROQ_MODEL=$GROQ_MODEL \
  faq-backend:latest

docker build -t faq-bot:latest .
docker run -d --name faq-bot \
  -e DISCORD_TOKEN=$DISCORD_TOKEN \
  -e CLIENT_ID=$CLIENT_ID \
  -e GUILD_ID=$GUILD_ID \
  -e RAG_API=http://host.docker.internal:8000/api/rag-query \
  -e FEEDBACK_API=http://host.docker.internal:8000/api/feedback \
  faq-bot:latest

4. Ingest documents

curl -X POST http://localhost:8000/api/ingest -F "file=@./data/backend.pdf"

5. Try it
In your Discord server, /ask What is the FAQ bot?
