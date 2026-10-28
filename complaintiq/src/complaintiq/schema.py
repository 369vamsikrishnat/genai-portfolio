"""CFPB bulk-file column names -> snake_case."""
COLUMN_MAP = {
    "Date received": "date_received",
    "Product": "product",
    "Sub-product": "sub_product",
    "Issue": "issue",
    "Sub-issue": "sub_issue",
    "Consumer complaint narrative": "narrative",
    "Company public response": "company_public_response",
    "Company": "company",
    "State": "state",
    "ZIP code": "zip3",
    "Tags": "tags",
    "Consumer consent provided?": "consent",
    "Submitted via": "submitted_via",
    "Date sent to company": "date_sent",
    "Company response to consumer": "company_response",
    "Timely response?": "timely",
    "Consumer disputed?": "disputed",
    "Complaint ID": "complaint_id",
}
MONETARY = "Closed with monetary relief"
