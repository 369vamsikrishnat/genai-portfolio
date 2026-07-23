# Day 7 - Prompt Engineering (Anthropic)

> Goal: Learn how to write clear, reliable prompts.

## Table of Contents
1. What is Prompt Engineering?
2. System Prompts
3. Giving Context
4. Being Specific
5. Structured Output
6. Tell the Model What NOT to Do
7. Few-Shot Prompting
8. Prompt Chaining
9. XML Tags
10. Production Prompt Template
11. Common Mistakes
12. Interview Questions
13. 30-Second Revision

---

## 1. What is Prompt Engineering?
Prompt engineering is the practice of designing instructions so an LLM clearly understands its role, context, task, output format, and constraints.

**Mental Model:** Treat the model like a highly capable new teammate.

---

## 2. System Prompts
A system prompt defines the model's role, behavior, and boundaries.

Example:
```
You are a Senior AI Engineer.
Explain clearly.
Prefer production-ready code.
Never invent APIs.
```

Flow:
```
System Prompt -> User Prompt -> Model -> Response
```

---

## 3. Giving Context
Context reduces ambiguity.

Poor: `Write an email.`

Better:
```
Audience: Engineering Manager
Purpose: Request extension
Tone: Professional
Length: 150 words
```

---

## 4. Being Specific
Formula:
```
Role + Context + Task + Constraints + Output Format
```

---

## 5. Structured Output
Ask for Markdown, JSON, tables, or another fixed format.

Example:
```
## Summary
## Risks
## Recommendations
```

---

## 6. Tell the Model What NOT to Do
Example:
```
Do NOT:
- Invent facts
- Change numbers
- Add opinions
```

---

## 7. Few-Shot Prompting
Teach with examples before asking for a new task.

Zero-shot: instructions only.
One-shot: one example.
Few-shot: multiple examples.

---

## 8. Prompt Chaining
Break a complex task into smaller prompts.

```
Document
 -> Summary
 -> Risks
 -> Recommendations
 -> Presentation
```

---

## 9. XML Tags
Use XML to organize long prompts.

```xml
<role>Senior AI Engineer</role>
<context>Review this RAG system.</context>
<task>Find issues.</task>
```

---

## 10. Production Prompt Template
```
ROLE
CONTEXT
TASK
OUTPUT FORMAT
CONSTRAINTS
EXAMPLES (Optional)
INPUT
```

---

## 11. Common Mistakes
- Vague prompts
- Missing context
- No output format
- No constraints
- One huge prompt

---

## 12. Interview Questions
- What is a system prompt?
- Why is context important?
- What is few-shot prompting?
- Why use structured output?
- Why use prompt chaining?

---

## 13. 30-Second Revision
- Use a system prompt.
- Provide context.
- Be specific.
- Request structured output.
- State constraints.
- Use examples.
- Chain complex tasks.
- Use XML for long prompts.
