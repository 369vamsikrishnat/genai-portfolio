from complaintiq.pii import redact, redact_text, sql_redact_expr


def test_redacts_common_pii():
    t, c = redact("Call 415-555-0134 or jane.doe@example.com, SSN 123-45-6789, card 4111 1111 1111 1111.")
    assert "415-555-0134" not in t and "jane.doe@example.com" not in t
    assert "123-45-6789" not in t and "4111" not in t
    assert {"phone", "email", "ssn", "card"} <= set(c)


def test_plain_text_untouched():
    s = "The bank charged me a late fee on 2023 although I paid early."
    assert redact_text(s) == s


def test_sql_expression_shape():
    e = sql_redact_expr('"x"')
    assert e.count("regexp_replace") == 5 and "'g'" in e
