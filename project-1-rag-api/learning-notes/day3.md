# Day 3 -  LangChain

### Topic
LangChain Framework: Building LLM-Powered Applications

### What is LangChain?

**LangChain** is an open-source framework for developing applications powered by Large Language Models (LLMs).

**Key Characteristics:**
- Orchestrates components very effectively across different layers
- Enables maximum output with minimal code
- Concept of **chains** where you can string different components together into a single pipeline
- The beauty of chains is that the output of one component automatically acts as the input for another component
- **Model-agnostic framework**: If you want to shift from OpenAI to Google or another provider in the future, you don't have to change much code—it can be done with ease

**Current Applications Built with LangChain:**
- Knowledge assistants for companies
- Conversational chatbots
- AI agents (the focus is shifting towards building agents)

---

## LangChain Components

LangChain consists of 6 core components that work together to build powerful LLM applications:

### 1. Models

In LangChain, models are the core interfaces through which you interact with AI models.

**Types of Models:**

#### a) Language Models (LLM)
- **Interface:** Text in → Text out
- **Purpose:** Generate text responses based on prompts
- **Examples:** OpenAI GPT-4, Google PaLM, Cohere, Llama
- **Capability:** Reasoning, conversation, content generation

#### b) Embedding Models
- **Interface:** Text in → Vector out
- **Purpose:** Convert text into high-dimensional numerical representations (embeddings)
- **Use Cases:** Semantic search, similarity matching, document retrieval
- **Examples:** OpenAI Embeddings, Hugging Face sentence-transformers, Cohere Embeddings

**How to Find Available Models:**
- Visit [LangChain Documentation](https://python.langchain.com/)
- Check which LLM models can be interacted with
- Check which embedding models can be interacted with
- Explore supported providers (OpenAI, Google, Azure, Cohere, local models, etc.)

**Example Usage:**
```python
from langchain.llms import OpenAI
from langchain.embeddings import OpenAIEmbeddings

# Language Model
llm = OpenAI(temperature=0.7)
response = llm("What is machine learning?")

# Embedding Model
embeddings = OpenAIEmbeddings()
vector = embeddings.embed_query("machine learning")
```

---

### 2. Prompts

Prompts are basically inputs provided to LLMs. They are critical for controlling the behavior and output of language models.

#### a) Dynamic and Reusable Prompts (Prompt Templates)

**Concept:** Use templates with placeholders to create dynamic prompts

**Basic Example:**
```
Template: "Summarize {topic} in a {tone} tone"
Format: topic='Cricket', tone='fun'
Final Prompt: "Summarize Cricket in a fun tone"
```

**Benefits:**
- Reusability across different contexts
- Easy parameter substitution
- Consistency in prompt structure
- Maintainability

**Code Example:**
```python
from langchain.prompts import PromptTemplate

# Create a prompt template
prompt_template = PromptTemplate(
    input_variables=["topic", "tone"],
    template="Summarize {topic} in a {tone} tone"
)

# Format with specific values
final_prompt = prompt_template.format(topic="Cricket", tone="fun")
print(final_prompt)
# Output: "Summarize Cricket in a fun tone"
```

#### b) Role-Based Prompts (Chat Prompts)

**Concept:** Define different roles (system, user, assistant) for more structured conversations

**Common Roles:**
- **System Prompt:** Defines the behavior and role of the AI
- **User Prompt:** The actual user query or message
- **Assistant Prompt:** Previous responses (for conversation history)

**Example:**
```
System: "You are an experienced {profession}"
User: "Tell me about {topic}"

Format: profession="doctor", topic="viral fever"

Final:
System: "You are an experienced doctor"
User: "Tell me about viral fever"
```

**Code Example:**
```python
from langchain.prompts import ChatPromptTemplate

# Create a role-based chat prompt
chat_template = ChatPromptTemplate.from_messages([
    ("system", "You are an experienced {profession}"),
    ("user", "Tell me about {topic}")
])

# Format with specific values
messages = chat_template.format_messages(
    profession="doctor",
    topic="viral fever"
)
```

#### c) Few-Shot Prompting

**Concept:** Provide examples in the prompt to guide the model's behavior

**Structure:**
1. **Examples:** Add example input-output pairs
2. **Template:** Define the pattern for new inputs
3. **Few-Shot Prompt Template:** Combine examples with the template
4. **Final Implementation:** Use with the LLM

**Benefits:**
- Improves model accuracy without retraining
- Helps with in-context learning
- Guides the model to produce desired output format
- Useful for specific tasks or domains

**Example:**
```
Examples:
Input: "The movie was great!"
Output: Sentiment - Positive

Input: "I hated that experience"
Output: Sentiment - Negative

New Input: "This product is amazing"
Expected Output: Sentiment - Positive
```

**Code Example:**
```python
from langchain.prompts import FewShotPromptTemplate, PromptTemplate

# Define examples
examples = [
    {"text": "The movie was great!", "sentiment": "Positive"},
    {"text": "I hated that experience", "sentiment": "Negative"},
]

# Define the example template
example_prompt = PromptTemplate(
    input_variables=["text", "sentiment"],
    template="Text: {text}\nSentiment: {sentiment}"
)

# Create few-shot prompt
few_shot_prompt = FewShotPromptTemplate(
    examples=examples,
    example_prompt=example_prompt,
    suffix="Text: {text}\nSentiment:",
    input_variables=["text"]
)

# Use it
output = few_shot_prompt.format(text="This product is amazing")
```

---

### 3. Chains

Chains are used to build pipelines by connecting multiple components together in different patterns.

**Purpose:** Orchestrate complex workflows where outputs from one step feed into the next

#### a) Sequential Chains

**Concept:** Components execute one after another in a fixed order

**Example 1: Content Generation Chain**
```
Input: Topic
  ↓
[Step 1: Generate Title] → Title
  ↓
[Step 2: Write Introduction] → Introduction
  ↓
[Step 3: Create Body Content] → Full Content
  ↓
Output: Complete Article
```

**Example 2: Document Processing Chain**
```
Input: Raw Text
  ↓
[Step 1: Extract Key Info] → Key Points
  ↓
[Step 2: Summarize] → Summary
  ↓
[Step 3: Generate Questions] → Q&A
  ↓
Output: Processed Document
```

**Code Example:**
```python
from langchain.chains import SimpleSequentialChain, LLMChain

# Create sequential chain
chain = SimpleSequentialChain(
    chains=[
        LLMChain(llm=llm, prompt=title_prompt),
        LLMChain(llm=llm, prompt=content_prompt),
    ]
)

result = chain.run(topic="Machine Learning")
```

#### b) Parallel Chains

**Concept:** Multiple components execute simultaneously, then results are combined

**Example 1: Multi-Aspect Analysis**
```
Input: Product Review
  ├─ [Analysis 1: Sentiment] → Sentiment Score
  ├─ [Analysis 2: Key Features] → Features List
  └─ [Analysis 3: Recommendations] → Recommendations
Output: Combined Analysis Report
```

**Example 2: Document Enrichment**
```
Input: News Article
  ├─ [Extract: Summary] → Summary
  ├─ [Extract: Keywords] → Keywords
  ├─ [Extract: Category] → Category
  └─ [Extract: Sentiment] → Sentiment
Output: Enriched Article Data
```

**Benefits:**
- Faster execution (all branches run simultaneously)
- Comprehensive analysis from multiple perspectives
- Better resource utilization

#### c) Conditional Chains

**Concept:** Choose which component to execute based on conditions or routing logic

**Example 1: Support Ticket Routing**
```
Input: Support Ticket
  ↓
[Router: Analyze Category]
  ├─ IF Category == "Technical" → [Route to: Technical Support Chain]
  ├─ IF Category == "Billing" → [Route to: Billing Chain]
  └─ IF Category == "General" → [Route to: General Support Chain]
  ↓
Output: Category-Specific Response
```

**Example 2: Content Type Decision**
```
Input: User Query
  ↓
[Router: Determine Query Type]
  ├─ IF Type == "Question" → [Use: Q&A Chain]
  ├─ IF Type == "Story" → [Use: Narrative Chain]
  └─ IF Type == "Code" → [Use: Code Generation Chain]
  ↓
Output: Type-Specific Content
```

**Benefits:**
- Smart routing based on input characteristics
- Different processing for different scenarios
- More efficient resource usage
- Better output quality

---

### 4. Indexes

Indexes connect your application to external knowledge sources, enabling Retrieval-Augmented Generation (RAG).

**Purpose:** Enhance LLM capabilities with real-world data

**Components:**

#### a) Document Loaders
- Load documents from various sources (PDFs, websites, databases, APIs)
- Extract and normalize text

#### b) Text Splitter
- Break large documents into manageable chunks
- Preserve context with overlap

#### c) Vector Store
- Store embeddings of text chunks
- Enable semantic search

#### d) Retrievers
- Fetch relevant chunks based on query
- Return top-K similar documents

**Workflow: LLM + External Knowledge**
```
User Query
  ↓
[Retriever] → Fetch relevant documents
  ↓
[Context Augmentation] → Add retrieved docs to prompt
  ↓
[LLM] → Generate response using context
  ↓
Answer (Based on External Knowledge)
```

**Benefits:**
- Access to real-time or domain-specific information
- Reduced hallucinations
- Factually accurate responses
- Up-to-date knowledge

**Code Example:**
```python
from langchain.document_loaders import PDFLoader
from langchain.text_splitters import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings

# 1. Load documents
loader = PDFLoader("document.pdf")
docs = loader.load()

# 2. Split text
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(docs)

# 3. Create embeddings and vector store
embeddings = OpenAIEmbeddings()
vector_store = FAISS.from_documents(chunks, embeddings)

# 4. Create retriever
retriever = vector_store.as_retriever()

# 5. Use in chain for RAG
result = retriever.get_relevant_documents("your query")
```

---

### 5. Memory

Memory enables LLMs to maintain context across multiple interactions. This is crucial because API calls to LLMs are stateless.

**Problem:** Without memory, each LLM call starts fresh with no knowledge of previous conversations

**Solution:** Store and manage conversation history

#### a) Conversation Buffer Memory

**Concept:** Stores a transcript of all recent messages

**Use Case:** Short conversations where complete history is needed

**Advantages:**
- Complete conversation history
- No loss of information
- Good for short chats

**Disadvantages:**
- Can grow large quickly
- High token usage over time
- Memory bloat for long conversations

**Example:**
```
Interaction 1: User: "Hello", Assistant: "Hi there!"
Interaction 2: User: "How are you?", Assistant: "I'm doing well"
Interaction 3: User: "Tell me a joke", Assistant: "Why did the chicken cross the road?"

Stored Memory: All 3 interactions (complete history)
```

#### b) Conversation Buffer Window Memory

**Concept:** Only keeps the last N interactions to avoid excessive token usage

**Use Case:** Long conversations where recent context matters most

**Advantages:**
- Bounded memory size
- Controlled token usage
- Efficient for long chats

**Disadvantages:**
- Loses older information
- May lose important context from earlier in conversation

**Example (Window Size = 2):**
```
Interaction 1: User: "Hello" (DROPPED - outside window)
Interaction 2: User: "How are you?", Assistant: "I'm doing well" (KEPT)
Interaction 3: User: "Tell me a joke", Assistant: "..." (KEPT)

Stored Memory: Only last 2 interactions
```

**Code Example:**
```python
from langchain.memory import ConversationBufferWindowMemory

memory = ConversationBufferWindowMemory(k=2)  # Keep last 2 interactions
memory.save_context({"input": "Hi"}, {"output": "Hello!"})
memory.save_context({"input": "How are you?"}, {"output": "I'm well"})
memory.save_context({"input": "Tell joke"}, {"output": "Why did..."})
```

#### c) Summarizer-Based Memory

**Concept:** Periodically summarizes older chat segments to keep a condensed memory footprint

**Use Case:** Very long conversations where complete history is important but storage is limited

**Advantages:**
- Condensed representation of older interactions
- Maintains important information
- Lower token usage than buffer
- Good for long-term conversations

**Disadvantages:**
- Summarization may lose nuances
- Requires LLM calls for summarization
- More complex implementation

**Example:**
```
Interactions 1-10: Summarized as "User discussed project requirements"
Interactions 11-20: Detailed conversation stored
Interactions 21-30: Detailed conversation stored

Stored Memory: Summary + Recent 20 interactions
```

#### d) Custom Memory

**Concept:** For advanced use cases, store specialized state in a custom memory class

**Use Cases:**
- Store specific user preferences
- Keep track of key facts about the user
- Maintain custom state variables
- Implement domain-specific context

**Example:**
```
Store:
- User Name: "John"
- User Role: "Manager"
- Department: "Engineering"
- Previous Purchases: ["Laptop", "Monitor"]
- Preferences: ["Fast Service", "Email Updates"]

This custom state is maintained separately from conversation history
```

**Code Example:**
```python
from langchain.memory import BaseMemory

class CustomMemory(BaseMemory):
    user_facts: dict = {}
    
    def save_fact(self, key: str, value: str):
        self.user_facts[key] = value
    
    def get_fact(self, key: str):
        return self.user_facts.get(key)

# Usage
memory = CustomMemory()
memory.save_fact("profession", "doctor")
memory.save_fact("expertise", "cardiology")
```

---

### 6. Agents

An AI agent is a chatbot with superpowers. While chatbots can only talk, agents can get work done.

**Key Difference:**
- **Chatbot:** Can only respond with text
- **Agent:** Can reason, plan, and execute actions

**Agent Characteristics:**
- **Reasoning Capabilities:** Break down complex problems
- **Tool Access:** Can use external tools and APIs
- **Decision Making:** Choose appropriate actions based on context
- **Autonomy:** Work towards goals without step-by-step instructions

#### Chain of Thought (CoT) Reasoning

**Concept:** Breaks the task into steps and reasons through it step by step

**Benefits:**
- Improved accuracy for complex problems
- Transparent reasoning process
- Better error handling
- More human-like problem solving

**Example: Customer Support Agent**
```
Customer Query: "I bought a laptop last month and it's not working"

Agent Reasoning (Chain of Thought):
Step 1: Identify the issue → Product malfunction
Step 2: Check warranty status → Need to verify purchase date
Step 3: Determine solution → Offer replacement or repair
Step 4: Execute action → Create support ticket
Step 5: Communicate → Send confirmation to customer

Agent Powers:
- Accesses customer database (Tool 1)
- Checks warranty system (Tool 2)
- Creates tickets in support system (Tool 3)
- Sends emails (Tool 4)
```

**Agent Architecture:**
```
User Request
  ↓
[Agent Reasoning Engine]
  ├─ Understand the task
  ├─ Break into subtasks
  ├─ Identify needed tools
  └─ Plan execution order
  ↓
[Tool Selection & Execution]
  ├─ Call API Tool 1
  ├─ Call Database Tool 2
  ├─ Call Processing Tool 3
  └─ Process results
  ↓
[Response Generation]
  └─ Synthesize findings
  ↓
Final Response with Action Taken
```

#### Agent Types

**1. Reactive Agents**
- Respond immediately to input
- No planning or memory
- Good for simple tasks

**2. Planning Agents**
- Create a plan before execution
- Can break down complex tasks
- Good for multi-step workflows

**3. Memory-Augmented Agents**
- Maintain context across interactions
- Learn from past actions
- Good for long-term tasks

---

## LangChain Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    LangChain Application                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐ │
│  │    Agents        │  │    Chains        │  │   Memory   │ │
│  │  (Smart Tools)   │  │  (Pipelines)     │  │ (Context)  │ │
│  └──────────────────┘  └──────────────────┘  └────────────┘ │
│           │                    │                     │        │
│           └────────────────────┼─────────────────────┘        │
│                                │                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │              Prompts & Messages                          ││
│  └──────────────────────────────────────────────────────────┘│
│           │                    │                     │        │
│           └────────────────────┼─────────────────────┘        │
│                                │                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │                    Models Layer                          ││
│  │  ┌──────────────┐          ┌──────────────┐            ││
│  │  │ Language     │          │  Embeddings  │            ││
│  │  │ Models (LLM) │          │  Models      │            ││
│  │  └──────────────┘          └──────────────┘            ││
│  └──────────────────────────────────────────────────────────┘│
│           │                                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Indexes (External Knowledge)              │ │
│  │  ┌─────────────┐  ┌─────────┐  ┌──────────────┐       │ │
│  │  │ Doc Loaders │  │ Splitter│  │ Vector Store │       │ │
│  │  └─────────────┘  └─────────┘  └──────────────┘       │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

### Resources
- [LangChain Official Documentation](https://python.langchain.com/)
- [YouTube Tutorial Series](https://www.youtube.com/watch?v=-xSJA8-o6Eg&list=PLKnIA16_RmvaTbihpo4MtzVm4XOQa0ER0&index=4)
- [LangChain GitHub Repository](https://github.com/langchain-ai/langchain)
- [LangChain Community](https://github.com/langchain-ai/langchain/discussions)

### Key Takeaways

- LangChain is a model-agnostic framework that simplifies LLM application development
- 6 core components work together: Models, Prompts, Chains, Indexes, Memory, and Agents
- Chains enable orchestration of complex workflows with minimal code
- Indexes enable RAG by connecting to external knowledge
- Memory enables stateful conversations
- Agents represent the next evolution from chatbots—they can reason and take action
- The framework allows easy switching between different LLM providers

### Reflection
- Understood how LangChain abstracts away LLM complexity
- Realized the power of composable components for building complex systems
- Appreciated the model-agnostic nature for future flexibility
- Recognized agents as the future of LLM applications
- Understood how memory management is critical for maintaining context

### Next Steps
- [ ] Set up LangChain locally
- [ ] Create first simple LLMChain with prompts
- [ ] Build a sequential chain with multiple steps
- [ ] Implement conversation buffer memory
- [ ] Create a simple Q&A chain with RAG
- [ ] Explore embedding models
- [ ] Build a custom agent with tools
- [ ] Experiment with different LLM providers (OpenAI, Google, etc.)
- [ ] Create role-based chatbot with system prompts
- [ ] Implement few-shot prompting for specific tasks
