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
