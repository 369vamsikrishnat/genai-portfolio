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

### Resources
- [Sentence Transformers Documentation](https://www.sbert.net/)
- [BERT Models for Embeddings](https://huggingface.co/sentence-transformers)
- [Understanding Cosine Similarity](https://en.wikipedia.org/wiki/Cosine_similarity)
- [Euclidean Distance in Machine Learning](https://scikit-learn.org/stable/modules/metrics.pairwise.html)

### Reflection
- Gained a solid understanding of how embeddings work and why they're crucial for RAG systems
- Learned the differences between cosine similarity and Euclidean distance - cosine similarity is preferred for semantic search due to its focus on direction
- Understanding the trade-off between model size/speed vs. accuracy is important for choosing the right embedding model
- The similarity metrics learned here will be fundamental for implementing the retrieval component of RAG

### Next Steps
- [ ] Implement embedding generation using `sentence-transformers`
- [ ] Test similarity calculations with sample sentences
- [ ] Explore vector storage solutions (FAISS, Pinecone)
- [ ] Benchmark different embedding models on sample data
- [ ] Integrate embeddings into RAG pipeline
