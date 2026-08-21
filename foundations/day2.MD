# Day 2 - Text Splitting & Chunking Strategies

### Topic
Text Splitting & Chunking Strategies for RAG Systems

### Why do we need Text Splitting?

Large Language Models (LLMs) have a context window limit, meaning they cannot process an entire large document at once. Therefore, documents must be split into smaller chunks before they are embedded or sent to the model.

A good chunking strategy should:
- Preserve the meaning and context.
- Avoid cutting sentences or ideas in half.
- Improve retrieval quality in RAG systems.
- Reduce hallucinations by providing complete context.

---

### Important Parameters

#### Chunk Size
- Number of characters or tokens in each chunk.
- Smaller chunks → More precise retrieval but may lose context.
- Larger chunks → Better context but may retrieve unnecessary information.

#### Chunk Overlap
- Number of characters/tokens shared between consecutive chunks.
- Helps preserve context between chunks.
- Prevents important information from being lost at chunk boundaries.

**Example:**

```
Chunk 1:
The capital of France is Paris.
It is famous for the Eiffel...

Chunk 2:
...famous for the Eiffel Tower.
Millions of tourists visit every year.
```

Without overlap, the connection between ideas may be lost.

---

## Five Levels of Text Splitting

### Level 1 – Character Text Splitter

The simplest chunking strategy.

The document is split into fixed-size chunks based purely on the number of characters.

**Example:**
```
Chunk Size = 500 characters
Overlap = 100 characters
```

**Advantages:**
- Very simple
- Fast
- Works for any text

**Disadvantages:**
- Can cut words in half.
- Can split sentences.
- Can split paragraphs.
- May lose semantic meaning.
- Lower retrieval quality.

**Strategy:**
Splits text into fixed-size character chunks with optional overlap.

**Best Used When:**
- Working with simple text files.
- Speed is more important than retrieval quality.
- Quick prototypes or small datasets.

**Avoid When:**
- Meaning and sentence boundaries need to be preserved.

This approach is usually not recommended for production RAG systems.

---

### Level 2 – Recursive Character Text Splitter

Instead of splitting blindly, Recursive Character Splitter tries multiple separators in order to preserve meaning.

**Typical separator order:**
```
Paragraphs ("\n\n")
    ↓
New Line ("\n")
    ↓
Sentence
    ↓
Space (" ")
    ↓
Character
```

It attempts to split using the largest separator possible while respecting the chunk size.

**If a paragraph is too large:**
- Split by sentences.

**If a sentence is too large:**
- Split by words.

**If a word is still too large:**
- Split by characters.

**Advantages:**
- Preserves paragraphs.
- Preserves sentences.
- Better semantic coherence.
- One of the most commonly used chunking strategies.

**Strategy:**
Recursively splits text using separators such as:
Paragraph (\n\n) → New Line (\n) → Space (" ") → Character.
This preserves the natural structure of the document.

**Best Used When:**
- General-purpose RAG applications.
- Most PDFs, text files, Word documents, and webpages.
- Default choice for LangChain projects.

**Why Use It:**
- Preserves sentences and paragraphs.
- Produces better retrieval than fixed-size chunking.

This is the default splitter used in many LangChain applications.

---

### Level 3 – Document-Specific Splitting

Different document types require different splitting strategies.

Instead of treating every document as plain text, split based on the document's structure.

**Strategy:**
Splits documents according to their structure instead of plain text.

#### Source Code

**Examples:**

**Python**
```python
class User:
    def login():
    def logout():
```

Split by:
- Classes
- Functions
- Methods
- Modules

**Java**

Split by:
- Packages
- Classes
- Methods
- Interfaces

This preserves logical code blocks.

#### Markdown Documents

Split by:
- `#` (Heading 1)
- `##` (Heading 2)
- `###` (Heading 3)

Headings naturally separate topics.

#### HTML

Split using HTML tags like:
- `<h1>`
- `<h2>`
- `<p>`
- `<div>`

This preserves the webpage structure.

#### PDF Documents

PDFs often contain:
- Tables
- Images
- Graphs
- Charts
- Text

These require specialized processing.

**Tables:**

Instead of extracting tables as plain text, use:
```
unstructured.partition.pdf
```

This converts tables into HTML.

**Why HTML?**
Modern LLMs understand HTML table structures much better than flattened text, leading to better reasoning over tabular data.

**Images inside PDFs:**

LLMs cannot directly understand images unless they are multimodal.

**Typical workflow:**
1. Extract the image from the PDF.
2. Convert the image into Base64.
3. Send it to a Vision-capable LLM (e.g., GPT-4 Vision or another multimodal model).
4. Generate a text summary or description of the image.
5. Store the generated summary along with the document.
6. During retrieval, the LLM reads the image summary instead of the raw image.

This allows RAG systems to retrieve information from images, diagrams, and charts.

**Best Used When:**
- Working with structured documents.
- Building production-grade RAG systems.
- Processing code repositories or technical documentation.

**Special Notes:**
- Convert PDF tables to HTML using unstructured.partition.pdf.
- Extract images and generate text summaries using a Vision LLM (e.g., GPT-4 Vision) after converting images to Base64.

---

### Level 4 – Semantic Chunking

Instead of splitting by characters or document structure, split based on meaning.

The idea is to keep semantically related information together.

**Example:**
```
Paragraph 1: Introduction to Machine Learning
Paragraph 2: Types of Machine Learning
Paragraph 3: Training Process
Paragraph 4: Neural Networks
```

Even if Paragraphs 2 and 3 exceed the chunk size, semantic chunking may keep them together because they discuss the same topic.

**Typical process:**
1. Generate embeddings for sentences.
2. Measure semantic similarity between adjacent sentences.
3. Group highly similar sentences into one chunk.
4. Start a new chunk when semantic similarity drops below a threshold.

**Strategy:**
Groups text based on semantic similarity (meaning) using embeddings instead of relying on fixed sizes or document separators.

**Best Used When:**
- High retrieval accuracy is required.
- Enterprise RAG systems.
- Knowledge bases.
- Research papers.
- Legal or medical documents.

**Why Use It:**
- Keeps related concepts together.
- Improves search relevance.

**Trade-off:**
- Slower because embeddings must be computed.

Often considered one of the best approaches for high-quality RAG systems.

---

### Level 5 – Agentic Chunking

The most advanced chunking strategy.

Instead of following predefined rules, an LLM or agent decides how to split the document.

The agent analyzes:
- Topics
- Context
- Relationships
- Importance
- Future retrieval needs

It determines where chunks should begin and end.

**The agent may also:**
- Merge related sections.
- Split overly large concepts.
- Generate summaries.
- Create hierarchical chunks.
- Add metadata or tags.

**Example:**

A research paper may be chunked into:
- Abstract
- Problem Statement
- Methodology
- Experiments
- Results
- Limitations
- Future Work

rather than fixed-size chunks.

**Strategy:**
Uses an LLM/AI agent to intelligently decide chunk boundaries based on context, topics, and future retrieval needs.

**Best Used When:**
- Complex documents.
- Multi-document knowledge bases.
- Enterprise AI assistants.
- High-end RAG systems where quality matters more than cost.

**Why Use It:**
- Produces the most meaningful chunks.
- Can summarize, merge, split, and add metadata automatically.

**Trade-off:**
- Highest cost and slowest preprocessing due to additional LLM calls.

---

## Comparison Table

| Level | Method | Advantages | Disadvantages |
|-------|--------|-----------|----------------|
| Level 1 | Character Splitter | Simple, fast | Breaks words and sentences |
| Level 2 | Recursive Character Splitter | Preserves structure, commonly used | Still based on syntax, not meaning |
| Level 3 | Document-Specific Splitter | Understands document format (code, PDF, HTML, Markdown) | Requires document-specific logic |
| Level 4 | Semantic Chunking | Preserves meaning and improves retrieval | More computationally expensive |
| Level 5 | Agentic Chunking | Intelligent, adaptive, highest-quality chunks | Slowest and most expensive |

---

## Quick Rule to Remember

| Strategy | Use When |
|----------|----------|
| Character Splitter | Simple prototype, speed matters |
| Recursive Character Splitter | Default choice for most RAG applications |
| Document-Specific Splitter | PDFs, code, HTML, Markdown, structured documents |
| Semantic Chunking | Need higher retrieval accuracy by preserving meaning |
| Agentic Chunking | Best possible quality for complex, enterprise-scale RAG systems |

---

## Interview Tip

If asked "Which chunking strategy would you choose?", a strong answer is:

1. **Recursive Character Splitter** for most applications because it's fast, preserves structure, and is the standard default.

2. **Document-Specific Splitter** when handling structured content like code or PDFs.

3. **Semantic or Agentic Chunking** when retrieval quality is more important than preprocessing cost.

---

## Key Takeaways

- Chunking is the process of dividing large documents into smaller pieces before embedding or passing them to an LLM.
- Chunk overlap helps preserve context across chunk boundaries.
- **Recursive Character Splitter** is the most commonly used default strategy in LangChain.
- Document-specific chunking uses the document's natural structure (e.g., functions, headings, tables) to create meaningful chunks.
- Semantic chunking groups text by meaning using embeddings rather than fixed rules.
- Agentic chunking leverages an LLM to intelligently decide chunk boundaries based on context and document structure.
- Choosing the right chunking strategy has a significant impact on retrieval accuracy, context preservation, and the overall performance of a RAG (Retrieval-Augmented Generation) system.

---

## Practical Implementation

### Setup and Installation

```python
# Install necessary libraries
!pip install pypdf langchain-text-splitters nltk

# Download NLTK data for sentence splitting
import nltk
nltk.download('punkt')
nltk.download('punkt_tab')

# Import libraries for PDF extraction and text splitting
from pypdf import PdfReader
import io
import os
from langchain_text_splitters import RecursiveCharacterTextSplitter, NLTKTextSplitter
```

### Extract Text from PDF

```python
# Specify the path to your uploaded PDF file
pdf_file_path = '/Vamsi_Krishna_T_Resume.pdf'

# Check if the PDF file exists before proceeding
if not os.path.exists(pdf_file_path):
    raise FileNotFoundError(f"PDF file not found at: {pdf_file_path}. Please upload the file and ensure the name is correct.")

# Function to extract text from the PDF
def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

# Extract text from the PDF
document_text = extract_text_from_pdf(pdf_file_path)

# Provide feedback on text extraction
if not document_text.strip():
    print("Warning: The PDF seems to contain no extractable text. Please ensure it's not an image-only PDF.")
else:
    print(f"Successfully extracted text from '{pdf_file_path}'. Total characters: {len(document_text)}")
    print("\n--- First 500 characters of extracted text ---")
    print(document_text[:500])
    print("------------------------------------------------")
```

### Strategy 1: Fixed-Size Chunking

```python
# Fixed-size chunks (500 chars, 50 overlap)
# Using RecursiveCharacterTextSplitter with an empty string as a separator 
# effectively forces fixed-size splitting at character level
# Use when: You need strict, consistent chunk sizes, regardless of linguistic structure. 
# Good for fixed-input models.

fixed_size_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    length_function=len,
    separators=[""],  # Force character-level splitting for strict fixed size
    is_separator_regex=False,
)
fixed_size_chunks_combined = fixed_size_splitter.split_text(document_text)

print(f"Fixed-size chunking produced {len(fixed_size_chunks_combined)} chunks.")
print("\n--- First 5 Fixed-Size Chunks ---")
for i, chunk in enumerate(fixed_size_chunks_combined[:5]):
    print(f"Chunk {i+1} (Length: {len(chunk)} chars):\n{chunk}\n---\n")
```

### Strategy 2: Sentence-Based Chunking

```python
# Sentence-based chunking
# NLTKTextSplitter inherently performs sentence-based splitting
# Use when: You want to maintain semantic completeness within chunks, 
# as sentences represent complete thoughts. Good for RAG where context is key.

sentence_splitter_combined = NLTKTextSplitter()
sentence_chunks_combined = sentence_splitter_combined.split_text(document_text)

print(f"Sentence-based chunking produced {len(sentence_chunks_combined)} chunks.")
print("\n--- First 5 Sentence-Based Chunks ---")
for i, chunk in enumerate(sentence_chunks_combined[:5]):
    print(f"Chunk {i+1} (Length: {len(chunk)} chars):\n{chunk}\n---\n")
```

### Strategy 3: Recursive Character Text Splitter (Hierarchical)

```python
# Recursive Character Text Splitter (200 chars, 20 overlap, with explicit hierarchical separators)
# This strategy tries to split on a list of characters, in order, from longest to shortest.
# It attempts to keep all paragraphs, then sentences, then words together as long as possible.
# Use when: You need a flexible approach that prioritizes structural integrity 
# (paragraphs, sentences) while still aiming for a target chunk size. 
# Balances strict size with linguistic awareness.

recursive_splitter_explicit_combined = RecursiveCharacterTextSplitter(
    chunk_size=200,
    chunk_overlap=20,
    length_function=len,
    separators=["\n\n", "\n", " ", ""],  # Explicitly define hierarchical separators
    is_separator_regex=False,
)
recursive_chunks_combined = recursive_splitter_explicit_combined.split_text(document_text)

print(f"RecursiveCharacterTextSplitter produced {len(recursive_chunks_combined)} chunks.")
print("\n--- First 5 RecursiveCharacterTextSplitter Chunks ---")
for i, chunk in enumerate(recursive_chunks_combined[:5]):
    print(f"Chunk {i+1} (Length: {len(chunk)} chars):\n{chunk}\n---\n")
```

### Comparison Summary

```python
print("\n--- Combined Chunking Results Summary ---")
print(f"Fixed-size chunking produced {len(fixed_size_chunks_combined)} chunks.")
print(f"Sentence-based chunking produced {len(sentence_chunks_combined)} chunks.")
print(f"RecursiveCharacterTextSplitter produced {len(recursive_chunks_combined)} chunks.")

print("\n--- Analysis ---")
print("Fixed-Size Chunks: Maintains consistent length (or close to it, given the overlap).")
print("  Observation: Often cuts through words or sentences to meet the character count.")
print("\nSentence-Based Chunks: Ends at sentence boundaries, leading to varying chunk lengths.")
print("  Observation: Each chunk typically ends at a sentence boundary.")
print("\nRecursiveCharacterTextSplitter: Splits based on hierarchical separators.")
print("  Observation: Respects structural breaks like paragraphs and sentences.")
```

### Key Implementation Insights

**Fixed-Size Chunking:**
- Maintains uniform chunk sizes
- May break words/sentences
- Fast processing
- Predictable output size

**Sentence-Based Chunking:**
- Respects sentence boundaries
- Variable chunk sizes
- Better semantic preservation
- Good for natural language

**Recursive Character Splitter:**
- Balances size constraints with structure
- Respects paragraph and sentence boundaries when possible
- Falls back to word/character splitting if needed
- Most versatile approach

---


### Reflection
- Understood that "one-size-fits-all" chunking doesn't work for RAG systems
- Learned that context preservation is critical for LLM performance
- Realized that the choice of chunking strategy directly impacts retrieval accuracy
- Recognized that semantic and agentic approaches represent the future of RAG systems
- Understood the trade-offs between speed (Character/Recursive splitters) and quality (Semantic/Agentic)
- Gained hands-on experience with practical implementation of different chunking strategies
- Recognized that PDF extraction requires careful handling of text, tables, and images

