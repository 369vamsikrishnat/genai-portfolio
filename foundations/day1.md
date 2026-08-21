# Day 1 - Sentence Embeddings and Similarity Metrics

### Topic
Sentence Embeddings and Similarity Metrics

### Key Takeaways: Sentence Embeddings and Similarity Metrics

This section summarizes the core concepts explored regarding sentence embeddings, how to measure their similarity, and the characteristics of different models.

#### 1. What are Sentence Embeddings?
-   **Definition:** Numerical representations (vectors) of sentences that capture their semantic meaning.
-   **Dimensionality:** Each sentence is mapped to a high-dimensional space (e.g., 384 dimensions for `all-MiniLM-L6-v2`, 768 dimensions for `all-mpnet-base-v2`).
-   **Purpose:** Allows machines to process and understand the meaning and relationships between textual data.

#### 2. Similarity Metrics

##### a) Cosine Similarity
-   **Mechanism:** Measures the cosine of the angle between two embedding vectors.
-   **Range:** -1 (perfectly opposite) to 1 (perfectly identical direction). A score of 0 means orthogonal (no relationship).
-   **Interpretation:** Focuses purely on the **direction** of vectors, indicating semantic alignment regardless of vector magnitude.
-   **Use Case:** Ideal for finding semantically similar sentences.

##### b) Euclidean Distance
-   **Mechanism:** Measures the straight-line distance between the endpoints of two embedding vectors in the high-dimensional space.
-   **Range:** 0 (identical vectors) to larger positive values (less similar).
-   **Interpretation:** Considers both **direction and magnitude** of vectors. Smaller distance implies greater similarity.
-   **Use Case:** Useful for clustering or when absolute proximity in the embedding space is relevant.

##### c) Relationship between Cosine Similarity and Euclidean Distance
-   For **normalized embeddings** (vectors scaled to have a length of 1), maximizing cosine similarity is mathematically equivalent to minimizing Euclidean distance.
-   This often leads to very similar, if not identical, rankings when comparing sentences using these two metrics with normalized embeddings.

#### 3. Comparing Sentence Embedding Models

We explored two distinct `sentence-transformers` models:

##### a) `all-MiniLM-L6-v2`
-   **Characteristics:** Smaller, faster, and more resource-efficient.
-   **Best for:** Applications where computational speed and lower resource usage are critical, or for quick prototyping.

##### b) `all-mpnet-base-v2`
-   **Characteristics:** Larger, generally more robust and accurate, based on the MPNet architecture.
-   **Best for:** Tasks requiring higher semantic understanding and accuracy, where increased computational cost is acceptable.
-   **Differences in Output:** Different models learn different semantic spaces, leading to variations in absolute similarity scores and potentially slight shifts in relative rankings, even if top-ranked sentences remain consistent.

#### 4. Widely Used Sentence Embedding Models

-   **Sentence-BERT (SBERT) family:** Includes models like `MiniLM` (e.g., `all-MiniLM-L6-v2`), `MPNet` (e.g., `all-mpnet-base-v2`), and many others. These are fine-tuned BERT-like models for sentence-level embeddings.
-   **Universal Sentence Encoder (USE):** Developed by Google, known for its robustness.
-   **GloVe / Word2Vec (with pooling):** Older word embedding models that can be aggregated to form sentence embeddings, though less context-aware than SBERT/USE.
-   **InferSent:** Utilizes BiLSTMs with max-pooling.
-   **GTE (General-purpose Text Embeddings):** A newer generation of models demonstrating strong performance.

#### 5. Choosing the Right Model
-   **Accuracy vs. Speed:** A common trade-off; larger models often offer better accuracy but are slower.
-   **Resource Constraints:** Consider memory and processing power available.
-   **Task & Domain:** Some models perform better on specific tasks or domains.
-   **Language Support:** Ensure the model is trained on your target language(s).

#### 6. 'King minus Man plus Woman equals Queen' in Vector Space
-  This analogy refers to the idea that in a well-trained word embedding space, semantic relationships between words can be captured as consistent geometric relationships (vectors). 
-  If you take the vector for 'king', subtract the vector for 'man', and then add the vector for 'woman', the resulting vector will be very close to the vector for 'queen'.

It works because:

-  The vector king can be thought of as (royal) + (male).
-  The vector man can be thought of as (human) + (male).
-  The vector woman can be thought of as (human) + (female).
-  So, king - man essentially isolates the 'royalty' aspect and subtracts the 'male' aspect, potentially leaving a vector representing (royal - human).
-  When you then add woman (which contains (human) + (female)), you get something like (royal - human) + (human + female) = (royal + female), which is semantically very close to 'queen'.

This isn't an exact mathematical equation, but a demonstration that these models learn distributed representations where semantic properties are encoded in different directions or dimensions of the vector space.

---

### Practical Implementation

#### Generate Embeddings with `sentence-transformers`

First, we need to install the `sentence-transformers` library, which provides an easy way to compute dense vector representations for sentences, paragraphs, and images. Then, we will use a pre-trained model to convert your 10 sentences into embeddings and display the resulting vectors.

```python
from sentence_transformers import SentenceTransformer

# Define the sentences
sentences = [
    "This is an example sentence",
    "Each sentence is converted",
    "into a dense vector",
    "This is a test case",
    "Another example",
    "The quick brown fox jumps over the lazy dog",
    "Machine learning is fascinating",
    "Natural Language Processing is a key area of AI",
    "Embeddings help in understanding text semantics",
    "I enjoy coding in Python"
]

# Load a pre-trained sentence transformer model
# 'all-MiniLM-L6-v2' is a good general-purpose model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Generate embeddings for the sentences
sentence_embeddings = model.encode(sentences)

# Print the embeddings
print("Sentence Embeddings:")
for i, sentence in enumerate(sentences):
    print(f"Sentence: '{sentence}'")
    print(f"Embedding: {sentence_embeddings[i]}")
    print(f"Shape of embedding: {sentence_embeddings[i].shape}\n")
```

#### Ranking Sentences by Cosine Similarity

```python
from sklearn.metrics.pairwise import cosine_similarity

# Get the embedding for the first sentence
first_sentence_embedding = sentence_embeddings[0].reshape(1, -1)

# Calculate cosine similarity between the first sentence and all other sentences
similarities = cosine_similarity(first_sentence_embedding, sentence_embeddings)

# Create a list of (similarity_score, sentence_index, sentence_text) tuples
# We exclude the first sentence itself from the ranking (it will have a similarity of 1.0)
sentence_similarity_scores = []
for i, score in enumerate(similarities[0]):
    if i == 0:  # Skip the similarity of the sentence with itself
        continue
    sentence_similarity_scores.append((score, i, sentences[i]))

# Sort the sentences by similarity score in descending order
sentence_similarity_scores.sort(key=lambda x: x[0], reverse=True)

print(f"Reference sentence: '{sentences[0]}'\n")
print("Ranked sentences by cosine similarity:")
for score, idx, text in sentence_similarity_scores:
    print(f"- Sentence {idx + 1}: '{text}' (Similarity: {score:.4f})")
```

#### Ranking Sentences by Euclidean Distance

```python
from sklearn.metrics.pairwise import euclidean_distances

# Get the embedding for the first sentence
first_sentence_embedding = sentence_embeddings[0].reshape(1, -1)

# Calculate Euclidean distance between the first sentence and all other sentences
distances = euclidean_distances(first_sentence_embedding, sentence_embeddings)

# Create a list of (distance_score, sentence_index, sentence_text) tuples
# We exclude the first sentence itself from the ranking (it will have a distance of 0.0)
sentence_distance_scores = []
for i, score in enumerate(distances[0]):
    if i == 0:  # Skip the distance of the sentence with itself
        continue
    sentence_distance_scores.append((score, i, sentences[i]))

# Sort the sentences by distance score in ascending order (smaller distance = more similar)
sentence_distance_scores.sort(key=lambda x: x[0], reverse=False)

print(f"Reference sentence: '{sentences[0]}'\n")
print("Ranked sentences by Euclidean distance (smaller is more similar):")
for score, idx, text in sentence_distance_scores:
    print(f"- Sentence {idx + 1}: '{text}' (Distance: {score:.4f})")
```

#### Ranking Sentences by Cosine Similarity (all-mpnet-base-v2)

```python
# First, load the mpnet model
model_mpnet = SentenceTransformer('all-mpnet-base-v2')
sentence_embeddings_mpnet = model_mpnet.encode(sentences)

# Get the embedding for the first sentence from the new model
first_sentence_embedding_mpnet = sentence_embeddings_mpnet[0].reshape(1, -1)

# Calculate cosine similarity with the new embeddings
similarities_mpnet = cosine_similarity(first_sentence_embedding_mpnet, sentence_embeddings_mpnet)

# Create a list of (similarity_score, sentence_index, sentence_text) tuples
sentence_similarity_scores_mpnet = []
for i, score in enumerate(similarities_mpnet[0]):
    if i == 0:
        continue
    sentence_similarity_scores_mpnet.append((score, i, sentences[i]))

# Sort in descending order for similarity
sentence_similarity_scores_mpnet.sort(key=lambda x: x[0], reverse=True)

print(f"Reference sentence: '{sentences[0]}' (Model: all-mpnet-base-v2)\n")
print("Ranked sentences by cosine similarity (all-mpnet-base-v2):")
for score, idx, text in sentence_similarity_scores_mpnet:
    print(f"- Sentence {idx + 1}: '{text}' (Similarity: {score:.4f})")
```

#### Ranking Sentences by Euclidean Distance (all-mpnet-base-v2)

```python
# Calculate Euclidean distance with the new embeddings
distances_mpnet = euclidean_distances(first_sentence_embedding_mpnet, sentence_embeddings_mpnet)

# Create a list of (distance_score, sentence_index, sentence_text) tuples
sentence_distance_scores_mpnet = []
for i, score in enumerate(distances_mpnet[0]):
    if i == 0:
        continue
    sentence_distance_scores_mpnet.append((score, i, sentences[i]))

# Sort in ascending order for distance (smaller is more similar)
sentence_distance_scores_mpnet.sort(key=lambda x: x[0], reverse=False)

print(f"Reference sentence: '{sentences[0]}' (Model: all-mpnet-base-v2)\n")
print("Ranked sentences by Euclidean distance (smaller is more similar) (all-mpnet-base-v2):")
for score, idx, text in sentence_distance_scores_mpnet:
    print(f"- Sentence {idx + 1}: '{text}' (Distance: {score:.4f})")
```

---

### Reflection
- Gained a solid understanding of how embeddings work and why they're crucial for RAG systems
- Learned the differences between cosine similarity and Euclidean distance - cosine similarity is preferred for semantic search due to its focus on direction
- Understanding the trade-off between model size/speed vs. accuracy is important for choosing the right embedding model
- The similarity metrics learned here will be fundamental for implementing the retrieval component of RAG
- Practical code examples help bridge theory and implementation


