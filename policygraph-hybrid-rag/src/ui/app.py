import os

import requests
import streamlit as st


st.set_page_config(
    page_title="PolicyGraph Hybrid RAG",
    page_icon="📄",
    layout="wide"
)


st.title("PolicyGraph Hybrid RAG")
st.write("Ask questions about your policy documents.")


# --------------------------------------------------
# Configuration
# --------------------------------------------------

API_URL = os.getenv(
    "API_URL",
    "http://127.0.0.1:8000"
)

API_KEY = os.getenv(
    "API_KEY",
    ""
)


# --------------------------------------------------
# Query
# --------------------------------------------------

question = st.text_input(
    "Ask a question",
    placeholder="What is the coverage for flood damage?"
)


if st.button("Query"):

    if not question.strip():
        st.warning("Please enter a question.")

    else:

        headers = {
            "X-API-Key": API_KEY
        }

        payload = {
            "question": question
        }

        try:

            response = requests.post(
                f"{API_URL}/query",
                json=payload,
                headers=headers,
                timeout=120
            )

            if response.status_code != 200:
                st.error(
                    f"API error: {response.status_code}"
                )

            else:

                result = response.json()

                # ------------------------------------------
                # Answer
                # ------------------------------------------

                st.subheader("Answer")

                st.write(
                    result["answer"]
                )

                # ------------------------------------------
                # Cost
                # ------------------------------------------

                st.subheader("Query information")

                cost = result["cost"]["query_cost"]

                st.metric(
                    "Query cost",
                    f"${cost:.6f}"
                )

                # ------------------------------------------
                # Confidence
                # ------------------------------------------

                citations = result.get(
                    "citations",
                    []
                )

                if citations:

                    scores = [
                        citation["score"]
                        for citation in citations
                    ]

                    confidence = (
                        sum(scores) / len(scores)
                    )

                    confidence = max(
                        0.0,
                        min(1.0, confidence)
                    )

                    st.subheader("Confidence")

                    st.progress(
                        confidence
                    )

                    st.caption(
                        f"{confidence:.1%}"
                    )

                # ------------------------------------------
                # Citations
                # ------------------------------------------

                st.subheader("Citations")

                for index, citation in enumerate(
                    citations,
                    start=1
                ):

                    with st.expander(
                        f"Source {index}"
                    ):

                        st.write(
                            citation["content"]
                        )

                        st.caption(
                            f"Score: {citation['score']:.4f}"
                        )

        except requests.RequestException as error:

            st.error(
                f"Could not connect to API: {error}"
            )