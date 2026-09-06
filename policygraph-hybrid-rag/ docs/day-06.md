# DAY 6 — Citation-Grounded Generation

## Objective

Build a generation layer that answers questions using only retrieved documents, provides citations, and avoids hallucinating information that is not present in the documents.

---

## Hour 1 — Understand Faithfulness

### What is Faithfulness?

Faithfulness measures whether the generated answer is supported by the information available in the retrieved documents.

In a RAG system, retrieval alone is not enough. The LLM must generate an answer based only on the retrieved evidence.

### Why is it important?

Without grounding, an LLM may generate information from its own knowledge or invent unsupported information.

For a policy/document QA system, this can produce incorrect answers and undermine the reliability of the system.

### Key concept

If the required information cannot be found in the retrieved documents, the system should not invent an answer.

Instead, it should return:

```text
NOT_IN_DOCUMENTS
```

---

# Hours 2–3 — Build Citation-Grounded Generator

## File Created

```text
src/generation/generator.py
```

The generator receives:

```text
question
documents
client
```

and generates an answer using the supplied documents.

---

## Grounded Prompt

The prompt instructs the LLM to:

1. Use only the provided documents.
2. Avoid outside knowledge.
3. Support factual claims with citations.
4. Return `NOT_IN_DOCUMENTS` when the information is unavailable.
5. Never invent unsupported facts.

The documents are provided to the model as context:

```text
[Document 1]
...

[Document 2]
...
```

The question is then supplied after the document context.

---

## Gemini Integration

Gemini was connected using the Google GenAI client.

The generator uses the same function:

```python
generate(question, documents, client)
```

This keeps the generation function independent of which client is supplied.

Gemini was used for the interactive/single-request generation path.

---

# Testing the Generator

## Test 1 — Answerable Question

### Question

```text
Is flood damage covered?
```

### Document

```text
Section 2: Flood Protection
Clause 2(a): Flood Damage
Flood damage to the insured residential property is covered
when flood protection has been included in the policy.
```

### Result

```text
Flood damage to the insured residential property is covered when flood protection has been included in the policy [Document 1, Clause 2(a)].
```

### Result

**PASS ✅**

The model answered using the document and included a citation.

---

# Test 2 — Unanswerable Question

### Question

```text
What is the maximum age of the policyholder?
```

The supplied document contained no information about the policyholder's age.

### Result

```text
NOT_IN_DOCUMENTS
```

### Result

**PASS ✅**

The model did not invent an answer.

---

# Test 3 — Partially Answerable Question

### Question

```text
Is flood damage covered, and what is the maximum payout?
```

The document contained information about flood coverage but contained no information about the maximum payout.

### Result

```text
Flood damage to the insured residential property is covered when flood protection has been included in the policy [Document 1, Clause 2(a)].

Information regarding the maximum payout is not provided in the documents.
```

### Result

**PASS ✅**

The model answered the supported portion and did not invent the missing payout information.

---

# Full Pipeline Integration

The generator was also connected to the existing RAG pipeline:

```text
User Question
      ↓
Retrieval
      ↓
RRF Fusion
      ↓
Cross-Encoder Reranking
      ↓
Top Retrieved Documents
      ↓
Gemini Generator
      ↓
Grounded Answer + Citations
```

An integrated test was successfully executed for:

```text
What happens if property damage is intentional?
```

The system retrieved and reranked the relevant clauses and generated:

```text
If property damage is caused intentionally by the policyholder or by a person acting with the policyholder's knowledge or permission, it is not covered [Document 1, Clause 1(b); Document 2, Clause 4(a)].
```

This demonstrated that the retrieved and reranked documents were successfully passed into the generation layer.

---

# Two-Tier LLM Routing

The planned architecture uses two generation tiers:

### Interactive requests

Use Gemini.

```text
User Question
      ↓
Gemini API
      ↓
Answer
```

Gemini is suitable for interactive/single requests.

### Bulk requests

A local Ollama model can be used for bulk processing.

```text
Many Questions
      ↓
Local Ollama Model
      ↓
Answers
```

This avoids depending entirely on API request limits when processing many questions.

### Environment Note

The Ollama variant was **not implemented** because the current system does not support Ollama models.

The Gemini interactive generation path was successfully implemented and tested.

This was intentionally skipped rather than introducing another model/framework outside the current environment.

---

# Important Design Note

The current citation format identifies retrieved chunks by their position:

```text
[Document 1]
[Document 2]
```

Therefore, `Document 1` currently means the first document/chunk supplied to the generator.

It does not necessarily mean a separate policy file.

Source-aware citations such as:

```text
policy_1.txt
Section 4
Clause 4(a)
```

can be improved later.

For Day 6, the focus was on connecting the reranked documents to grounded generation, so the current citation design was intentionally left unchanged.

---

# Day 6 Checkpoint

## 1. Explain the Two-Tier LLM Routing Decision

Gemini can encounter API request/rate limits when many questions are sent at once.

Therefore:

* Gemini → interactive/single requests
* Ollama/local LLM → bulk requests

The local model can process bulk requests without depending on the Gemini API for every request.

---

## 2. When Should `NOT_IN_DOCUMENTS` Trigger?

`NOT_IN_DOCUMENTS` should trigger when the required information cannot be found in the retrieved documents.

The generator must not use its own outside knowledge to invent an answer.

For partially answerable questions, the generator should answer the supported portion and identify the unsupported portion instead of fabricating information.

---

**DAY 6 COMPLETE ✅**

The RAG pipeline now performs:

```text
Retrieve
   ↓
Fuse
   ↓
Rerank
   ↓
Generate from evidence
   ↓
Cite evidence
   ↓
Refuse unsupported information
```
