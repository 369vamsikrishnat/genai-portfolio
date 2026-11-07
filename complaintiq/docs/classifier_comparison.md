# Classifier Comparison

## Evaluation setup

Both models use the same frozen temporal evaluation split:
- Training complaints: 100,000
- Test complaints: 229,940
- Cutoff: 2025-09-24
- Test-ID SHA256: `4bfc116b97595b9fbe9994ecac3b66d9926c6955907620c6f658f61b88f35b4a`
- Data: real CFPB complaints
- Label: product

## Results

| Metric | Hashing | MiniLM |
|---|---:|---:|
| Training rows | 100,000 | 100,000 |
| Test rows | 229,940 | 229,940 |
| Dimensions | 384 | 384 |
| Macro-F1 | 0.4909 | **0.6321** |

MiniLM improves macro-F1 by 0.1412 absolute, or approximately 28.8% relative to hashing.

## Interpretation

MiniLM provides substantially better classification performance on this frozen temporal test set. Both artifacts use identical test IDs and training sample sizes, making this a directly comparable evaluation.

The result supports selecting MiniLM as the stronger embedding-based classifier candidate. It does not establish production readiness; latency, resource consumption, calibration and operational costs must also be considered.

## Artifacts

- Hashing: `artifacts/complaintiq_frozen`
- MiniLM: `artifacts/complaintiq_full_minilm`

## Limitations

- This comparison covers macro-F1, not end-to-end service latency or operating cost.
- Confidence threshold selection must use validation data, not this temporal test set.
