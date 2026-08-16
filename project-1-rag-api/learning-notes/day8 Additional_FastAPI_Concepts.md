# Day 8.2 — Additional FastAPI Concepts

> These are concepts we learned during Day 8 that were not explicitly listed in the original study plan, but are directly related to the Day 8 implementation.

---

## 1. Request Model vs Response Model

### Request Model

Defines the structure of data coming **into** the API.

```python
class AskRequest(BaseModel):
    question: str
```

Example:

```json
{
  "question": "What is RAG?"
}
```

### Response Model

Defines the structure of data going **out of** the API.

```python
class AskResponse(BaseModel):
    answer: str
```

Example:

```json
{
  "answer": "RAG stands for Retrieval-Augmented Generation."
}
```

### Simple Mental Model

```text
Request Model
     ↓
Incoming data

Response Model
     ↓
Outgoing data
```

---

## 2. What Happens During Pydantic Validation?

Suppose we have:

```python
class AskRequest(BaseModel):
    question: str
```

A request reaches FastAPI:

```text
Client
  ↓
JSON Request
  ↓
FastAPI
  ↓
Pydantic Validation
  ↓
Valid?
```

If valid:

```text
Validation
   ↓
Endpoint function executes
```

If invalid:

```text
Validation
   ↓
❌ Error
   ↓
422 response
```

The endpoint function does **not** execute when request validation fails.

---

## 3. Manual Validation vs Pydantic

### Manual validation

We would have to check inputs ourselves:

```text
Check field exists
     ↓
Check data type
     ↓
Check required fields
     ↓
Check constraints
     ↓
Return error if invalid
```

### Pydantic

We define the expected structure:

```python
class AskRequest(BaseModel):
    question: str
```

Pydantic handles the validation automatically.

### Key Idea

> Pydantic lets us define what valid data should look like instead of manually checking every input.

---

## 4. HTTPException

FastAPI provides `HTTPException` to return an HTTP error from an endpoint.

```python
from fastapi import HTTPException

raise HTTPException(
    status_code=404,
    detail="User not found"
)
```

Response:

```json
{
  "detail": "User not found"
}
```

---

## 5. Common HTTP Status Codes

### `200` — Success

The request completed successfully.

```text
GET /users/1
→ 200 OK
```

### `404` — Not Found

The requested resource does not exist.

```text
GET /users/999
→ 404 Not Found
```

### `422` — Validation Error

The request data doesn't match the expected structure.

```text
POST /ask
{
  "question": {...}
}
→ 422
```

---

## 6. `/docs` and Swagger UI

FastAPI automatically generates an interactive API documentation page:

```text
/docs
```

It is based on the API's OpenAPI schema.

It allows us to:

- View endpoints
- See HTTP methods
- See request models
- See response models
- Enter request data
- Execute requests
- Inspect responses

Example:

```text
/docs
   ↓
POST /ask
   ↓
Try it out
   ↓
Enter JSON
   ↓
Execute
   ↓
View response
```

---

## 7. FastAPI Request/Response Flow

The concepts we learned can be connected like this:

```text
Client
  ↓
HTTP Request
  ↓
FastAPI
  ↓
Pydantic Validation
  ↓
Endpoint
  ↓
Business Logic
  ↓
Response Model
  ↓
JSON Response
  ↓
Client
```

If validation fails:

```text
Client
  ↓
HTTP Request
  ↓
FastAPI
  ↓
Pydantic Validation
  ↓
❌ Validation Error
  ↓
422 Response
```

---

## 8. Our RAG API Architecture

The Day 8 API was designed as a starting structure for our RAG application.

```text
Client
   │
   ├── POST /upload
   │       ↓
   │    Upload documents
   │
   ├── POST /index
   │       ↓
   │    Trigger indexing
   │
   └── POST /ask
           ↓
        Ask question
           ↓
       RAG pipeline
           ↓
          Answer
```

At Day 8, these are still placeholder endpoints.

---

## 9. Why `/ask`?

`/ask` is our own FastAPI endpoint.

It does not mean we are directly calling Gemini from `/ask`.

The eventual architecture is:

```text
Client
  ↓
POST /ask
  ↓
FastAPI
  ↓
RAG Pipeline
  ↓
LLM
  ↓
Answer
  ↓
Client
```

So:

```text
/upload → Upload documents
/index  → Process/index documents
/ask    → Ask a question and receive an answer
```

---

# Day 8.2 Key Takeaways

```text
Pydantic
→ Defines and validates data

Request Model
→ Incoming data

Response Model
→ Outgoing data

HTTPException
→ Return API errors

200
→ Success

404
→ Not Found

422
→ Validation Error

/docs
→ Interactive API documentation

FastAPI Flow
→ Request → Validation → Endpoint → Response
```
