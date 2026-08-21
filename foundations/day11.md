# Day 11 — FastAPI StreamingResponse

## 1. What is Streaming?

A normal API waits for the complete response before sending it:

```text
Client
  ↓
POST /ask
  ↓
LLM generates complete answer
  ↓
Complete response
  ↓
Client
```

With streaming, the server sends pieces as they become available:

```text
Client
  ↓
POST /ask/stream
  ↓
Generate response
  ↓
Chunk 1 → Client
  ↓
Chunk 2 → Client
  ↓
Chunk 3 → Client
  ↓
...
```

This allows the user to start reading before the complete answer is generated.

---

## 2. StreamingResponse

FastAPI provides `StreamingResponse` for streaming data to the client.

```python
from fastapi.responses import StreamingResponse
```

Example:

```python
@app.post("/ask/stream")
async def ask_stream():

    async def generate():
        yield "Hello "
        yield "from "
        yield "FastAPI"

    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )
```

`StreamingResponse` does not generate the data. It streams the data produced by the generator.

---

## 3. `return` vs `yield`

### `return`

`return` gives a value and ends the function.

```python
def example():
    return "Hello"
```

```text
Function starts
     ↓
return "Hello"
     ↓
Function ends
```

### `yield`

`yield` produces one value and pauses the generator so it can continue later.

```python
def example():
    yield "Hello"
    yield "World"
```

```text
yield "Hello"
      ↓
pause
      ↓
continue
      ↓
yield "World"
```

### Simple difference

```text
return → give the result and finish

yield → give one piece and continue later
```

---

## 4. Async Generator

An async generator uses:

```python
async def
```

with:

```python
yield
```

Example:

```python
async def generate():
    yield "Hello"
    yield "World"
```

This is useful for streaming because data can be produced asynchronously.

---

## 5. Testing Streaming

Swagger `/docs` is not ideal for visually verifying streaming because it may display the collected response instead of showing each piece as it arrives.

We tested using the terminal.

Run FastAPI:

```bash
uvicorn main:app --reload
```

Then use another terminal:

```powershell
curl.exe -N -X POST http://127.0.0.1:8000/ask/stream
```

`-N` tells curl not to buffer the response.

---

## 6. Simulating Streaming

We used `asyncio.sleep()` to simulate an LLM taking time to produce the next piece.

```python
import asyncio
from fastapi.responses import StreamingResponse


@app.post("/ask/stream")
async def ask_stream():

    async def generate():
        yield "Hello "
        await asyncio.sleep(1)

        yield "from "
        await asyncio.sleep(1)

        yield "FastAPI"

    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )
```

The client receives the pieces separately with delays.

This verified that the response was actually being streamed.

---

## 7. Gemini Streaming Concept

The Day 11 plan uses Gemini's streaming API.

Conceptually:

```text
Question
   ↓
Gemini
   ↓
Response chunk 1
   ↓
Response chunk 2
   ↓
Response chunk 3
   ↓
...
```

Our async generator can pass those chunks to the client:

```python
async def generate():

    for chunk in gemini_response:
        yield chunk.text
```

Then:

```python
return StreamingResponse(
    generate(),
    media_type="text/plain"
)
```

Complete architecture:

```text
POST /ask/stream
       ↓
FastAPI
       ↓
Gemini streaming API
       ↓
Response chunks
       ↓
async generator
       ↓
yield
       ↓
StreamingResponse
       ↓
Client
```

The actual Gemini integration was not implemented because a Gemini API key was not available during this exercise.

---

## 8. Why Streaming Feels Better

Without streaming:

```text
User
 ↓
[wait.........................]
 ↓
Complete answer
```

With streaming:

```text
User
 ↓
Answer starts
 ↓
More text
 ↓
More text
 ↓
Complete answer
```

Even if the total generation time is similar, streaming provides immediate feedback and lets the user start reading while the rest of the answer is being generated.

---

# Day 11 — End-of-Day Questions

## 1. What is the difference between `return` and `yield`?

`return` gives a response/value and ends the function.

`yield` gives one piece of data and pauses the generator, allowing it to continue and produce the next piece later.

## 2. Why does streaming feel better to users even if the total time is the same?

Because the user receives the beginning of the answer immediately instead of waiting for the entire response. The user can start reading while the remaining response is being generated.

---

# Day 11 — Final Status

```text
StreamingResponse                 ✅
Async generator                   ✅
yield                             ✅
return vs yield                   ✅
Streaming endpoint                ✅
Terminal streaming test           ✅
StreamingResponse media type      ✅
Gemini streaming integration      ⏳
```

Gemini integration remains pending because Gemini API access was not available during this exercise.
