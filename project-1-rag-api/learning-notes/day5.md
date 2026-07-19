# Day 5 - LangChain RAG Fundamentals

> **Goal:** Understand the core building blocks of a RAG (Retrieval-Augmented Generation) application before building a complete pipeline.

---

# Table of Contents

1. What is LangChain?
2. What is a Document?
3. Document Loaders
4. Chat Models
5. OpenAI vs ChatOpenAI
6. Prompt Templates
7. ChatPromptTemplate
8. Embedding Models
9. Chat Model vs Embedding Model
10. Vector Stores
11. Vector Store vs Vector Database
12. Retrievers
13. Vector Store vs Retriever
14. Indexing Pipeline
15. Complete Architecture
16. Interview Questions
17. Common Mistakes
18. Quick Revision

---

# 1. What is LangChain?

## Definition

LangChain is an open-source framework for building applications powered by Large Language Models (LLMs). It provides reusable components for loading documents, generating embeddings, storing vectors, retrieving information, interacting with LLMs, and building AI workflows.

---

## Why do we need LangChain?

Without LangChain:

- Write custom code for every model
- Handle prompts manually
- Build retrieval logic from scratch
- Connect databases manually

With LangChain:

- Standard APIs
- Reusable components
- Easy model switching
- Faster AI application development

---

## Architecture

```text
                LangChain
                    │
     ┌──────────────┼──────────────┐
     │              │              │
 Documents      Chat Models    Vector Stores
     │              │              │
     └──────────────┼──────────────┘
                    │
                 RAG Apps
```

---

# 2. Document

## Definition

A **Document** is LangChain's standard object for storing text along with metadata.

---

## Structure

```python
Document(
    page_content="LangChain is an LLM framework.",
    metadata={
        "source": "book.pdf",
        "page": 10
    }
)
```

---

## Components

### page_content

Contains the actual text.

```text
LangChain is an LLM framework.
```

---

### metadata

Stores information about the document.

Example:

- source
- page number
- author
- filename
- URL

---

## Why not use plain strings?

Instead of

```python
text = "Hello"
```

LangChain uses

```python
Document(
    page_content="Hello",
    metadata={...}
)
```

Metadata allows the system to trace where information came from.

---

## Mental Model

```text
Document

↓

Text

+

Metadata
```

---

# 3. Document Loaders

## Definition

Document Loaders read external data and convert it into LangChain `Document` objects.

---

## Supported Sources

- PDF
- Word
- Text
- CSV
- HTML
- Websites
- YouTube
- Notion
- Google Drive

---

## Example

```python
from langchain_community.document_loaders import PyPDFLoader

loader = PyPDFLoader("book.pdf")

docs = loader.load()
```

Output

```python
[
    Document(...),
    Document(...),
]
```

---

## Flow

```text
PDF

↓

Document Loader

↓

Document Objects
```

---

# 4. Chat Models

## Definition

A Chat Model is a wrapper around an LLM that accepts messages and generates responses.

---

Example

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI()
```

---

Input

```python
[
    HumanMessage("Hello")
]
```

↓

Output

```python
AIMessage("Hi!")
```

---

## Flow

```text
Messages

↓

Chat Model

↓

AIMessage
```

---

# 5. OpenAI vs ChatOpenAI

This is one of the most common interview questions.

| OpenAI | ChatOpenAI |
|----------|------------|
| API Provider | LangChain Wrapper |
| Sends HTTP requests | Integrates with LangChain |
| No LangChain features | Supports invoke(), stream(), LCEL |
| Generic SDK | LangChain Runnable |

---

## Relationship

```text
Your Code

↓

ChatOpenAI

↓

OpenAI API

↓

GPT Model
```

---

## Important Point

ChatOpenAI is **NOT** another AI model.

It simply wraps the OpenAI API so it works with LangChain.

---

# 6. Prompt Templates

## Definition

A Prompt Template creates reusable prompts with placeholders.

---

Instead of

```python
f"What is {topic}?"
```

we write

```python
PromptTemplate.from_template(
    "What is {topic}?"
)
```

---

Input

```python
{
    "topic":"RAG"
}
```

↓

Output

```text
What is RAG?
```

---

## Benefits

- Reusable
- Cleaner code
- Dynamic prompts

---

# 7. ChatPromptTemplate

## Definition

Creates prompts as chat messages instead of plain text.

---

Example

```python
ChatPromptTemplate.from_messages([
    ("system","You are helpful."),
    ("human","{question}")
])
```

---

Output

```text
System:
You are helpful.

Human:
What is RAG?
```

---

## Flow

```text
Variables

↓

Prompt Template

↓

Messages

↓

Chat Model
```

---

# PromptTemplate vs ChatPromptTemplate

| PromptTemplate | ChatPromptTemplate |
|---------------|-------------------|
| Creates text | Creates messages |
| For text models | For chat models |
| One prompt | Multiple roles |

---

# 8. Embedding Models

## Definition

Embedding Models convert text into numerical vectors.

---

Example

```text
"I love AI"

↓

[0.13, -0.72, 0.44, ...]
```

---

## Why?

Computers cannot compare text efficiently.

Vectors allow mathematical similarity search.

---

## Example

```python
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings()
```

---

## Flow

```text
Text

↓

Embedding Model

↓

Vector
```

---

# 9. Chat Model vs Embedding Model

| Chat Model | Embedding Model |
|------------|----------------|
| Generates text | Generates vectors |
| Input → Messages | Input → Text |
| Output → AIMessage | Output → Numbers |
| Used for answering | Used for searching |

---

## Mental Model

```text
Chat Model

Question

↓

Answer


Embedding Model

Text

↓

Vector
```

---

# 10. Vector Store

## Definition

A Vector Store stores embeddings and performs similarity search.

---

Example

```python
vectorstore = Chroma(...)
```

---

Stored Data

```text
Original Text

+

Embedding

+

Metadata
```

---

## Search Flow

```text
Question

↓

Embedding

↓

Vector Store

↓

Most Similar Documents
```

---

# Popular Vector Stores

- Chroma
- Pinecone
- FAISS
- Qdrant
- Weaviate
- Milvus

---

# 11. Vector Store vs Vector Database

This confused me initially, so here's the distinction:

| Vector Store | Vector Database |
|--------------|----------------|
| LangChain abstraction | Actual storage system |
| Wrapper/API | Database |
| Common interface | Backend implementation |

---

Example

```text
Application

↓

LangChain Chroma Wrapper

↓

Chroma Database
```

---

# 12. Retrievers

## Definition

A Retriever receives a query and returns the most relevant documents.

It does NOT:

- Generate answers ❌
- Store vectors ❌
- Create embeddings ❌

It only retrieves documents.

---

Example

```python
retriever = vectorstore.as_retriever()

docs = retriever.invoke(question)
```

---

Output

```python
[
    Document(...),
    Document(...)
]
```

---

## Flow

```text
Question

↓

Retriever

↓

Vector Store

↓

Relevant Documents
```

---

# Search Types

### Similarity

Nearest vectors.

---

### MMR

Returns relevant and diverse documents.

---

### Hybrid

Combines vector search and keyword search.

---

# 13. Vector Store vs Retriever

| Vector Store | Retriever |
|--------------|-----------|
| Stores embeddings | Retrieves documents |
| Performs search | Uses search strategy |
| Database interface | Retrieval interface |

---

## Mental Model

```text
Retriever

↓

Uses

↓

Vector Store
```

Retriever sits on top of the Vector Store.

---

# 14. Indexing Pipeline

## Definition

Indexing is the offline process of preparing documents for retrieval.

---

## Complete Pipeline

```text
Raw Documents
      │
      ▼
Document Loader
      │
      ▼
Documents
      │
      ▼
Text Splitter
      │
      ▼
Chunks
      │
      ▼
Embedding Model
      │
      ▼
Vectors
      │
      ▼
Vector Store
```

---

## Why Split Documents?

Large documents:

- Poor retrieval
- Too much context
- Lower accuracy

Instead

```text
100 Pages

↓

300 Chunks

↓

Embed Each Chunk
```

---

## Why Offline?

Embedding thousands of documents is expensive.

Do it once.

Reuse forever.

---

# 15. Complete Architecture (Day 5)

```text
                   OFFLINE

PDF
 │
 ▼
Document Loader
 │
 ▼
Documents
 │
 ▼
Text Splitter
 │
 ▼
Chunks
 │
 ▼
Embedding Model
 │
 ▼
Vector Store
```

This completes the indexing phase.

Querying happens on Day 6.

---

# Interview Questions

## What is a Document?

A LangChain object that stores text and metadata.

---

## Why use Embeddings?

To convert text into vectors so semantic similarity search becomes possible.

---

## Difference between ChatOpenAI and OpenAI?

OpenAI is the API provider.

ChatOpenAI is LangChain's wrapper that integrates OpenAI models into the LangChain ecosystem.

---

## Difference between Vector Store and Retriever?

Vector Store stores embeddings and performs searches.

Retriever uses the Vector Store to fetch relevant documents through a standardized interface.

---

## What is Indexing?

The offline process of:

- Loading documents
- Splitting them
- Creating embeddings
- Storing them in a Vector Store

---

# Common Beginner Mistakes

❌ Thinking Documents are just strings.

❌ Thinking ChatOpenAI is a separate LLM.

❌ Confusing Embedding Models with Chat Models.

❌ Thinking Vector Stores generate answers.

❌ Thinking Retrievers store vectors.

❌ Embedding an entire PDF instead of chunking it.

❌ Assuming indexing happens for every user query.

---

# Quick Revision (30 Seconds)

✅ LangChain provides reusable AI components.

✅ Document = Text + Metadata.

✅ Document Loader converts external files into Documents.

✅ Chat Model generates answers.

✅ ChatPromptTemplate creates chat messages.

✅ Embedding Model converts text into vectors.

✅ Vector Store stores embeddings.

✅ Retriever fetches relevant Documents.

✅ Indexing = Load → Split → Embed → Store.

---

# Day 5 Summary

```text
                    OFFLINE

PDF
 │
 ▼
Loader
 │
 ▼
Documents
 │
 ▼
Text Splitter
 │
 ▼
Chunks
 │
 ▼
Embedding Model
 │
 ▼
Vector Store

(Output: Searchable Knowledge Base)
```

> **Next (Day 6):**
>
> We use this indexed knowledge base to build a complete RAG application using Retrievers, LCEL, RAG Chains, Streaming, Message History, and History-Aware Retrieval.
