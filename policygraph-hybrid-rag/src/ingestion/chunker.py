import re

PROMPT_INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"ignore all previous instructions",
    r"disregard previous instructions",
    r"disregard all previous instructions",
    r"system override",
]


def detect_prompt_injection(text):
    text_lower = text.lower()

    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text_lower):
            return True

    return False

def section_aware_split(text, doc_name):
    section_pattern = r"(?=Section\s+\d+)"
    clause_pattern = r"(?=Clause\s+\d+\([a-z]\))"

    sections = re.split(section_pattern, text)

    chunks = []

    for section in sections:
        section = section.strip()

        if not section:
            continue

        section_match = re.match(
            r"Section\s+(\d+):\s*(.+)",
            section
        )

        if not section_match:
            continue

        section_number = section_match.group(1)
        section_title = section_match.group(2).split("\n")[0]
        section_heading = f"Section {section_number}: {section_title}"

        clauses = re.split(clause_pattern, section)

        for clause in clauses:
            clause = clause.strip()

            if not clause or clause.startswith("Section "):
                continue

            chunks.append({
    "section_number": section_number,
    "section_title": section_title,
    "doc_name": doc_name,
    "page_number": 1,
    "content": f"{section_heading}\n\n{clause}",
    "prompt_injection": detect_prompt_injection(clause)
})
            

    return chunks

def fixed_size_split(text, chunk_size=200):
    return [
        text[i:i + chunk_size]
        for i in range(0, len(text), chunk_size)
    ]

if __name__ == "__main__":
    with open("data/synthetic_policies/policy_1.txt", "r", encoding="utf-8") as file:
        text = file.read()

    chunks = section_aware_split(text, "policy_1.txt")

    # your existing Clause 4(b) test
    print("\n=== SECTION-AWARE CHUNK ===")
    for chunk in chunks:
        if "Clause 4(b)" in chunk["content"]:
            print(chunk["content"])
            break

    # your existing fixed-size test
    fixed_chunks = fixed_size_split(text, chunk_size=200)

    print("\n=== FIXED-SIZE CHUNKS AROUND CLAUSE 4(b) ===")
    clause_start = text.find("Clause 4(b)")

    for i, chunk in enumerate(fixed_chunks):
        chunk_start = i * 200
        chunk_end = chunk_start + 200

        if chunk_start <= clause_start < chunk_end or (
            chunk_start < clause_start + 400 and chunk_end > clause_start
        ):
            print(f"\n--- Fixed Chunk {i + 1} ---")
            print(chunk)

    # prompt injection test MUST be here
    print("\n=== PROMPT INJECTION DETECTION ===")

    for chunk in chunks:
        if chunk["prompt_injection"]:
            print("PROMPT INJECTION DETECTED")
            print(chunk["content"])
