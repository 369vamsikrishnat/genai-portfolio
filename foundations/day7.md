# Day 7 - Prompt Engineering (Anthropic)

> **Goal:** Learn how to write production-quality prompts that generate reliable, consistent, and predictable outputs from Large Language Models (LLMs).

---

# Table of Contents

1. What is Prompt Engineering?
2. Prompt Lifecycle
3. Why Prompt Engineering Matters
4. System Prompts
5. Giving Context
6. Being Specific
7. Structured Output
8. Telling the Model What NOT To Do
9. Few-Shot Prompting
10. Prompt Chaining
11. XML Tags
12. Production Prompt Template
13. Best Practices
14. Interview Questions
15. Common Mistakes
16. 30-Second Revision

---

# 1. What is Prompt Engineering?

## Definition

Prompt Engineering is the process of designing clear and structured instructions that help a Large Language Model (LLM) produce accurate, relevant, and consistent responses.

A prompt is more than just asking a question.

It defines:

- The model's role
- The available context
- The task
- The expected output
- The constraints

The better the prompt, the better the response.

---

## Why Do We Need Prompt Engineering?

LLMs are trained to predict the next token based on the input they receive.

They **do not know what you actually want**.

They only know what your prompt tells them.

A vague prompt produces vague answers.

Example:

```
Explain AI.
```

The model has to guess:

- Beginner or expert?
- Short or long?
- Technical or non-technical?
- Examples or theory?

Now compare:

```
You are a Senior AI Engineer.

Explain Retrieval-Augmented Generation (RAG)
to a Python developer.

Include:

- Definition
- Architecture
- Advantages
- Limitations
- One real-world example

Limit the response to 300 words.
```

Now the model has almost no ambiguity.

---

## Mental Model

Think of an LLM as a **highly knowledgeable intern**.

The intern knows almost everything but cannot read your mind.

If you say:

```
Do the report.
```

You'll probably get something usable but not exactly what you wanted.

If you say:

```
Write a two-page executive summary
for the CEO using the attached financial report.

Focus only on revenue trends.

Do not discuss technical implementation.

Return Markdown.
```

The quality improves dramatically.

Prompt engineering is simply writing better specifications.

---

# Prompt Lifecycle

Every prompt follows a simple lifecycle.

```
User

↓

Prompt

↓

LLM

↓

Reasoning

↓

Generated Response
```

A better prompt provides better guidance during the model's reasoning process.

---

# Components of a Good Prompt

A production-quality prompt usually contains:

```
Role

↓

Context

↓

Task

↓

Output Format

↓

Constraints

↓

Examples (Optional)

↓

User Input
```

Each component reduces ambiguity.

---

# Benefits of Prompt Engineering

- More accurate responses
- Better consistency
- Less hallucination
- Easier automation
- Better structured outputs
- Lower development effort
- Easier debugging

---

# 2. System Prompts

## What is a System Prompt?

A System Prompt defines the model's **role**, **behavior**, and **boundaries** before the conversation begins.

It is the highest-priority instruction provided to the model.

Think of it as the model's permanent job description for the current conversation.

Example:

```text
You are a Senior AI Engineer.

Explain concepts clearly.

Prefer production-ready code.

If you are uncertain, say so.

Never invent APIs.
```

---

## Why Do We Need System Prompts?

Without a system prompt:

The model decides its own behavior.

With a system prompt:

The developer controls:

- Tone
- Style
- Level of detail
- Constraints
- Safety boundaries
- Domain expertise

This makes responses much more consistent.

---

## How System Prompts Work

```
System Prompt
      │
      ▼
User Prompt
      │
      ▼
LLM
      │
      ▼
Response
```

The system prompt is processed before the user's message and influences how the model interprets subsequent instructions.

---

## Real Example

System Prompt:

```text
You are an AI tutor.

Always explain concepts step by step.

Never skip intermediate reasoning.

Assume the student is a beginner.
```

User:

```text
Explain vector databases.
```

The response will naturally be beginner-friendly because the system prompt established the model's behavior.

---

## Good vs Bad System Prompt

### Bad

```text
Be helpful.
```

Problems:

- Too vague
- No role
- No constraints
- No audience

---

### Good

```text
You are a Senior Python Backend Engineer.

Explain concepts using production examples.

Prefer FastAPI code.

If information is uncertain, explicitly mention it.

Avoid unnecessary theory unless requested.
```

This gives the model a clear identity and expectations.

---

## Best Practices

✅ Clearly define the model's role.

✅ Specify the audience when relevant.

✅ Mention important constraints.

✅ State how uncertainty should be handled.

✅ Keep the instructions concise but specific.

---

## Common Mistakes

❌ Using generic instructions like "Be helpful."

❌ Giving contradictory instructions.

❌ Repeating the same instruction multiple times.

❌ Trying to solve the entire task inside the system prompt.

---

## Interview Questions

### Q1. What is a System Prompt?

**Answer:**

A System Prompt is the highest-priority instruction that defines the model's role, behavior, and constraints before user interaction begins.

---

### Q2. Why are System Prompts important?

**Answer:**

They provide consistent behavior across interactions, reducing ambiguity and making responses more reliable.

---

### Q3. Does the user message override the System Prompt?

**Answer:**

Not necessarily. The model follows the instruction hierarchy, where the system prompt generally has higher priority than user instructions unless there are reasons not to follow it.

---

# 30-Second Revision

Prompt engineering is the practice of writing structured instructions that help an LLM generate reliable and predictable outputs. A good prompt clearly defines the model's role, provides sufficient context, describes the task, specifies the expected output, and includes any necessary constraints. System prompts play a critical role by establishing the model's behavior for the entire conversation, making responses more consistent and aligned with the developer's goals.

---

# 3. Giving Context

## What is Context?

Context is the background information that helps the LLM understand **why** the task exists and **how** it should respond.

Without context, the model has to guess.

With context, the model can generate responses that are more accurate and relevant.

Think of context as giving the model enough information to understand the situation before asking it to perform a task.

---

## Why is Context Important?

Imagine asking someone:

```
Write an email.
```

Immediately several questions arise:

- Who is the recipient?
- What is the purpose?
- Formal or informal?
- Long or short?
- Friendly or professional?

The LLM faces the same ambiguity.

Now compare:

```
Write a professional email.

Audience:
Engineering Manager

Purpose:
Request a one-week extension for project delivery.

Reason:
Unexpected production issue.

Tone:
Professional and respectful.

Length:
Around 150 words.
```

This prompt leaves very little room for guessing.

---

## How Context Improves Responses

```
No Context

↓

Model makes assumptions

↓

Less accurate response
```

```
Rich Context

↓

Model understands the situation

↓

More accurate response
```

The more relevant context you provide, the fewer assumptions the model needs to make.

---

## Types of Context

### 1. Audience

Who is the response intended for?

Examples:

- Beginner
- Student
- Software Engineer
- CEO
- Customer

Example:

```
Explain RAG to a college student.
```

vs

```
Explain RAG to a Senior AI Engineer.
```

The explanation will be completely different.

---

### 2. Purpose

Why is this task being performed?

Example:

```
Summarize this document
for executive decision making.
```

This is different from:

```
Summarize this document
for exam preparation.
```

---

### 3. Background

Provide any important facts the model should know.

Example:

```
This application processes insurance claims.

OCR extracts document text.

LangChain is used for RAG.

Explain how the retrieval process works.
```

Now the model understands the application's domain.

---

### 4. Constraints

Context can also include restrictions.

Example:

```
Use Python.

Avoid third-party libraries.

Limit the answer to 200 words.
```

---

## Best Practices

✅ Include only relevant information.

✅ Specify the audience.

✅ Explain the purpose.

✅ Mention important background information.

✅ Avoid unnecessary details.

Too much irrelevant context can reduce response quality.

---

## Common Mistakes

❌ Assuming the model knows your project.

❌ Providing no audience.

❌ Mixing unrelated information.

❌ Giving excessive background that doesn't help the task.

---

## Interview Questions

### Q1. Why is context important in prompt engineering?

**Answer:**

Context reduces ambiguity by helping the model understand the situation, audience, and purpose of the task, leading to more relevant and accurate responses.

---

### Q2. Can too much context be harmful?

**Answer:**

Yes.

Large amounts of irrelevant information may distract the model and reduce the quality of the final response.

---

# 30-Second Revision

Context gives the model the background it needs to understand a task. Instead of forcing the model to make assumptions, developers provide information such as the audience, purpose, domain knowledge, and constraints. Good context improves accuracy, while unnecessary context can reduce response quality.

---

# 4. Being Specific

## Why Specificity Matters

LLMs are excellent at following instructions.

However, they cannot determine your expectations unless you explicitly state them.

The more specific the prompt, the more predictable the output.

---

## Poor Prompt

```
Explain AI.
```

Questions the model must guess:

- Beginner or expert?
- Long or short?
- Examples?
- Technical?
- History?
- Modern AI?

---

## Better Prompt

```
You are an AI Instructor.

Explain Retrieval-Augmented Generation (RAG)
to a Python developer.

Include:

- Definition
- Architecture
- One practical example
- Advantages
- Limitations

Use Markdown.

Limit to 300 words.
```

Notice how every ambiguity has been removed.

---

## The Prompt Formula

A good production prompt usually follows this structure:

```
Role

↓

Context

↓

Task

↓

Output Format

↓

Constraints

↓

Examples (Optional)
```

Example:

```
Role:
Senior AI Engineer

Context:
Teaching junior developers

Task:
Explain vector databases

Output:
Markdown

Constraints:
Maximum 500 words
```

This structure makes prompts easier to read, maintain, and debug.

---

## Specific Instructions vs Generic Instructions

### Generic

```
Write code.
```

### Better

```
Write a FastAPI endpoint
that accepts a PDF,
extracts text,
stores embeddings in Chroma,
and returns a success response.

Include comments.
```

The second prompt clearly defines the expected result.

---

## Why Specific Prompts Produce Better Results

Specific prompts:

- Reduce ambiguity
- Improve consistency
- Reduce hallucinations
- Produce reusable outputs
- Require fewer follow-up questions

---

## Best Practices

✅ Mention the desired role.

✅ Clearly describe the task.

✅ Specify the output format.

✅ Mention word limits when needed.

✅ Include examples if appropriate.

---

## Common Mistakes

❌ Assuming the model knows what you mean.

❌ Using vague instructions like "make it better."

❌ Forgetting output requirements.

❌ Combining multiple unrelated tasks into one prompt.

---

## Interview Questions

### Q1. Why are specific prompts better?

**Answer:**

Specific prompts reduce ambiguity and clearly communicate expectations, allowing the model to generate more accurate and consistent responses.

---

### Q2. What are the essential parts of a production-quality prompt?

**Answer:**

A production prompt typically includes a role, context, task, output format, constraints, and optional examples.

---

### Q3. How does specificity reduce hallucinations?

**Answer:**

By limiting the model's freedom to make assumptions, specific prompts guide the model toward the desired response and reduce opportunities to generate incorrect or irrelevant information.

---

# 30-Second Revision

Specificity is one of the most important principles of prompt engineering. Instead of asking broad questions, clearly define the role, context, task, expected output, and constraints. The fewer assumptions the model has to make, the more reliable and consistent the response becomes.
---

# 5. Structured Output

## What is Structured Output?

Structured Output means explicitly telling the model **how the response should be formatted** instead of allowing it to decide.

Instead of only describing **what** you want, you also describe **how** you want it returned.

Think of it as defining the schema of the response.

---

## Why Do We Need Structured Output?

Imagine you're building a production AI application.

If the model returns a different format every time:

```
Response 1

Summary:
...

Response 2

Here's what I found...

Response 3

• Point 1
• Point 2
```

Your application becomes difficult to process.

Instead, request a fixed format.

Example:

```
Return the answer using:

## Summary

## Advantages

## Limitations

## Conclusion
```

Now every response follows the same structure.

---

## Benefits

Structured output provides:

- Consistent responses
- Easier parsing
- Better automation
- Predictable formatting
- Easier integration with applications

---

## Markdown Output

Example:

```
Explain RAG.

Return the answer using:

# Definition

# Architecture

# Advantages

# Limitations

# Conclusion
```

The response becomes much easier to read.

---

## JSON Output

Applications often require JSON.

Example Prompt

```text
Analyze the resume.

Return ONLY valid JSON.

{
  "name":"",
  "skills":[],
  "experience":"",
  "summary":""
}
```

Possible Response

```json
{
  "name":"John",
  "skills":[
      "Python",
      "LangChain"
  ],
  "experience":"3 Years",
  "summary":"AI Engineer..."
}
```

This format is much easier for backend applications to consume.

---

## Table Output

Sometimes tables communicate information better.

Example

```
Compare GPT and Claude.

Return as a table.
```

Response

| Feature | GPT | Claude |
|---------|-----|---------|
| Coding | Excellent | Excellent |
| Long Context | Good | Excellent |
| Reasoning | Excellent | Excellent |

---

## Why Production Systems Prefer Structured Output

Imagine building a Resume Screening Application.

Without structure:

```
The candidate has Python,
FastAPI,
and LangChain experience...
```

Every response is different.

Instead:

```json
{
 "skills":[],
 "experience":"",
 "education":""
}
```

Now your backend can parse the response automatically.

---

## Best Practices

✅ Specify the output format.

✅ Mention whether Markdown, JSON, XML, or a table is expected.

✅ For JSON, clearly define the schema.

✅ Tell the model if no extra text should be returned.

---

## Common Mistakes

❌ Asking for JSON but accepting additional explanations.

❌ Not defining the expected schema.

❌ Mixing Markdown and JSON unless required.

---

## Interview Questions

### Q1. What is Structured Output?

**Answer:**

Structured Output is the practice of explicitly defining how an LLM should format its response, such as Markdown, JSON, XML, or tables.

---

### Q2. Why is Structured Output important?

**Answer:**

It produces consistent and predictable responses, making them easier to parse, automate, and integrate into applications.

---

### Q3. When is JSON preferred?

**Answer:**

JSON is commonly used when the response needs to be processed programmatically by another application or API.

---

# 30-Second Revision

Structured Output ensures that LLM responses follow a predictable format instead of changing from one request to another. By requesting Markdown, JSON, XML, or tables, developers can create AI systems that are easier to automate, parse, and maintain.

---

# 6. Telling the Model What NOT To Do

## Why Negative Instructions Matter

Most people only tell the model **what to do**.

Production prompts also tell the model **what not to do**.

This reduces unwanted behavior.

---

## Example

Instead of:

```
Summarize this article.
```

Write:

```
Summarize this article.

Do NOT:

- Invent facts
- Change numbers
- Add opinions
- Omit important findings
```

The second prompt is much more reliable.

---

## Why This Works

LLMs try to satisfy the user's request.

If you only specify positive instructions,

```
Do X
```

the model still has many possible interpretations.

Negative instructions remove unwanted possibilities.

Think of them as guardrails.

---

## Positive vs Negative Instructions

Positive

```
Explain RAG.
```

Negative

```
Do NOT:

- Use technical jargon
- Assume prior knowledge
- Exceed 300 words
```

Together they create a much clearer specification.

---

## Common Negative Constraints

```
Do NOT hallucinate.

Do NOT fabricate citations.

Do NOT use deprecated APIs.

Do NOT modify input values.

Do NOT answer outside the provided context.

Do NOT include unnecessary explanations.

Return only JSON.
```

These constraints are extremely common in production AI systems.

---

## Example

Poor Prompt

```
Generate SQL.
```

Better Prompt

```
Generate PostgreSQL SQL.

Do NOT:

- Drop tables
- Delete records
- Modify schema
- Use vendor-specific syntax
```

The second version is significantly safer.

---

## Best Practices

✅ Clearly state forbidden actions.

✅ Keep constraints concise.

✅ Include safety requirements.

✅ Mention formatting restrictions.

---

## Common Mistakes

❌ Writing contradictory instructions.

Example

```
Be concise.

Explain every detail.
```

❌ Too many unnecessary restrictions.

❌ Forgetting important safety constraints.

---

## Interview Questions

### Q1. Why should prompts include negative instructions?

**Answer:**

Negative instructions reduce ambiguity by explicitly telling the model what behaviors to avoid, resulting in safer and more reliable outputs.

---

### Q2. Give some examples of negative constraints.

**Answer:**

- Do not hallucinate.
- Do not invent facts.
- Do not modify numbers.
- Do not use deprecated APIs.
- Return only JSON.

---

### Q3. Are negative instructions enough to eliminate hallucinations?

**Answer:**

No.

They reduce unwanted behavior but cannot completely eliminate hallucinations. Good context, clear tasks, and reliable retrieval are also important.

---

# 30-Second Revision

Good prompts specify both what the model should do and what it must avoid doing. Negative constraints act as guardrails, reducing hallucinations, improving consistency, and making AI systems safer for production use. Combined with clear positive instructions, they help produce reliable and predictable responses.
---

# 7. Few-Shot Prompting

## What is Few-Shot Prompting?

Few-shot prompting is a prompting technique where we provide the model with **a few examples** before asking it to perform a new task.

Instead of only describing the task, we **demonstrate the expected pattern**.

The model learns the pattern from the examples and applies it to the new input.

---

## Why Do We Need Few-Shot Prompting?

Sometimes instructions alone are not enough.

Example:

```
Classify the sentiment.

Input:
The movie was amazing.
```

The model may understand what you want, but different models might format their responses differently.

Instead, show examples.

```
Input: I love this product.
Output: Positive

Input: This is terrible.
Output: Negative

Input: The service was okay.
Output:
```

Now the model follows the same pattern.

---

# Types of Prompting

## Zero-Shot Prompting

No examples.

Only instructions.

Example:

```
Translate the following sentence to French.

Hello
```

---

## One-Shot Prompting

One example is provided.

```
English: Thank you
French: Merci

English: Hello
French:
```

---

## Few-Shot Prompting

Multiple examples are provided.

```
English: Hello
French: Bonjour

English: Thank you
French: Merci

English: Good Morning
French: Bonjour

English: Good Night
French:
```

The model now has enough examples to infer the expected pattern.

---

## How Few-Shot Prompting Works

```
Instructions

↓

Example 1

↓

Example 2

↓

Example 3

↓

New Input

↓

LLM

↓

Response
```

The examples act as demonstrations rather than rules.

---

## When Should You Use Few-Shot Prompting?

Few-shot prompting is useful when:

- The output format is difficult to describe.
- Consistency is important.
- Classification tasks.
- Text transformation.
- Information extraction.
- Style imitation.

---

## Advantages

- Better consistency
- Fewer formatting mistakes
- Reduced ambiguity
- Easier to teach output patterns
- Often improves accuracy

---

## Limitations

- Longer prompts consume more tokens.
- Too many examples increase cost.
- Poor examples teach poor behavior.
- Examples should closely match the target task.

---

## Best Practices

✅ Use high-quality examples.

✅ Keep examples consistent.

✅ Use representative inputs.

✅ Avoid contradictory examples.

---

## Interview Questions

### Q1. What is Few-Shot Prompting?

**Answer:**

Few-shot prompting is a technique where several input-output examples are included in the prompt to demonstrate the desired behavior before presenting the actual task.

---

### Q2. Difference between Zero-Shot and Few-Shot Prompting?

**Answer:**

Zero-shot uses only instructions, while few-shot provides multiple examples that teach the model the expected output pattern.

---

### Q3. Why does Few-Shot Prompting improve results?

**Answer:**

Examples reduce ambiguity by showing the model exactly how the response should look instead of relying only on written instructions.

---

# 30-Second Revision

Few-shot prompting improves model performance by teaching through examples instead of relying solely on instructions. By providing representative input-output pairs, developers can achieve more consistent formatting, better classification, and improved response quality.

---

# 8. Prompt Chaining

## What is Prompt Chaining?

Prompt Chaining is the practice of breaking a **large, complex task** into multiple smaller prompts.

Instead of asking the model to do everything in one request, each prompt performs one specific task.

The output of one prompt becomes the input for the next.

---

## Why Use Prompt Chaining?

Imagine asking:

```
Read this document,
summarize it,
identify risks,
suggest improvements,
generate presentation slides,
and write an executive email.
```

Although the model may complete the task, debugging errors becomes difficult.

Instead, split the workflow.

---

## Prompt Chaining Workflow

```
Document

↓

Summary

↓

Risk Analysis

↓

Recommendations

↓

Presentation

↓

Executive Email
```

Each step has a single responsibility.

---

## Benefits of Prompt Chaining

- Easier debugging
- Higher accuracy
- Better maintainability
- Reusable prompts
- Modular workflows
- Easier testing

---

## Example

### Prompt 1

```
Summarize the PDF.
```

↓

Output

```
Summary
```

---

### Prompt 2

```
Identify risks from this summary.
```

↓

Output

```
Risk List
```

---

### Prompt 3

```
Generate recommendations based on these risks.
```

↓

Output

```
Recommendations
```

Each prompt focuses on one task instead of many.

---

## Architecture

```
User Input

↓

Prompt 1

↓

Output 1

↓

Prompt 2

↓

Output 2

↓

Prompt 3

↓

Final Result
```

---

## Real-World Example (RAG)

```
User Question

↓

Retriever

↓

Relevant Documents

↓

Prompt

↓

LLM

↓

Answer
```

Even RAG is a form of prompt chaining because retrieval happens before generation.

---

## Prompt Chaining vs One Large Prompt

| One Large Prompt | Prompt Chaining |
|------------------|-----------------|
| Hard to debug | Easy to debug |
| Difficult to reuse | Highly reusable |
| Higher chance of mistakes | Better reliability |
| One failure affects everything | Failures are isolated |

---

## Best Practices

✅ Give each prompt a single responsibility.

✅ Keep outputs structured.

✅ Validate outputs before passing them to the next step.

✅ Reuse prompts whenever possible.

---

## Common Mistakes

❌ Trying to solve everything in one prompt.

❌ Passing unstructured outputs between prompts.

❌ Making every prompt dependent on unnecessary information.

---

## Interview Questions

### Q1. What is Prompt Chaining?

**Answer:**

Prompt chaining is the process of breaking a complex task into multiple smaller prompts, where the output of one prompt becomes the input to the next.

---

### Q2. Why is Prompt Chaining better than one large prompt?

**Answer:**

It improves modularity, debugging, maintainability, and often produces more reliable results because each prompt focuses on a single task.

---

### Q3. Give a real-world example of Prompt Chaining.

**Answer:**

A RAG system retrieves relevant documents, builds a prompt using those documents, sends the prompt to an LLM, and generates an answer. Each stage is part of a chained workflow.

---

# 30-Second Revision

Prompt chaining divides complex workflows into smaller, focused prompts. Instead of solving everything in one request, each prompt performs one task and passes its output to the next stage. This approach improves reliability, debugging, reusability, and is widely used in production AI systems such as RAG pipelines, agents, and workflow automation.
---

# 9. XML Tags

## What are XML Tags?

XML tags are used to separate different parts of a prompt into clearly defined sections.

Instead of writing one long paragraph, XML organizes information into logical blocks.

Anthropic strongly recommends XML tags for long and complex prompts because they make prompts easier for both humans and models to understand.

---

## Why Use XML Tags?

Without XML:

```text
You are an AI Engineer.
Review this RAG architecture.
Find performance issues.
Return Markdown.
Don't modify the architecture.
```

Everything is mixed together.

With XML:

```xml
<role>
You are a Senior AI Engineer.
</role>

<context>
Review the following RAG architecture.
</context>

<task>
Find performance bottlenecks.
</task>

<output>
Markdown
</output>

<constraints>
Do not modify the architecture.
</constraints>
```

Each section has a clear purpose.

---

## Advantages

- Improves readability
- Separates instructions clearly
- Reduces ambiguity
- Easier to maintain
- Better for long prompts
- Preferred in Claude documentation

---

## Common XML Sections

```xml
<role>

<context>

<task>

<instructions>

<constraints>

<examples>

<input>

<output>
```

You don't have to use every tag—only those that make sense for your task.

---

## Best Practices

- Use meaningful tag names.
- Keep each tag focused on one purpose.
- Avoid deeply nested tags unless necessary.
- Maintain a consistent structure across prompts.

---

## Interview Questions

### Q1. Why are XML tags used in prompt engineering?

**Answer:**

XML tags organize prompts into logical sections, making instructions clearer for both developers and language models.

---

### Q2. Are XML tags mandatory?

**Answer:**

No. They are optional, but they are highly recommended for long or complex prompts because they improve organization and readability.

---

# 30-Second Revision

XML tags organize prompts into structured sections such as role, context, task, constraints, and output. They improve readability, reduce ambiguity, and make complex prompts easier to maintain.

---

# 10. Production Prompt Template

A production-ready prompt should follow a consistent structure.

```text
ROLE
Who should the model act as?

↓

CONTEXT
What background information is needed?

↓

TASK
What exactly should the model do?

↓

OUTPUT FORMAT
Markdown, JSON, XML, Table, etc.

↓

CONSTRAINTS
What must the model avoid?

↓

EXAMPLES (Optional)
Provide demonstrations if needed.

↓

INPUT
Actual user data.
```

---

## Example

```text
ROLE

You are a Senior AI Engineer.

--------------------------------

CONTEXT

The application is a RAG-based chatbot for insurance claims.

--------------------------------

TASK

Answer the user's question using only the provided context.

--------------------------------

OUTPUT

Markdown.

--------------------------------

CONSTRAINTS

Do not invent facts.
If the answer isn't available, say:
"I don't have enough information."

--------------------------------

INPUT

<Retrieved Documents>

User Question:
How are claims validated?
```

This structure is easy to read, maintain, and reuse across applications.

---

# 11. Best Practices

## Always Define a Role

Bad

```text
Explain RAG.
```

Better

```text
You are a Senior AI Engineer.

Explain RAG.
```

---

## Provide Context

The model performs better when it understands the situation.

Include:

- Audience
- Goal
- Background
- Domain knowledge

---

## Be Specific

Avoid vague requests.

Instead of

```
Improve this.
```

write

```
Improve readability,
fix grammar,
keep the tone professional,
limit to 200 words.
```

---

## Request Structured Output

Instead of:

```
Summarize.
```

Use:

```
Return:

## Summary

## Risks

## Recommendations
```

---

## State Constraints

Examples:

```
Do not hallucinate.

Do not invent citations.

Return only JSON.

Do not modify input values.
```

---

## Use Examples

When describing the desired behavior is difficult, demonstrate it with one-shot or few-shot examples.

---

## Break Complex Tasks into Smaller Prompts

Use prompt chaining instead of asking the model to perform many unrelated tasks in one prompt.

---

# Common Mistakes

❌ Vague prompts

❌ Missing context

❌ No output format

❌ No constraints

❌ Contradictory instructions

❌ Trying to solve multiple unrelated tasks in one prompt

❌ Poor or inconsistent examples

---

# Interview Questions

## Q1. What is Prompt Engineering?

**Answer:**

Prompt engineering is the process of designing structured instructions that help an LLM generate accurate, consistent, and reliable responses.

---

## Q2. What is the purpose of a System Prompt?

**Answer:**

It defines the model's role, behavior, and constraints before user interaction begins, ensuring consistent responses.

---

## Q3. Why is context important?

**Answer:**

Context reduces ambiguity by providing the model with the background needed to understand the task.

---

## Q4. Why should prompts be specific?

**Answer:**

Specific prompts reduce assumptions, improve consistency, and produce more predictable outputs.

---

## Q5. Why is structured output useful?

**Answer:**

It produces consistent responses that are easier to read, parse, and integrate into applications.

---

## Q6. What is Few-Shot Prompting?

**Answer:**

Few-shot prompting teaches the model the expected behavior using multiple examples before presenting the actual task.

---

## Q7. What is Prompt Chaining?

**Answer:**

Prompt chaining breaks a complex task into multiple smaller prompts, where the output of one prompt becomes the input of the next.

---

## Q8. Why are XML tags recommended?

**Answer:**

They organize prompts into logical sections, improving readability, maintainability, and reducing ambiguity.

---

# Complete Mental Model

Think of Prompt Engineering as writing a **software specification** rather than asking a casual question.

Instead of hoping the model understands your intent, you explicitly define:

```
Role

↓

Context

↓

Task

↓

Output Format

↓

Constraints

↓

Examples

↓

Input

↓

LLM

↓

Structured Response
```

The fewer assumptions the model has to make, the more reliable and predictable the output becomes.

---

# Complete Day 7 Revision

Prompt engineering is the practice of designing structured instructions that guide a language model toward accurate and consistent responses. Effective prompts clearly define the model's role, provide sufficient context, describe the exact task, specify the desired output format, and include any necessary constraints. Techniques such as few-shot prompting, prompt chaining, structured outputs, and XML tags further improve reliability, maintainability, and production readiness. Instead of treating prompts as simple questions, developers should think of them as detailed specifications for an intelligent software component.

---

# Key Takeaways

- Prompt engineering is about reducing ambiguity.
- System prompts define long-term behavior.
- Context helps the model understand the situation.
- Specific prompts outperform vague prompts.
- Structured outputs make responses predictable.
- Negative constraints improve reliability.
- Few-shot prompting teaches through examples.
- Prompt chaining simplifies complex workflows.
- XML tags organize long prompts.
- Production prompts follow a consistent template.

---

# 30-Second Revision

Prompt engineering is the foundation of building reliable AI applications. A well-designed prompt clearly defines the model's role, provides relevant context, specifies the exact task, requests a structured output, and includes constraints that prevent unwanted behavior. Techniques like few-shot prompting, prompt chaining, and XML tags further improve consistency and maintainability. In production systems, prompts should be treated like software specifications—clear, structured, reusable, and easy to maintain.
