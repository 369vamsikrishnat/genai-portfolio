from sentence_transformers import SentenceTransformer
import psycopg2

from src.ingestion.chunker import section_aware_split


# --------------------------------------------------
# BGE embedding model
# --------------------------------------------------

model = SentenceTransformer("BAAI/bge-base-en-v1.5")


# --------------------------------------------------
# Database connection
# --------------------------------------------------

def get_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="policygraph",
        user="postgres",
        password="postgres"
    )


# --------------------------------------------------
# Dense retrieval
# --------------------------------------------------

def dense_search(query, chunks, top_k=5):
    """
    Perform dense retrieval using BGE embeddings
    and PostgreSQL pgvector.

    Returns:
        List of (chunk, similarity_score) tuples.
    """

    query_embedding = model.encode(query)

    query_vector = "[" + ",".join(
        str(float(x)) for x in query_embedding
    ) + "]"

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            content,
            1 - (embedding <=> %s::vector) AS similarity
        FROM document_chunks
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
        """,
        (
            query_vector,
            query_vector,
            top_k
        )
    )

    rows = cursor.fetchall()

    cursor.close()
    connection.close()

    # Match database results back to the original chunks
    chunk_lookup = {
        chunk["content"]: chunk
        for chunk in chunks
    }

    results = []

    for content, similarity in rows:

        if content in chunk_lookup:

            results.append(
                (
                    chunk_lookup[content],
                    float(similarity)
                )
            )

    return results


# --------------------------------------------------
# Main - Dense retrieval test
# --------------------------------------------------

def main():

    # --------------------------------------------------
    # Load policy
    # --------------------------------------------------

    with open(
        "data/synthetic_policies/policy_1.txt",
        "r",
        encoding="utf-8"
    ) as file:
        text = file.read()

    # --------------------------------------------------
    # Create section-aware chunks
    # --------------------------------------------------

    chunks = section_aware_split(
        text,
        "policy_1.txt"
    )

    print(
        "Number of chunks:",
        len(chunks)
    )

    # --------------------------------------------------
    # Generate BGE embeddings
    # --------------------------------------------------

    contents = [
        chunk["content"]
        for chunk in chunks
    ]

    embeddings = model.encode(contents)

    print(
        "Chunk embeddings shape:",
        embeddings.shape
    )

    # --------------------------------------------------
    # Store chunks + embeddings in PostgreSQL
    # --------------------------------------------------

    connection = get_connection()
    cursor = connection.cursor()

    # Remove previous Day 1 test data
    cursor.execute(
        "DELETE FROM document_chunks"
    )

    # Insert actual section-aware chunks
    for chunk, embedding in zip(
        chunks,
        embeddings
    ):

        vector = "[" + ",".join(
            str(float(x))
            for x in embedding
        ) + "]"

        cursor.execute(
            """
            INSERT INTO document_chunks
            (
                document_name,
                section_number,
                section_title,
                page_number,
                document_type,
                content,
                embedding
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                "policy_1.txt",
                chunk["section_number"],
                chunk["section_title"],
                chunk["page_number"],
                "insurance",
                chunk["content"],
                vector
            )
        )

    connection.commit()

    cursor.close()
    connection.close()

    print(
        f"Stored {len(chunks)} chunks in PostgreSQL."
    )

    # --------------------------------------------------
    # Test dense retrieval
    # --------------------------------------------------

    query = (
        "Does the insurance policy cover "
        "damage caused by flooding?"
    )

    results = dense_search(
        query,
        chunks,
        top_k=5
    )

    print("\nTop 5 dense results:")

    for rank, (chunk, score) in enumerate(
        results,
        start=1
    ):

        print(
            f"\n{rank}. {score:.4f}"
        )

        print(
            chunk["content"]
        )


# --------------------------------------------------
# Run
# --------------------------------------------------

if __name__ == "__main__":
    main()
