Sentence Embeddings:

Are dense vector representations of sentences, capturing their semantic meaning.
Dimension size (e.g., 384 for all-MiniLM-L6-v2) indicates the complexity of the semantic space.
Generated using pre-trained sentence-transformers models (e.g., all-MiniLM-L6-v2, all-mpnet-base-v2).
Cosine Similarity:

Measures the angle between two vectors.
Range: -1 (opposite) to 1 (identical direction).
Focus: Direction/orientation of vectors; insensitive to magnitude.
Best for: Semantic similarity – identifying sentences with similar meaning.
Euclidean Distance:

Measures the straight-line distance between two points in space.
Range: 0 (identical) to higher positive values (less similar).
Focus: Absolute position and magnitude of vectors.
Best for: Identifying how 'far apart' sentence meanings are.
Relationship between Cosine Similarity & Euclidean Distance:

For normalized embeddings (vectors with length 1, common in sentence-transformers models), maximizing cosine similarity is mathematically equivalent to minimizing Euclidean distance.
This is why their rankings for similarity often appear very similar or identical.
Comparing Models (all-MiniLM-L6-v2 vs. all-mpnet-base-v2):

all-MiniLM-L6-v2: Smaller, faster, efficient, good for resource-constrained environments.
all-mpnet-base-v2: Larger, generally more accurate, based on MPNet architecture, but slower and more computationally intensive.
Differences arise from: Unique architectures, training data, and learning objectives.
Impact: Can lead to variations in absolute similarity/distance scores and slight shifts in relative rankings, even if top similar sentences remain consistent.
Widely Used Models:

Sentence-BERT (SBERT): Framework for fine-tuning BERT-like models (e.g., MiniLM, MPNet).
Universal Sentence Encoder (USE): Google's general-purpose sentence encoder.
Other options: GloVe/Word2Vec (with pooling), InferSent, GTE models.
Choosing a model: Depends on desired performance, speed/efficiency, domain specificity, and language support.
