import re


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

        clauses = re.split(clause_pattern, section)

        for clause in clauses:
            clause = clause.strip()

            if not clause:
                continue

            chunks.append({
                "section_number": section_number,
                "section_title": section_title,
                "doc_name": doc_name,
                "page_number": 1,
                "content": clause
            })

    return chunks
