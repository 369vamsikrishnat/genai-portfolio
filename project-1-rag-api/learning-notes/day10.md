# Day 10 — FastAPI File Upload + PDF Ingestion + Pinecone

## 1. UploadFile

FastAPI provides `UploadFile` for receiving uploaded files.

```python
from fastapi import UploadFile

@app.post("/upload")
async def upload(file: UploadFile):
    return {
        "filename": file.filename,
        "content_type": file.content_type
    }
```

Useful properties:

```python
file.filename
file.content_type
file.file
```

---

## 2. Saving an Uploaded File

We created a temporary upload directory:

```python
from pathlib import Path

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
```

Then saved the uploaded PDF:

```python
file_path = UPLOAD_DIR / file.filename

with open(file_path, "wb") as buffer:
    buffer.write(await file.read())
```

`wb` means:

```text
w → write
b → binary
```

PDFs are binary files, so they are written in binary mode.

---

## 3. PDF Validation

We don't want users uploading arbitrary file types.

```python
if file.content_type != "application/pdf":
    raise HTTPException(
        status_code=400,
        detail="Only PDF files are allowed"
    )
```

A non-PDF upload produces:

```text
400 Bad Request
```

Example:

```json
{
  "detail": "Only PDF files are allowed"
}
```

---

# 4. PDF Ingestion

We created `ingestion.py` to process the uploaded PDF.

```python
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def ingest_pdf(file_path: str):

    reader = PdfReader(file_path)

    pages_processed = len(reader.pages)

    full_text = ""

    for page in reader.pages:
        text = page.extract_text() or ""
        full_text += text + "\n"

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    chunks = splitter.split_text(full_text)

    return {
        "pages_processed": pages_processed,
        "chunks": chunks
    }
```

---

## 5. Why We Changed the Chunking Strategy

Initially:

```text
1 page → 1 chunk
```

For the 269-page PDF:

```text
269 pages
→ 264 non-empty page-level chunks
```

We then changed to recursive text splitting:

```text
269 pages
    ↓
Extract text
    ↓
RecursiveCharacterTextSplitter
    ↓
365 chunks
```

This is better for RAG because chunks are based on text size and separators rather than simply using page boundaries.

Configuration:

```python
chunk_size=1000
chunk_overlap=200
```

### Chunk overlap

Overlap preserves some context between neighboring chunks.

---

# 6. Pinecone

Pinecone is used as the vector database.

Our index:

```text
rag-index
```

Embedding model:

```text
llama-text-embed-v2
```

The index reported:

```text
dimension = 1024
metric = cosine
```

We verified the connection from Python.

---

# 7. Connecting to Pinecone

`pinecone_client.py` handles the Pinecone connection.

```python
import os
from pinecone import Pinecone

pc = Pinecone(
    api_key=os.environ["PINECONE_API_KEY"]
)

index = pc.Index("rag-index")
```

The API key is kept outside the source code as an environment variable.

---

# 8. Storing Chunks in Pinecone

We created:

```python
def store_chunks(chunks: list[str]):

    records = []

    for i, chunk in enumerate(chunks):
        records.append({
            "_id": f"chunk-{i}",
            "text": chunk
        })

    batch_size = 96

    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]

        index.upsert_records(
            namespace="documents",
            records=batch
        )

    return len(records)
```

### Why batching?

Our first attempt sent all 365 chunks in one request.

Pinecone returned:

```text
Batch size exceeds 96
```

So we changed the implementation to send:

```text
365 chunks
    ↓
96
96
96
77
```

Total:

```text
365 records
```

---

# 9. Complete Upload Flow

```text
Client
  ↓
POST /upload
  ↓
UploadFile
  ↓
Check PDF
  ↓
Save temporarily
  ↓
ingest_pdf()
  ↓
Extract pages
  ↓
Create chunks
  ↓
store_chunks()
  ↓
Pinecone
  ↓
Return statistics
```

Response:

```json
{
  "filename": "uploaded_documnet.pdf",
  "pages_processed": 269,
  "chunks_created": 365,
  "vectors_stored": 365
}
```

---

# 10. Temporary Uploaded Files

After successful ingestion, the temporary PDF generally does not need to remain on the application server.

Current conceptual flow:

```text
PDF
 ↓
Temporary storage
 ↓
Extract text
 ↓
Create chunks
 ↓
Store in Pinecone
 ↓
Delete temporary file
```

If the original PDF is required later, it should be stored in persistent storage instead.

---

# 11. Large File Protection

The current implementation does not yet protect against extremely large uploads.

This is important because:

```python
await file.read()
```

reads the file contents into memory.

A very large upload could consume excessive memory.

A production API should enforce a maximum file size:

```text
Upload
 ↓
Check size
 ↓
Too large?
 ↓
Reject
```

---

# Day 10 — End-of-Day Questions

## 1. What happens to the uploaded file after ingestion — should you keep it or delete it?

For our current project, the uploaded PDF is temporary.

After successful ingestion:

```text
PDF
 ↓
Extract
 ↓
Chunk
 ↓
Store in Pinecone
 ↓
Delete temporary PDF
```

If the original document is required later, store it in persistent storage instead.

---

## 2. How do you prevent someone from uploading a 1GB file and crashing your server?

Set a maximum file-size limit and reject files that exceed it.

The current implementation still needs this protection added.

The important problem is:

```python
await file.read()
```

can load a large file into memory.

---

# Day 10 — Final Result

```text
PDF Upload                         ✅
PDF Validation                     ✅
Temporary File Storage             ✅
PDF Page Extraction                ✅
Recursive Text Splitting           ✅
365 Chunks Created                 ✅
Pinecone Connection                ✅
llama-text-embed-v2                ✅
Pinecone Batch Upload              ✅
365 Vectors Stored                 ✅
Pinecone Dashboard Verified        ✅
Non-PDF Error Tested               ✅
```
