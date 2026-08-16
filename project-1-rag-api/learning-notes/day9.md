# Day 9 — FastAPI Async/Await

## 1. What is Async Programming?

Asynchronous programming allows the application to work on other tasks while one task is waiting for an I/O operation to finish.

### Restaurant Analogy

**Synchronous:**

```text
Take Order A
     ↓
Wait for food
     ↓
Serve A
     ↓
Take Order B
```

**Asynchronous:**

```text
Take Order A
     ↓
Kitchen starts preparing
     ↓
Serve Customer B
     ↓
Come back when A is ready
     ↓
Serve A
```

**Key concept:** While one operation is waiting, other asynchronous work can proceed.

---

## 2. `async def`

`async def` defines an asynchronous function.

```python
async def get_data():
    ...
```

In FastAPI:

```python
@app.post("/ask")
async def ask():
    ...
```

An async function can use `await` for asynchronous operations.

---

## 3. `await`

`await` waits for an asynchronous operation to complete.

```python
response = await client.get(url)
```

Conceptually:

```text
Start operation
     ↓
await
     ↓
Waiting for response
     ↓
Other async work can run
     ↓
Response arrives
     ↓
Continue the function
```

**Key point:** `await` allows the event loop to handle other asynchronous work while the current operation is waiting.

---

## 4. Synchronous vs Asynchronous

### Synchronous

```python
def call_api():
    response = requests.get(url)
    return response
```

The current execution waits for the HTTP response.

```text
Request
  ↓
Call API
  ↓
WAIT
  ↓
Response
  ↓
Continue
```

### Asynchronous

```python
async def call_api():
    response = await client.get(url)
    return response
```

```text
Request
  ↓
Call API
  ↓
await
  ↓
Other async work can run
  ↓
Response
  ↓
Continue
```

---

## 5. Why Async Matters for LLM APIs

An LLM API call is an I/O operation.

```text
FastAPI
   ↓
Gemini API
   ↓
Waiting for response
   ↓
Answer
```

The server may spend time waiting for the external API.

Using async allows the server to handle other asynchronous work while waiting.

---

## 6. Async HTTP Requests with HTTPX

Install:

```bash
pip install httpx
```

Example:

```python
import httpx

async def call_api():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://example.com")

    return response
```

Important parts:

```python
httpx.AsyncClient()
```

Creates an asynchronous HTTP client.

```python
await client.get(...)
```

Makes an asynchronous HTTP request.

---

## 7. Async RAG Pipeline

Our `/ask` endpoint will eventually call the RAG pipeline asynchronously.

```python
async def rag_pipeline(question: str) -> str:
    return f"RAG answer for: {question}"
```

Then:

```python
@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    answer = await rag_pipeline(request.question)

    return AskResponse(
        answer=answer
    )
```

### Flow

```text
POST /ask
    ↓
AskRequest
    ↓
Pydantic validation
    ↓
ask()
    ↓
await rag_pipeline()
    ↓
RAG answer
    ↓
AskResponse
    ↓
JSON
```

---

## 8. Error Handling

If the RAG pipeline or LLM call fails, we can return an HTTP 500 error.

```python
from fastapi import HTTPException

@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    try:
        answer = await rag_pipeline(request.question)

        return AskResponse(
            answer=answer
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="RAG pipeline failed"
        )
```

### Flow

```text
/ask
 ↓
rag_pipeline()
 ↓
Error
 ↓
except
 ↓
HTTP 500
```

Response:

```json
{
  "detail": "RAG pipeline failed"
}
```

---

# 9. What Does `/ask` Mean?

`/ask` is **our FastAPI endpoint**, not the Gemini endpoint.

Its purpose is to allow a client to ask our RAG system a question.

```text
Client
  ↓
POST /ask
  ↓
FastAPI
  ↓
RAG Pipeline
  ↓
LLM (e.g. Gemini)
  ↓
Answer
  ↓
Client
```

For our RAG project:

```text
/upload → Upload documents
/index  → Process/index documents
/ask    → Ask a question and get an answer
```

---

# Day 9 — End-of-Day Questions

## 1. What is happening during the `await` keyword?

`await` waits for an asynchronous operation while allowing the event loop to handle other asynchronous work.

---

## 2. Why would a synchronous LLM endpoint struggle under 10 concurrent users?

A synchronous endpoint can block while waiting for each LLM API response. Multiple requests can therefore spend significant time waiting, reducing the server's ability to efficiently handle concurrent requests.

---

## 3. What is the difference between `async def` and `def` in FastAPI?

`async def` defines an asynchronous endpoint that can use `await` for asynchronous operations.

`def` defines a normal synchronous endpoint.

**Important:** `async def` does not automatically mean multiple requests execute simultaneously. The benefit comes when asynchronous operations use `await`, allowing the event loop to work on other tasks while waiting.

---

# Day 9 Key Takeaways

```text
async def
    ↓
Defines an async function

await
    ↓
Wait for async operation
    ↓
Allow other async work while waiting

httpx.AsyncClient
    ↓
Async HTTP requests

/ask
    ↓
FastAPI endpoint
    ↓
Async RAG pipeline
    ↓
LLM
    ↓
Answer
```
