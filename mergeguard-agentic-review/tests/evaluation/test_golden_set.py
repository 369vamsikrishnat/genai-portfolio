from mergeguard.evaluation.scoring import GoldenPRSet, evaluate_verdict_precision


def test_golden_pr_set_tracks_expected_verdicts():
    suite = GoldenPRSet()
    suite.add_example(
        pr_id="PR#101",
        expected_verdict="MERGE",
        notes="small docs change",
    )
    suite.add_example(
        pr_id="PR#102",
        expected_verdict="BLOCK",
        notes="security issue",
    )

    assert suite.examples[0]["expected_verdict"] == "MERGE"
    assert suite.examples[1]["expected_verdict"] == "BLOCK"


def test_evaluate_verdict_precision_returns_percent():
    predictions = {
        "PR#101": "MERGE",
        "PR#102": "BLOCK",
        "PR#103": "MERGE",
    }
    expected = {
        "PR#101": "MERGE",
        "PR#102": "MERGE",
        "PR#103": "BLOCK",
    }

    precision = evaluate_verdict_precision(predictions, expected)

    assert precision == 33.33
