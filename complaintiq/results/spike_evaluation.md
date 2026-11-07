# Complaint spike detection: chronological CFPB backtest

No incident or independently reviewed alert labels are available. Alert counts are not true positives; false-alert rate, precision, recall, and detection latency cannot be measured.

Weekly grouped rows: 225,706; groups: 26,730; weeks: 124 (2024-04-01 to 2026-08-10).
Complaint records counted: 2,004,605; source: `F:\ai\genai-portfolio\complaintiq\data\processed\complaints`; filter: non-null date_received and non-null grouping keys.
Grouping: company, product, issue.

## Detector configuration

* Trailing baseline: 8 weeks; current week excluded.
* Minimum current count: 10; minimum prior baseline count: 20; minimum observed baseline weeks: 4.
* Multiple-testing correction: causal alpha spending: 0.05 / (historically-supported groups * week * (week + 1)).

## Observed alerts

* Alert count: **139**.
* Statistical severity buckets: {'low': 65, 'medium': 50, 'high': 24}. These describe alert magnitude only, not verified incident severity.
* Alerts by year: {'2024': 32, '2025': 92, '2026': 15}.
* False-alert count/rate: **not measurable** without independently labeled incidents.
* Detection latency: **not measurable** without incident onset labels; detector runtime for this historical scan was 7846.564 ms.

## Alert details

| Week | Company | Product | Issue | Count | Baseline mean | Baseline count | Lift | z | p-value | Severity |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| 2025-01-13 | Block, Inc. | Money transfer, virtual currency, or money service | Other transaction problem | 17417 | 3.12 | 25 | 5573.44 | 9850.78 | 0 | high |
| 2025-01-13 | CAPITAL ONE FINANCIAL CORPORATION | Checking or savings account | Managing an account | 3288 | 13.62 | 109 | 241.32 | 866.86 | 0 | high |
| 2025-01-13 | NAVY FEDERAL CREDIT UNION | Checking or savings account | Problem caused by your funds being low | 3908 | 16.38 | 131 | 238.66 | 584.91 | 0 | high |
| 2025-10-06 | Early Warning Services, LLC | Money transfer, virtual currency, or money service | Other transaction problem | 522 | 6.25 | 50 | 83.52 | 206.3 | 0 | high |
| 2025-01-13 | Early Warning Services, LLC | Money transfer, virtual currency, or money service | Fraud or scam | 364 | 6.12 | 49 | 59.43 | 58.85 | 6.75e-287 | high |
| 2025-01-13 | Block, Inc. | Money transfer, virtual currency, or money service | Unauthorized transactions or other transaction problem | 134 | 6.75 | 54 | 19.85 | 48.98 | 8.21e-84 | high |
| 2025-01-13 | Block, Inc. | Money transfer, virtual currency, or money service | Fraud or scam | 214 | 8.62 | 69 | 24.81 | 44.09 | 1.02e-141 | high |
| 2025-01-20 | Nelnet, Inc. | Student loan | Struggling to repay your loan | 68 | 4.0 | 32 | 17.0 | 29.93 | 2.72e-41 | high |
| 2025-01-13 | JPMORGAN CHASE & CO. | Money transfer, virtual currency, or money service | Other transaction problem | 74 | 3.88 | 31 | 19.1 | 29.02 | 1.53e-46 | high |
| 2025-03-10 | Nelnet, Inc. | Student loan | Improper use of your report | 85 | 4.75 | 38 | 17.89 | 24.77 | 4.54e-52 | high |
| 2025-01-13 | Early Warning Services, LLC | Credit reporting or other personal consumer reports | Improper use of your report | 35 | 3.38 | 27 | 10.37 | 17.21 | 3.59e-18 | high |
| 2025-01-13 | JPMORGAN CHASE & CO. | Money transfer, virtual currency, or money service | Fraud or scam | 69 | 8.38 | 67 | 8.24 | 16.38 | 2.66e-30 | high |
| 2025-01-13 | Block, Inc. | Checking or savings account | Managing an account | 68 | 9.75 | 78 | 6.97 | 16.29 | 4.99e-27 | high |
| 2025-01-13 | Experian Information Solutions Inc. | Credit reporting or other personal consumer reports | Problem with a company's investigation into an existing problem | 4128 | 939.38 | 7515 | 4.39 | 14.97 | 0 | medium |
| 2025-01-13 | Block, Inc. | Checking or savings account | Problem with a lender or other company charging your account | 34 | 2.5 | 20 | 13.6 | 13.89 | 7.63e-20 | high |
| 2026-02-16 | NAVY FEDERAL CREDIT UNION | Checking or savings account | Problem caused by your funds being low | 25 | 2.62 | 21 | 9.52 | 13.81 | 6.5e-13 | high |
| 2025-01-13 | CAPITAL ONE FINANCIAL CORPORATION | Credit card | Fees or interest | 51 | 9.25 | 74 | 5.51 | 13.73 | 1.28e-17 | high |
| 2025-01-13 | NAVY FEDERAL CREDIT UNION | Checking or savings account | Managing an account | 75 | 11.75 | 94 | 6.38 | 13.69 | 6.22e-28 | high |
| 2024-09-09 | Navient Solutions, LLC. | Student loan | Struggling to repay your loan | 34 | 4.88 | 39 | 6.97 | 13.19 | 2.43e-14 | high |
| 2025-01-13 | Block, Inc. | Checking or savings account | Closing an account | 23 | 2.5 | 20 | 9.2 | 12.97 | 8.29e-12 | high |
| 2025-03-10 | Nelnet, Inc. | Student loan | Dealing with your lender or servicer | 137 | 20.62 | 165 | 6.64 | 12.55 | 6.35e-51 | high |
| 2025-06-16 | TRANSUNION INTERMEDIATE HOLDINGS, INC. | Debt collection | False statements or representation | 35 | 6.12 | 49 | 5.71 | 11.67 | 6.39e-13 | high |
| 2025-01-13 | Block, Inc. | Money transfer, virtual currency, or money service | Managing, opening, or closing your mobile wallet account | 23 | 3.0 | 24 | 7.67 | 11.55 | 9.31e-11 | high |
| 2025-06-02 | Chime Financial Inc | Checking or savings account | Closing an account | 35 | 6.88 | 55 | 5.09 | 10.73 | 7.1e-12 | high |
| 2025-05-26 | CBC Companies, Inc. | Credit reporting or other personal consumer reports | Improper use of your report | 34 | 3.62 | 29 | 9.38 | 10.39 | 7.2e-17 | high |
| 2025-03-10 | EdFinancial Services | Student loan | Dealing with your lender or servicer | 58 | 10.0 | 80 | 5.8 | 9.86 | 1.45e-20 | medium |
| 2025-03-10 | Maximus Federal Services, Inc. | Student loan | Dealing with your lender or servicer | 66 | 12.25 | 98 | 5.39 | 9.78 | 6.52e-22 | medium |
| 2025-01-13 | AMERICAN EXPRESS COMPANY | Credit card | Trouble using your card | 26 | 3.12 | 25 | 8.32 | 9.71 | 1.69e-12 | medium |
| 2025-01-20 | MOHELA | Student loan | Struggling to repay your loan | 62 | 14.12 | 113 | 4.39 | 9.63 | 2e-17 | medium |
| 2025-01-13 | JPMORGAN CHASE & CO. | Checking or savings account | Problem caused by your funds being low | 24 | 4.25 | 34 | 5.65 | 9.58 | 2.86e-09 | medium |
| 2024-11-11 | NAVY FEDERAL CREDIT UNION | Checking or savings account | Problem caused by your funds being low | 241 | 9.88 | 79 | 24.41 | 9.51 | 1.29e-158 | medium |
| 2025-01-20 | Maximus Federal Services, Inc. | Student loan | Struggling to repay your loan | 24 | 2.75 | 22 | 8.73 | 9.44 | 6.1e-12 | medium |
| 2025-02-10 | Nelnet, Inc. | Credit reporting or other personal consumer reports | Improper use of your report | 32 | 4.38 | 35 | 7.31 | 9.29 | 5.59e-14 | medium |
| 2025-01-13 | BANK OF AMERICA, NATIONAL ASSOCIATION | Money transfer, virtual currency, or money service | Fraud or scam | 41 | 7.38 | 59 | 5.56 | 8.73 | 1.43e-14 | medium |
| 2025-03-10 | Servicer under contract with Federal Student Aid | Student loan | Improper use of your report | 28 | 2.5 | 20 | 11.2 | 8.71 | 2.27e-15 | medium |
| 2025-01-13 | JPMORGAN CHASE & CO. | Checking or savings account | Managing an account | 109 | 41.12 | 329 | 2.65 | 8.53 | 4.96e-16 | medium |
| 2025-01-27 | LEXISNEXIS | Credit reporting or other personal consumer reports | Incorrect information on your report | 82 | 26.12 | 209 | 3.14 | 8.25 | 1.1e-15 | medium |
| 2026-03-02 | TRANSWORLD SYSTEMS INC | Debt collection | Attempts to collect debt not owed | 39 | 11.12 | 89 | 3.51 | 8.2 | 2.38e-09 | medium |
| 2025-02-03 | FactorTrust, Inc. | Credit reporting or other personal consumer reports | Incorrect information on your report | 38 | 3.75 | 30 | 10.13 | 8.03 | 2.23e-19 | medium |
| 2025-01-13 | WELLS FARGO & COMPANY | Money transfer, virtual currency, or money service | Fraud or scam | 35 | 6.88 | 55 | 5.09 | 7.98 | 7.1e-12 | medium |
| 2026-03-02 | Rocket Mortgage, LLC | Mortgage | Trouble during payment process | 56 | 10.0 | 80 | 5.6 | 7.96 | 2.09e-19 | medium |
| 2026-03-02 | CL Holdings LLC | Debt collection | Attempts to collect debt not owed | 236 | 57.62 | 461 | 4.1 | 7.55 | 3.45e-57 | medium |
| 2025-01-13 | EQUIFAX, INC. | Credit reporting or other personal consumer reports | Problem with a company's investigation into an existing problem | 1865 | 802.12 | 6417 | 2.33 | 7.47 | 7.2e-192 | medium |
| 2024-08-19 | LEXISNEXIS | Credit reporting or other personal consumer reports | Incorrect information on your report | 49 | 17.88 | 143 | 2.74 | 7.36 | 1.81e-08 | medium |
| 2025-01-13 | BANK OF AMERICA, NATIONAL ASSOCIATION | Checking or savings account | Managing an account | 74 | 27.25 | 218 | 2.72 | 7.32 | 8.03e-12 | medium |
| 2024-12-02 | MOHELA | Student loan | Dealing with your lender or servicer | 159 | 47.0 | 376 | 3.38 | 7.24 | 1.24e-31 | medium |
| 2024-09-02 | LEXISNEXIS | Credit reporting or other personal consumer reports | Problem with a company's investigation into an existing problem | 35 | 7.12 | 57 | 4.91 | 7.13 | 1.49e-11 | medium |
| 2024-05-06 | Chime Financial Inc | Checking or savings account | Closing an account | 24 | 4.4 | 22 | 5.45 | 7.02 | 2.76e-08 | medium |
| 2025-02-17 | TRANSUNION INTERMEDIATE HOLDINGS, INC. | Debt collection | Written notification about debt | 47 | 9.38 | 75 | 5.01 | 6.87 | 3.27e-15 | medium |
| 2025-08-04 | TRANSUNION INTERMEDIATE HOLDINGS, INC. | Debt collection | Attempts to collect debt not owed | 195 | 85.5 | 684 | 2.28 | 6.82 | 4.94e-21 | medium |
| 2025-01-20 | ENCORE CAPITAL GROUP INC. | Credit reporting or other personal consumer reports | Problem with a company's investigation into an existing problem | 36 | 4.25 | 34 | 8.47 | 6.57 | 7.36e-17 | medium |
| 2025-02-17 | EQUIFAX, INC. | Debt collection | Written notification about debt | 54 | 11.25 | 90 | 4.8 | 6.45 | 1.25e-16 | medium |
| 2026-03-02 | Spring Oaks Capital, LLC | Debt collection | Attempts to collect debt not owed | 48 | 12.5 | 100 | 3.84 | 6.28 | 3.1e-12 | medium |
| 2024-09-09 | Navient Solutions, LLC. | Student loan | Dealing with your lender or servicer | 53 | 19.75 | 158 | 2.68 | 6.23 | 8.9e-09 | medium |
| 2025-03-10 | MOHELA | Credit reporting or other personal consumer reports | Improper use of your report | 37 | 5.25 | 42 | 7.05 | 6.07 | 1.45e-15 | medium |
| 2026-03-02 | Kriya Capital, LLC | Debt collection | Attempts to collect debt not owed | 73 | 23.88 | 191 | 3.06 | 6.05 | 1.08e-13 | medium |
| 2025-08-04 | Experian Information Solutions Inc. | Debt collection | Attempts to collect debt not owed | 143 | 64.38 | 515 | 2.22 | 5.91 | 4e-15 | medium |
| 2026-03-02 | ENCORE CAPITAL GROUP INC. | Debt collection | Attempts to collect debt not owed | 164 | 45.88 | 367 | 3.57 | 5.91 | 8.9e-35 | medium |
| 2025-01-20 | TRANSUNION INTERMEDIATE HOLDINGS, INC. | Credit reporting or other personal consumer reports | Problem with a company's investigation into an existing problem | 2227 | 869.0 | 6952 | 2.56 | 5.9 | 1.72e-274 | medium |
| 2025-03-10 | MOHELA | Student loan | Improper use of your report | 37 | 3.62 | 29 | 10.21 | 5.9 | 5.63e-19 | medium |
| 2025-07-07 | TRANSUNION INTERMEDIATE HOLDINGS, INC. | Credit reporting or other personal consumer reports | Problem with a company's investigation into an existing problem | 1113 | 806.5 | 6452 | 1.38 | 5.82 | 6.98e-22 | low |
| 2025-02-17 | Experian Information Solutions Inc. | Debt collection | Written notification about debt | 55 | 14.75 | 118 | 3.73 | 5.8 | 2.22e-13 | medium |
| 2025-03-10 | Servicer under contract with Federal Student Aid | Student loan | Dealing with your lender or servicer | 49 | 11.38 | 91 | 4.31 | 5.79 | 6.98e-14 | medium |
| 2025-01-20 | EQUIFAX, INC. | Credit reporting or other personal consumer reports | Problem with a company's investigation into an existing problem | 3226 | 925.5 | 7404 | 3.49 | 5.69 | 0 | medium |
| 2025-01-20 | CBC Companies, Inc. | Credit reporting or other personal consumer reports | Incorrect information on your report | 95 | 25.62 | 205 | 3.71 | 5.56 | 9.43e-22 | medium |
| 2024-08-12 | TRANSUNION INTERMEDIATE HOLDINGS, INC. | Credit reporting or other personal consumer reports | Problem with fraud alerts or security freezes | 27 | 6.88 | 55 | 3.93 | 5.41 | 1.04e-07 | medium |
| 2026-03-02 | I.C. System, Inc. | Debt collection | Attempts to collect debt not owed | 70 | 21.62 | 173 | 3.24 | 5.4 | 3.77e-14 | medium |
| 2025-05-26 | TRANSUNION INTERMEDIATE HOLDINGS, INC. | Credit reporting or other personal consumer reports | Improper use of your report | 2512 | 1590.75 | 12726 | 1.58 | 5.38 | 4.31e-88 | low |
| 2025-03-10 | Nelnet, Inc. | Credit reporting or other personal consumer reports | Improper use of your report | 61 | 8.5 | 68 | 7.18 | 5.31 | 7.24e-25 | medium |
| 2025-03-10 | MOHELA | Student loan | Dealing with your lender or servicer | 160 | 72.88 | 583 | 2.2 | 5.25 | 2.42e-16 | medium |
| 2025-03-10 | Servicer under contract with Federal Student Aid | Credit reporting or other personal consumer reports | Improper use of your report | 23 | 3.12 | 25 | 7.36 | 5.24 | 1.61e-10 | medium |
| 2026-03-02 | Portfolio Recovery Associates, LLC | Debt collection | Attempts to collect debt not owed | 100 | 32.62 | 261 | 3.07 | 5.23 | 3.43e-18 | medium |
| 2025-08-11 | EQUIFAX, INC. | Credit card | Problem with a company's investigation into an existing problem | 29 | 4.12 | 33 | 7.03 | 5.16 | 1.6e-12 | medium |
| 2025-08-11 | TRANSUNION INTERMEDIATE HOLDINGS, INC. | Credit card | Problem with a company's investigation into an existing problem | 25 | 3.25 | 26 | 7.69 | 5.14 | 1.4e-11 | medium |
| 2024-09-09 | Advanced Resolution Services Inc. | Credit reporting or other personal consumer reports | Incorrect information on your report | 35 | 3.12 | 25 | 11.2 | 5.11 | 8.19e-19 | medium |
| 2025-01-20 | Resurgent Capital Services L.P. | Credit reporting or other personal consumer reports | Problem with a company's investigation into an existing problem | 39 | 9.25 | 74 | 4.22 | 5.0 | 3.67e-11 | medium |
| 2024-11-04 | ID Analytics, Inc. | Credit reporting or other personal consumer reports | Incorrect information on your report | 30 | 5.62 | 45 | 5.33 | 4.84 | 9.2e-11 | low |
| 2025-05-26 | EQUIFAX, INC. | Credit reporting or other personal consumer reports | Improper use of your report | 2811 | 1642.25 | 13138 | 1.71 | 4.74 | 1.89e-131 | low |
| 2025-01-20 | CL Holdings LLC | Credit reporting or other personal consumer reports | Problem with a company's investigation into an existing problem | 25 | 4.25 | 34 | 5.88 | 4.68 | 7.38e-10 | low |
| 2024-12-02 | TRANSUNION INTERMEDIATE HOLDINGS, INC. | Credit reporting or other personal consumer reports | Improper use of your report | 1310 | 1071.12 | 8569 | 1.22 | 4.58 | 1.91e-11 | low |
| 2026-03-02 | CCS Financial Services, Inc. | Debt collection | Attempts to collect debt not owed | 89 | 27.62 | 221 | 3.22 | 4.57 | 1.96e-17 | low |
| 2025-08-04 | EQUIFAX, INC. | Debt collection | Attempts to collect debt not owed | 202 | 112.25 | 898 | 1.8 | 4.57 | 8.63e-13 | low |
| 2025-01-20 | CAPITAL ONE FINANCIAL CORPORATION | Credit reporting or other personal consumer reports | Problem with a company's investigation into an existing problem | 43 | 13.0 | 104 | 3.31 | 4.49 | 1.55e-09 | low |
| 2024-08-19 | MOHELA | Student loan | Dealing with your lender or servicer | 65 | 29.25 | 234 | 2.22 | 4.43 | 9.17e-08 | low |
| 2025-01-13 | TRANSUNION INTERMEDIATE HOLDINGS, INC. | Credit reporting or other personal consumer reports | Problem with a company's investigation into an existing problem | 1355 | 810.0 | 6480 | 1.67 | 4.42 | 9.99e-60 | low |
| 2024-08-12 | Experian Information Solutions Inc. | Credit reporting or other personal consumer reports | Improper use of your report | 1312 | 1055.25 | 8442 | 1.24 | 4.41 | 4.79e-13 | low |
| 2025-08-04 | Experian Information Solutions Inc. | Credit card | Incorrect information on your report | 24 | 3.25 | 26 | 7.38 | 4.32 | 6.25e-11 | low |
| 2024-04-29 | TRANSUNION INTERMEDIATE HOLDINGS, INC. | Credit reporting or other personal consumer reports | Incorrect information on your report | 1717 | 1415.75 | 5663 | 1.21 | 4.28 | 3.16e-12 | low |
| 2025-04-07 | TRANSUNION INTERMEDIATE HOLDINGS, INC. | Debt collection | Written notification about debt | 131 | 48.38 | 387 | 2.71 | 4.17 | 1.51e-19 | low |
| 2025-05-19 | Experian Information Solutions Inc. | Credit reporting or other personal consumer reports | Improper use of your report | 1800 | 1272.62 | 10181 | 1.41 | 4.12 | 5.37e-39 | low |
| 2024-11-11 | NAVY FEDERAL CREDIT UNION | Checking or savings account | Managing an account | 35 | 10.62 | 85 | 3.29 | 4.11 | 5.17e-08 | low |
| 2024-04-29 | Experian Information Solutions Inc. | Credit reporting or other personal consumer reports | Incorrect information on your report | 1700 | 1433.75 | 5735 | 1.19 | 4.09 | 6.65e-10 | low |
| 2025-05-19 | Block, Inc. | Money transfer, virtual currency, or money service | Other transaction problem | 165 | 67.25 | 538 | 2.45 | 4.07 | 1.36e-20 | low |
| 2025-07-28 | Netspend Corporation | Checking or savings account | Managing an account | 26 | 3.75 | 30 | 6.93 | 4.07 | 2.7e-11 | low |
| 2024-08-12 | CBC Companies, Inc. | Credit reporting or other personal consumer reports | Improper use of your report | 32 | 8.38 | 67 | 3.82 | 4.04 | 1.23e-08 | low |
| 2025-05-26 | Experian Information Solutions Inc. | Credit reporting or other personal consumer reports | Improper use of your report | 2228 | 1348.62 | 10789 | 1.65 | 3.99 | 1.04e-92 | low |
| 2026-04-06 | MOHELA | Student loan | Dealing with your lender or servicer | 83 | 30.12 | 241 | 2.76 | 3.95 | 2.48e-13 | low |
| 2025-04-07 | Experian Information Solutions Inc. | Debt collection | Written notification about debt | 105 | 43.88 | 351 | 2.39 | 3.93 | 3.59e-13 | low |
| 2024-04-29 | EQUIFAX, INC. | Credit reporting or other personal consumer reports | Incorrect information on your report | 1692 | 1419.5 | 5678 | 1.19 | 3.93 | 2.33e-10 | low |
| 2026-03-02 | JPMORGAN CHASE & CO. | Checking or savings account | Managing an account | 93 | 39.38 | 315 | 2.36 | 3.88 | 1.35e-11 | low |
| 2026-03-09 | Paypal Holdings, Inc | Money transfer, virtual currency, or money service | Fraud or scam | 48 | 15.88 | 127 | 3.02 | 3.88 | 2e-09 | low |
| 2025-01-20 | Servicer under contract with Federal Student Aid | Student loan | Struggling to repay your loan | 24 | 3.38 | 27 | 7.11 | 3.78 | 1.07e-10 | low |
| 2024-08-26 | Experian Information Solutions Inc. | Credit reporting or other personal consumer reports | Incorrect information on your report | 2337 | 1954.62 | 15637 | 1.2 | 3.76 | 1.73e-15 | low |
| 2025-05-19 | EQUIFAX, INC. | Credit reporting or other personal consumer reports | Improper use of your report | 2136 | 1550.0 | 12400 | 1.38 | 3.72 | 6.46e-40 | low |
| 2025-04-14 | Experian Information Solutions Inc. | Debt collection | Written notification about debt | 138 | 55.25 | 442 | 2.5 | 3.7 | 4.87e-18 | low |
| 2025-04-14 | EQUIFAX, INC. | Debt collection | Written notification about debt | 166 | 68.5 | 548 | 2.42 | 3.62 | 2.88e-20 | low |
| 2024-08-19 | CBC Companies, Inc. | Credit reporting or other personal consumer reports | Incorrect information on your report | 36 | 10.88 | 87 | 3.31 | 3.6 | 3.06e-08 | low |
| 2024-08-12 | TRANSUNION INTERMEDIATE HOLDINGS, INC. | Credit reporting or other personal consumer reports | Improper use of your report | 1368 | 1112.75 | 8902 | 1.23 | 3.55 | 2.19e-12 | low |
| 2024-04-29 | Navient Solutions, LLC. | Student loan | Dealing with your lender or servicer | 40 | 14.25 | 57 | 2.81 | 3.52 | 1.24e-06 | low |
| 2025-06-09 | CBC Companies, Inc. | Credit reporting or other personal consumer reports | Incorrect information on your report | 86 | 37.5 | 300 | 2.29 | 3.51 | 2.56e-10 | low |
| 2024-11-18 | Experian Information Solutions Inc. | Credit reporting or other personal consumer reports | Incorrect information on your report | 2730 | 2212.75 | 17702 | 1.23 | 3.48 | 1.26e-23 | low |
| 2025-05-12 | EQUIFAX, INC. | Credit reporting or other personal consumer reports | Improper use of your report | 1852 | 1499.88 | 11999 | 1.23 | 3.47 | 9.86e-17 | low |
| 2025-05-12 | Experian Information Solutions Inc. | Credit reporting or other personal consumer reports | Improper use of your report | 1518 | 1237.75 | 9902 | 1.23 | 3.45 | 2.74e-13 | low |
| 2025-03-03 | TRANSUNION INTERMEDIATE HOLDINGS, INC. | Credit reporting or other personal consumer reports | Problem with fraud alerts or security freezes | 53 | 18.5 | 148 | 2.86 | 3.44 | 1.43e-09 | low |
| 2024-08-19 | TRANSUNION INTERMEDIATE HOLDINGS, INC. | Credit reporting or other personal consumer reports | Problem with a company's investigation into an existing problem | 1068 | 886.0 | 7088 | 1.21 | 3.36 | 1.41e-08 | low |
| 2025-07-07 | Experian Information Solutions Inc. | Credit reporting or other personal consumer reports | Problem with a company's investigation into an existing problem | 1243 | 954.12 | 7633 | 1.3 | 3.36 | 2.97e-17 | low |
| 2025-02-03 | ID Analytics, Inc. | Credit reporting or other personal consumer reports | Incorrect information on your report | 61 | 26.0 | 208 | 2.35 | 3.35 | 4.54e-08 | low |
| 2025-07-28 | TRANSUNION INTERMEDIATE HOLDINGS, INC. | Debt collection | Written notification about debt | 141 | 75.38 | 603 | 1.87 | 3.29 | 2.3e-10 | low |
| 2025-04-14 | TRANSUNION INTERMEDIATE HOLDINGS, INC. | Debt collection | Written notification about debt | 162 | 63.5 | 508 | 2.55 | 3.29 | 1.29e-21 | low |
| 2025-01-06 | Experian Information Solutions Inc. | Credit reporting or other personal consumer reports | Problem with a company's investigation into an existing problem | 1345 | 891.62 | 7133 | 1.51 | 3.26 | 5.68e-40 | low |
| 2026-02-16 | CL Holdings LLC | Debt collection | Attempts to collect debt not owed | 104 | 44.5 | 356 | 2.34 | 3.25 | 1.53e-12 | low |
| 2025-01-20 | Block, Inc. | Money transfer, virtual currency, or money service | Unauthorized transactions or other transaction problem | 168 | 22.88 | 183 | 7.34 | 3.23 | 2.66e-66 | low |
| 2025-04-14 | MicroBilt / PRBC (formerly CL Verify) | Credit reporting or other personal consumer reports | Problem with fraud alerts or security freezes | 24 | 2.5 | 20 | 9.6 | 3.22 | 1.66e-12 | low |
| 2025-07-07 | CBC Companies, Inc. | Credit reporting or other personal consumer reports | Improper use of your report | 73 | 22.88 | 183 | 3.19 | 3.2 | 1.95e-14 | low |
| 2024-08-12 | EQUIFAX, INC. | Credit reporting or other personal consumer reports | Improper use of your report | 1327 | 1130.75 | 9046 | 1.17 | 3.19 | 4.97e-08 | low |
| 2025-01-06 | Experian Information Solutions Inc. | Credit reporting or other personal consumer reports | Incorrect information on your report | 3497 | 2453.25 | 19626 | 1.43 | 3.16 | 7.02e-77 | low |
| 2026-06-22 | Experian Information Solutions Inc. | Debt collection | Written notification about debt | 59 | 23.5 | 188 | 2.51 | 3.14 | 1.02e-08 | low |
| 2025-05-19 | TRANSUNION INTERMEDIATE HOLDINGS, INC. | Credit reporting or other personal consumer reports | Improper use of your report | 1904 | 1538.75 | 12310 | 1.24 | 3.12 | 1.91e-17 | low |
| 2025-09-01 | EQUIFAX, INC. | Credit card | Incorrect information on your report | 35 | 9.38 | 75 | 3.73 | 3.09 | 4.24e-09 | low |
| 2024-12-02 | Experian Information Solutions Inc. | Credit reporting or other personal consumer reports | Improper use of your report | 1327 | 1079.12 | 8633 | 1.23 | 3.08 | 4.31e-12 | low |
| 2024-05-06 | Experian Information Solutions Inc. | Credit reporting or other personal consumer reports | Problem with a company's investigation into an existing problem | 1004 | 825.4 | 4127 | 1.22 | 3.07 | 2.6e-08 | low |
| 2024-12-02 | TRANSUNION INTERMEDIATE HOLDINGS, INC. | Credit reporting or other personal consumer reports | Incorrect information on your report | 2866 | 2217.88 | 17743 | 1.29 | 3.06 | 2.76e-35 | low |
| 2024-05-20 | TRANSUNION INTERMEDIATE HOLDINGS, INC. | Credit reporting or other personal consumer reports | Problem with a company's investigation into an existing problem | 1021 | 846.14 | 5923 | 1.21 | 3.05 | 3.13e-08 | low |
| 2025-04-07 | EQUIFAX, INC. | Debt collection | Written notification about debt | 124 | 54.5 | 436 | 2.28 | 3.05 | 6.05e-14 | low |
| 2024-11-11 | ID Analytics, Inc. | Credit reporting or other personal consumer reports | Incorrect information on your report | 39 | 8.38 | 67 | 4.66 | 3.05 | 3.73e-12 | low |
| 2025-04-07 | EQUIFAX, INC. | Credit reporting or other personal consumer reports | Problem with fraud alerts or security freezes | 89 | 41.12 | 329 | 2.16 | 3.05 | 1.42e-09 | low |
| 2025-04-14 | CORELOGIC INC | Credit reporting or other personal consumer reports | Problem with fraud alerts or security freezes | 24 | 2.62 | 21 | 9.14 | 3.04 | 3.23e-12 | low |
| 2024-05-20 | EQUIFAX, INC. | Credit reporting or other personal consumer reports | Problem with a company's investigation into an existing problem | 1031 | 815.71 | 5710 | 1.26 | 3.03 | 8.79e-12 | low |
| 2024-11-18 | EQUIFAX, INC. | Credit reporting or other personal consumer reports | Incorrect information on your report | 2572 | 2102.62 | 16821 | 1.22 | 3.02 | 8.64e-21 | low |

## Limitations

* CFPB complaint arrival patterns, reporting delays, and publication batches can produce bursts unrelated to new underlying incidents.
* No confirmed incidents or reviewed alerts are available; this is a descriptive historical backtest, not predictive-accuracy validation.
* Results describe the selected source snapshot. Source completeness or upstream filtering can affect counts; complaint records are not linked to incident ground truth.
* Severity is a transparent statistical heuristic, not consumer-harm severity or legal risk.
