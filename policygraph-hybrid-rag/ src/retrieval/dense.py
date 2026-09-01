from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import psycopg2


# Models
mini_model = SentenceTransformer("all-MiniLM-L6-v2")
bge_model = SentenceTransformer("BAAI/bge-base-en-v1.5")

# Model selected for PostgreSQL vector storage
model = SentenceTransformer("BAAI/bge-base-en-v1.5")


# Test sentences
sentences = [
    "Flood damage to the insured residential property is covered under this policy.",
    "Fire damage caused by accidental ignition is covered subject to the policy limits.",
    "The policyholder must report property damage within thirty days.",
    "Water damage caused by a burst internal pipe may be covered.",
    "Earthquake damage is excluded unless additional earthquake coverage was purchased.",
    "The insurance policy covers theft of personal belongings after a documented burglary.",
    "Storm-related damage to the roof is covered under the property protection section.",
    "Flooding caused by external water sources is covered under the flood protection clause.",
    "Premium payments must be made before the coverage renewal date.",
    "Damage caused intentionally by the policyholder is not covered.",
]


# Query
query = "Does the insurance policy cover damage caused by flooding?"


# # --------------------------------------------------
# # Hour 3 - MiniLM vs BGE experiment
# # --------------------------------------------------

# mini_embeddings = mini_model.encode(sentences)
# mini_query_embedding = mini_model.encode(query)

# bge_embeddings = bge_model.encode(sentences)
# bge_query_embedding = bge_model.encode(query)


# mini_scores = cosine_similarity(
#     [mini_query_embedding],
#     mini_embeddings
# )[0]

# bge_scores = cosine_similarity(
#     [bge_query_embedding],
#     bge_embeddings
# )[0]


# print("MiniLM embedding shape:", mini_embeddings.shape)
# print("BGE embedding shape:", bge_embeddings.shape)


# print("\nMiniLM ranking:")
# for index in mini_scores.argsort()[::-1]:
#     print(f"{mini_scores[index]:.4f} - {sentences[index]}")


# print("\nBGE ranking:")
# for index in bge_scores.argsort()[::-1]:
#     print(f"{bge_scores[index]:.4f} - {sentences[index]}")


# --------------------------------------------------
# Hour 4 - Generate BGE embeddings for PostgreSQL
# --------------------------------------------------

embeddings = model.encode(sentences)

print("Database embeddings shape:", embeddings.shape)


# Generate query embedding
query_embedding = model.encode(query)

query_vector = "[" + ",".join(
    str(float(x)) for x in query_embedding
) + "]"


# --------------------------------------------------
# Connect to PostgreSQL
# --------------------------------------------------

connection = psycopg2.connect(
    host="localhost",
    port=5432,
    database="policygraph",
    user="postgres",
    password="postgres"
)

cursor = connection.cursor()


# --------------------------------------------------
# Store embeddings in PostgreSQL
# --------------------------------------------------

for sentence, embedding in zip(sentences, embeddings):

    vector = "[" + ",".join(
        str(float(x)) for x in embedding
    ) + "]"

    cursor.execute(
        """
        UPDATE document_chunks
        SET embedding = %s
        WHERE content = %s
        """,
        (vector, sentence)
    )


connection.commit()


# --------------------------------------------------
# Vector similarity search
# --------------------------------------------------

cursor.execute(
    """
    SELECT
        id,
        content,
        1 - (embedding <=> %s::vector) AS similarity
    FROM document_chunks
    WHERE embedding IS NOT NULL
    ORDER BY embedding <=> %s::vector
    LIMIT 5;
    """,
    (query_vector, query_vector)
)

rows = cursor.fetchall()


print("\nTop 5 results:")

for row in rows:
    print(f"{row[2]:.4f} - {row[1]}")


# --------------------------------------------------
# Close database connection
# --------------------------------------------------

cursor.close()
connection.close()
