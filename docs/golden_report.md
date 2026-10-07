# Golden Query Report — mode: offline
**Accuracy: 35/35 = 100.0%**
(F1 gate = ≥90% on the LLM path. Offline = build-time sanity only.)

| ✓ | Query | lang | expected | got | rows |
|---|---|---|---|---|---|
| ✅ | show chain snatching in Rajajinagar | en | T1 | T1 | 10 |
| ✅ | list robberies in Bengaluru North | en | T1 | T1 | 10 |
| ✅ | show robbery trend in Bengaluru North last 3 months | en | T3 | T3 | 2 |
| ✅ | theft trend over time | en | T3 | T3 | 6 |
| ✅ | where are the theft hotspots | en | T11 | T11 | 10 |
| ✅ | which zones have the most crime | en | T11 | T11 | 10 |
| ✅ | who are the repeat offenders | en | T5 | T5 | 10 |
| ✅ | find suspect Yellappa | en | T2 | T2 | 2 |
| ✅ | who is Raju | en | T2 | T2 | 25 |
| ✅ | top suspects in Rajajinagar | en | T4 | T4 | 10 |
| ✅ | victim gender breakdown | en | T7 | T7 | 2 |
| ✅ | age breakdown of suspects | en | T7 | T7 | 35 |
| ✅ | how many open cases by status | en | T8 | T8 | 17 |
| ✅ | recent crimes in Whitefield | en | T12 | T12 | 10 |
| ✅ | where should I increase patrols this weekend | en | CLARIFY | CLARIFY | 0 |
| ✅ | vehicle theft this month where | en | T11 | T11 | 3 |
| ✅ | ರಾಜಾಜಿನಗರದಲ್ಲಿ ಸರಗಳ್ಳತನ ಪ್ರಕರಣಗಳು | kn | T1 | T1 | 10 |
| ✅ | ದರೋಡೆ ಪ್ರವೃತ್ತಿ ತೋರಿಸಿ | kn | T3 | T3 | 6 |
| ✅ | ಅಪರಾಧ ಹಾಟ್‌ಸ್ಪಾಟ್ ಎಲ್ಲಿ | kn | CLARIFY | CLARIFY | 0 |
| ✅ | ಕಳ್ಳತನದ ಪ್ರಮುಖ ಸ್ಥಳಗಳು ಎಲ್ಲಿವೆ | kn | T11 | T11 | 10 |
| ✅ | ಪುನರಾವರ್ತಿತ ಅಪರಾಧಿಗಳು ಯಾರು | kn | T5 | T5 | 10 |
| ✅ | ಸಂತ್ರಸ್ತರ ಲಿಂಗ ವಿಭಜನೆ | kn | T7 | T7 | 2 |
| ✅ | ತೆರೆದ ಪ್ರಕರಣಗಳು ಎಷ್ಟು | kn | T8 | T8 | 17 |
| ✅ | ಇತ್ತೀಚಿನ ಪ್ರಕರಣಗಳು | kn | T12 | T12 | 10 |
| ✅ | which UPI IDs are used in more than one district | en | T19 | T19 | 10 |
| ✅ | FIRs for UPI user1101@bank | en | T20 | T20 | 19 |
| ✅ | cases for accused ACC-KA-500777 | en | T21 | T21 | 25 |
| ✅ | conviction rate by district in 2023 | en | T22 | T22 | 40 |
| ✅ | top beats for theft in Bengaluru City | en | T23 | T23 | 10 |
| ✅ | open theft cases by status in 2024 | en | T8 | T8 | 8 |
| ✅ | recent burglary cases in Whitefield | en | T12 | T12 | 10 |
| ✅ | ಹಲವು ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಬಳಸಿದ UPI ಐಡಿಗಳು | kn | T19 | T19 | 10 |
| ✅ | ACC-KA-500777 ಆರೋಪಿಯ ಪ್ರಕರಣಗಳು | kn | T21 | T21 | 25 |
| ✅ | ಜಿಲ್ಲಾವಾರು ಶಿಕ್ಷೆ ಪ್ರಮಾಣ | kn | T22 | T22 | 41 |
| ✅ | ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಕಳ್ಳತನ ಹೆಚ್ಚು ಇರುವ ಬೀಟ್‌ಗಳು | kn | T23 | T23 | 10 |