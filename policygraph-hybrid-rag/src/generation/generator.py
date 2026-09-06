from google import genai


MODEL_NAME = "gemini-3.7-flash"


def build_prompt(question, documents):
    context = "\n\n".join(
        f"[Document {i + 1}]\n{doc}"
        for i, doc in enumerate(documents)
    )

    return f"""
You are a document-grounded question answering system.

Answer the question using ONLY the information in the provided documents.

Rules:
1. Do not use outside knowledge.
2. Support every factual claim with a citation to the relevant document or clause.
3. If the entire question cannot be answered from the documents, return exactly:
NOT_IN_DOCUMENTS
4. If only part of a multi-part question can be answered:
   - Answer the part that is supported by the documents.
   - Clearly state that the unsupported part is not provided in the documents.
   - Do not guess, infer, or invent the missing information.
5. Do not invent or infer unsupported facts.

Documents:
{context}

Question:
{question}
"""


def generate(question, documents, client):
    prompt = build_prompt(question, documents)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text


if __name__ == "__main__":

    client = genai.Client()

    question = "Is flood damage covered, and what is the maximum payout?"

documents = ["""
Section 2: Flood Protection
Clause 2(a): Flood Damage
Flood damage to the insured residential property is covered
when flood protection has been included in the policy.
"""]

answer = generate(
        question=question,
        documents=documents,
        client=client
    )

print("\n=== GENERATED ANSWER ===\n")
print(answer)
