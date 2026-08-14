# Day 8 — FastAPI + REST Endpoints

## 1. FastAPI First Steps

FastAPI is a Python framework for building APIs.

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}
```

### Concept

`FastAPI()` creates the application.

`@app.get("/")` defines an API endpoint.

---

## 2. Path Parameters

Path parameters identify a specific resource through the URL.

```python
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}
```

Request:

```text
/users/25
```

Response:

```json
{
  "user_id": 25
}
```

### Concept

**Path parameter → Which resource?**

---

## 3. Request Body

The request body contains data sent to the API.

```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int
```

```python
@app.post("/users")
async def create_user(user: User):
    return user
```

Request:

```json
{
  "name": "Vamsi",
  "age": 25
}
```

### Concept

**Request body → What data are we sending?**

---

## 4. Pydantic Models

Pydantic models define the expected structure and data types.

```python
class AskRequest(BaseModel):
    question: str
```

Expected request:

```json
{
  "question": "What is RAG?"
}
```

Pydantic automatically validates incoming data.

### Manual Validation vs Pydantic

Without Pydantic:

```text
Manually check every field
→ Check required fields
→ Check data types
→ Check validity
```

With Pydantic:

```text
Define model
→ Automatic validation
```

---

## 5. Response Model

A response model defines the structure of the API response.

```python
class AskResponse(BaseModel):
    answer: str
```

```python
@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    return {
        "answer": "This is the answer"
    }
```

Response:

```json
{
  "answer": "This is the answer"
}
```

### Concept

```text
Request Model  → Incoming data

Response Model → Outgoing data
```

---

## 6. `/docs`

FastAPI automatically provides:

```text
/docs
```

Swagger UI allows us to:

- View endpoints
- Test APIs
- See schemas
- Execute requests
- View responses

---

## 7. Pydantic Validation

```python
class AskRequest(BaseModel):
    question: str
```

Valid:

```json
{
  "question": "What is RAG?"
}
```

Invalid:

```json
{
  "question": {
    "text": "What is RAG?"
  }
}
```

Response:

```text
422 Unprocessable Entity
```

Validation happens before the endpoint executes.

---

## 8. Error Handling

```python
from fastapi import HTTPException

raise HTTPException(
    status_code=404,
    detail="User not found"
)
```

Common status codes:

```text
200 → Success
404 → Not Found
422 → Validation Error
```

---

# Day 8 Mini Project

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    answer: str

@app.post("/upload")
async def upload():
    return {"message": "Upload endpoint"}

@app.post("/index")
async def index():
    return {"message": "Indexing triggered"}

@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    return AskResponse(
        answer=f"You asked: {request.question}"
    )
```

### Endpoints

```text
POST /upload
POST /index
POST /ask
```

### Run

```bash
uvicorn main:app --reload
```

Open:

```text
/docs
```

---

# Key Takeaways

| Concept | Meaning |
|----------|----------|
| Path Parameter | Which resource |
| Request Body | Data sent to API |
| Pydantic | Validation |
| Response Model | Response structure |
| `/docs` | API testing UI |
| `422` | Validation error |
| `HTTPException` | Return HTTP errors |

## Day 8 Mental Model

```text
HTTP Request
     ↓
FastAPI
     ↓
Pydantic Validation
     ↓
Endpoint
     ↓
Response Model
     ↓
JSON Response
```

---

# Day 8 — End-of-Day Questions

## 1. What does Pydantic do and why is it better than manual validation?

Pydantic defines the expected data structure and types and automatically validates incoming data.

Manual validation requires writing checks for fields and data types ourselves.

---

## 2. What is the `/docs` endpoint and why does it exist?

`/docs` is FastAPI's automatically generated Swagger UI.

It provides interactive API documentation where we can:

- View endpoints
- See request/response schemas
- Send test requests
- View responses

---

## 3. What is the difference between a path parameter and a request body?

**Path parameter** identifies which resource we want.

Example:

```text
/users/25
```

Here `25` is the path parameter.

**Request body** contains data that we send to the API.

Example:

```json
{
  "question": "What is RAG?"
}
```

### Simple mental model

```text
Path Parameter → Which resource?

Request Body → What data are we sending?
```

---

## Day 8 Final Revision

```text
FastAPI
    ↓
Request
    ↓
Pydantic Validation
    ↓
Endpoint
    ↓
Response Model
    ↓
JSON Response
```
