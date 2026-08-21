# Day 12 — Streamlit UI + FastAPI Integration

## Goal

Build a simple Streamlit frontend for the FastAPI application.

```text
PDF upload → POST /upload → FastAPI → ingestion → Pinecone

Question → POST /ask/stream → FastAPI → streaming response → Streamlit chat UI
```

---

## 1. Project Structure

```text
F:\ai\
├── main.py
├── ingestion.py
├── pinecone_client.py
├── ui.py
└── uploads\
```

`ui.py` is the Streamlit frontend.

---

## 2. Install Streamlit

```bash
pip install streamlit
streamlit --version
```

Run it with:

```bash
streamlit run ui.py
```

FastAPI runs separately:

```bash
uvicorn main:app --reload
```

---

## 3. Streamlit Basics

```python
import streamlit as st
import requests
```

### `st.title()`

```python
st.title("RAG Document Assistant")
```

Displays the page title.

### `st.file_uploader()`

```python
uploaded_file = st.file_uploader(
    "Upload a PDF",
    type=["pdf"]
)
```

Creates a file-upload widget. `type=["pdf"]` limits the UI to PDFs.

### `st.button()`

```python
if st.button("Upload"):
    ...
```

Runs the code inside the block when the button is clicked.

---

## 4. Calling `/upload`

```python
response = requests.post(
    "http://127.0.0.1:8000/upload",
    files={
        "file": (
            uploaded_file.name,
            uploaded_file,
            "application/pdf"
        )
    }
)
```

This sends the uploaded PDF from Streamlit to FastAPI.

Handle the result:

```python
if response.status_code == 200:
    st.success("PDF uploaded successfully")
    st.json(response.json())
else:
    st.error(response.text)
```

Expected response from our current backend:

```json
{
  "filename": "uploaded_documnet.pdf",
  "pages_processed": 269,
  "chunks_created": 365,
  "vectors_stored": 365
}
```

---

## 5. Question Input

Basic input:

```python
question = st.text_input("Enter your question")
```

Chat-style input:

```python
question = st.chat_input(
    "Ask a question about your document"
)
```

When the user submits:

```python
if question:
    ...
```

the UI can call:

```text
POST /ask/stream
```

---

## 6. Calling `/ask/stream`

```python
response = requests.post(
    "http://127.0.0.1:8000/ask/stream",
    data=question,
    stream=True
)
```

`stream=True` tells `requests` to process the HTTP response progressively rather than waiting for the complete response.

This connects directly to Day 11's `StreamingResponse`.

---

## 7. Reading Streaming Chunks

```python
for chunk in response.iter_content(
    chunk_size=None,
    decode_unicode=True
):
    if chunk:
        ...
```

`iter_content()` lets the client process pieces of the response as they arrive.

Conceptually:

```text
FastAPI
  ↓
chunk 1
  ↓
Streamlit
  ↓
chunk 2
  ↓
Streamlit
  ↓
chunk 3
  ↓
Streamlit
```

---

## 8. Chat-Style Display

### `st.chat_message()`

```python
with st.chat_message("user"):
    st.write(question)
```

Assistant:

```python
with st.chat_message("assistant"):
    st.write(answer)
```

This creates the chat-style interface.

---

## 9. `st.session_state`

Streamlit reruns the Python script when users interact with the application.

To preserve messages:

```python
if "messages" not in st.session_state:
    st.session_state.messages = []
```

Example message:

```python
{
    "role": "user",
    "content": "What is RAG?"
}
```

Assistant message:

```python
{
    "role": "assistant",
    "content": "RAG stands for..."
}
```

Display previous messages:

```python
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
```

---

## 10. Streaming the Assistant Answer

`st.empty()` creates a placeholder that can be updated.

```python
response_placeholder = st.empty()

answer = ""

for chunk in response.iter_content(
    chunk_size=None,
    decode_unicode=True
):
    if chunk:
        answer += chunk
        response_placeholder.markdown(answer)
```

The displayed answer grows as chunks arrive:

```text
RAG
↓
RAG is
↓
RAG is a technique
↓
RAG is a technique where...
```

---

## 11. Saving the Conversation

After streaming finishes:

```python
st.session_state.messages.append({
    "role": "user",
    "content": question
})

st.session_state.messages.append({
    "role": "assistant",
    "content": answer
})
```

This keeps the conversation available after Streamlit reruns.

---

## 12. Complete UI Concept

```python
import streamlit as st
import requests

st.title("RAG Document Assistant")

# PDF upload
uploaded_file = st.file_uploader(
    "Upload a PDF",
    type=["pdf"]
)

if uploaded_file is not None:

    if st.button("Upload"):

        response = requests.post(
            "http://127.0.0.1:8000/upload",
            files={
                "file": (
                    uploaded_file.name,
                    uploaded_file,
                    "application/pdf"
                )
            }
        )

        if response.status_code == 200:
            st.success("PDF uploaded successfully")
            st.json(response.json())
        else:
            st.error(response.text)


# Chat state
if "messages" not in st.session_state:
    st.session_state.messages = []


# Previous messages
for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.write(message["content"])


# Question
question = st.chat_input(
    "Ask a question about your document"
)


if question:

    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):

        response_placeholder = st.empty()
        answer = ""

        response = requests.post(
            "http://127.0.0.1:8000/ask/stream",
            data=question,
            stream=True
        )

        for chunk in response.iter_content(
            chunk_size=None,
            decode_unicode=True
        ):
            if chunk:
                answer += chunk
                response_placeholder.markdown(answer)

    st.session_state.messages.append({
        "role": "user",
        "content": question
    })

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })
```

---

## 13. Full Architecture

```text
                 Streamlit UI
                      │
          ┌───────────┴───────────┐
          ↓                       ↓
      Upload PDF             Ask Question
          │                       │
          ↓                       ↓
      POST /upload           POST /ask/stream
          │                       │
          ↓                       ↓
       FastAPI                 FastAPI
          │                       │
          ↓                       ↓
      PDF ingestion          RAG / LLM
          │                       │
          ↓                       ↓
       Pinecone             StreamingResponse
                                  │
                                  ↓
                              Streamlit
                                  │
                                  ↓
                            Chat display
```

---

## 14. What Was Not Executed

The Day 12 code was prepared but not executed during the study session.

Therefore these are **pending verification**, not completed tests:

```text
Streamlit installation              ⏳
Streamlit app launch                ⏳
PDF upload from Streamlit            ⏳
/upload integration test             ⏳
Question input test                  ⏳
/ask/stream integration test         ⏳
Chat display test                    ⏳
Streaming answer in Streamlit        ⏳
Full FastAPI + Streamlit run         ⏳
5-question demo                      ⏳
Screen recording                     ⏳
GitHub push                          ⏳
```

The concepts and code structure are covered, but they should only be marked verified after execution.

---

## 15. Gemini / RAG Status

The actual Gemini streaming integration is still pending because Gemini API access was not available.

Therefore the complete production flow:

```text
Question
 ↓
RAG retrieval
 ↓
Gemini
 ↓
Streaming answer
```

is not yet implemented/tested.

The separate RAG pipeline will be built later as planned.

---

## 16. Day 12 Demo Plan

When execution is possible:

1. Start FastAPI.

```bash
uvicorn main:app --reload
```

2. Start Streamlit.

```bash
streamlit run ui.py
```

3. Open the Streamlit application.
4. Upload a PDF.
5. Verify the upload response.
6. Ask 5 questions.
7. Verify the chat-style responses.
8. Record the demo.
9. Push the project to GitHub.

---

## Day 12 Concepts Covered

```text
Streamlit
st.title()
st.file_uploader()
st.button()
st.text_input()
st.chat_input()
st.chat_message()
st.empty()
st.success()
st.error()
st.json()
st.session_state

requests.post()
HTTP communication
File upload using requests
stream=True
iter_content()
Streaming UI
Chat-style display
FastAPI + Streamlit architecture
```

## Day 12 Final Status

**Concepts:** Covered ✅

**Code prepared:** Yes ✅

**Execution/testing:** Pending ⏳

**Full RAG + Gemini integration:** Later ⏳
