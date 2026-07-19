# Day 6 - LangChain Query Pipeline

> **Goal:** Understand how an indexed knowledge base is queried to generate answers using RAG.

## Table of Contents
1. RAG Pipeline
2. RAG Chain
3. `format_docs()`
4. Runnable Interface
5. LCEL
6. RunnableLambda
7. RunnablePassthrough
8. Parallel Inputs
9. Streaming
10. Message History
11. Conversational RAG
12. History-Aware Retriever
13. Production Architecture
14. Interview Questions
15. Common Mistakes
16. Quick Revision

---

# 1. RAG Pipeline

## Definition
Retrieval-Augmented Generation (RAG) combines retrieval from an external knowledge base with text generation from an LLM.

```text
User Question
      │
      ▼
Retriever
      │
      ▼
Relevant Documents
      │
      ▼
Prompt Template
      │
      ▼
Chat Model
      │
      ▼
Answer
```

The retriever finds knowledge; the LLM writes the answer.

---

# 2. RAG Chain

A RAG Chain connects multiple LangChain components into one pipeline.

Manual flow:

```python
docs = retriever.invoke(question)
context = "\n\n".join(doc.page_content for doc in docs)
messages = prompt.invoke({"context": context, "question": question})
response = llm.invoke(messages)
print(response.content)
```

---

# 3. format_docs()

Retrievers return `Document` objects, but LLMs need text.

```python
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)
```

Flow:

```text
Documents
   │
   ▼
format_docs()
   │
   ▼
Context String
```

---

# 4. Runnable Interface

Most LangChain components are **Runnables**.

Common methods:

| Method | Purpose |
|---|---|
| `invoke()` | Run once |
| `stream()` | Stream output |
| `astream()` | Async streaming |

Examples:

```python
llm.invoke(...)
prompt.invoke(...)
retriever.invoke(...)
```

---

# 5. LCEL (LangChain Expression Language)

LCEL lets you compose pipelines.

```python
chain = prompt | llm | StrOutputParser()
```

`|` passes the output of one runnable to the next.

```text
Input
 │
 ▼
Prompt
 │
 ▼
LLM
 │
 ▼
Parser
 │
 ▼
String
```

---

# 6. RunnableLambda

Wrap a normal Python function so it can be used in LCEL.

```python
from langchain_core.runnables import RunnableLambda

formatter = RunnableLambda(format_docs)
```

---

# 7. RunnablePassthrough

Passes input unchanged.

Useful when both the retriever and prompt need the original question.

```python
RunnablePassthrough()
```

---

# 8. Parallel Inputs

LCEL dictionaries execute branches in parallel.

```python
{
  "context": retriever | formatter,
  "question": RunnablePassthrough(),
}
```

Flow:

```text
Question
   ├──────────────┐
   ▼              ▼
Retriever   Passthrough
   │              │
format_docs()     │
   └──────┬───────┘
          ▼
{context, question}
```

---

# 9. Streaming

Without streaming:

```python
chain.invoke(question)
```

With streaming:

```python
for chunk in chain.stream(question):
    print(chunk)
```

Streaming improves user experience by returning chunks immediately.

---

# 10. Message History

Conversation history provides context for follow-up questions.

```text
Human
AI
Human
AI
Human
```

History is resent with each request; the model does not permanently remember.

---

# 11. Conversational RAG

Problem:

```text
User: Explain HNSW.
User: Why is it faster?
```

Retriever only sees:

```text
Why is it faster?
```

Poor search query.

Solution: rewrite to a standalone question.

```text
Why is HNSW faster?
```

---

# 12. History-Aware Retriever

Internally combines:

```text
Chat History
      │
      ▼
Question Rewriter (LLM)
      │
      ▼
Standalone Question
      │
      ▼
Retriever
      │
      ▼
Relevant Documents
```

The rewriting LLM **does not answer** the question.

---

# 13. Production Architecture

```text
                 OFFLINE

PDF
 │
 ▼
Loader
 │
 ▼
Splitter
 │
 ▼
Embeddings
 │
 ▼
Vector Store


                 ONLINE

Question
 │
 ▼
History-Aware Retriever
 │
 ▼
Relevant Documents
 │
 ▼
format_docs()
 │
 ▼
Prompt
 │
 ▼
Chat Model
 │
 ▼
StrOutputParser
 │
 ▼
Answer
```

---

# 14. Interview Questions

**What is a RAG Chain?**

A pipeline that retrieves documents and uses them as context for an LLM.

**Why use `format_docs()`?**

To convert `Document` objects into plain text.

**What is LCEL?**

A language for composing LangChain runnables with `|`.

**Why use RunnablePassthrough?**

To preserve the original user question.

**What is a History-Aware Retriever?**

A retriever that first rewrites follow-up questions into standalone questions before retrieval.

---

# 15. Common Mistakes

- Thinking retrievers generate answers.
- Forgetting to format retrieved documents.
- Confusing `invoke()` with `stream()`.
- Thinking chat history is sent directly to the retriever.
- Thinking the history-aware rewriter answers the question.

---

# 16. Quick Revision

- RAG = Retrieval + Generation
- Retriever → Documents
- format_docs() → Context string
- Prompt → Messages
- Chat Model → AIMessage
- Parser → String
- LCEL uses `|`
- RunnableLambda wraps Python functions
- RunnablePassthrough forwards input
- Streaming improves UX
- History-aware retrieval rewrites ambiguous questions

```text
Question
   │
   ▼
History-Aware Retriever
   │
   ▼
Documents
   │
   ▼
Prompt
   │
   ▼
LLM
   │
   ▼
Answer
```

