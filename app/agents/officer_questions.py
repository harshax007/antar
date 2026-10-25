"""
Antar - the questions offered on the empty chat screen
======================================================
What a station officer, an SHO or a district analyst actually needs on a working day, drawn
from the hackathon test suite (questions.txt, 165 prompts) and kept only when the answer can
be trusted: each one is answered from the register by a fixed path (a template, the case
sheet, the comparison, the anomaly scan or a stated register gap), never by the model alone.

tests/test_officer_questions.py asks every one of them, in English and in Kannada, through
the real chat stream, and fails if any is turned away, asks back, or answers in the wrong
language. A question that stops passing comes off this list; it is not reworded to pass.

`suite` names the test-suite prompt each one answers, so a reviewer can trace it. `kn` is
None where the answer is written in English only.
"""
from __future__ import annotations

OFFICER_QUESTIONS: list[dict] = [
    # the day: what came in, is it unusual
    {"en": "How many FIRs were registered today?",
     "kn": "ಇಂದು ಎಷ್ಟು FIR ದಾಖಲಾಗಿವೆ?", "suite": "Q057"},
    {"en": "Is today busier than usual?",
     "kn": "ಇಂದು ಸಾಮಾನ್ಯಕ್ಕಿಂತ ಹೆಚ್ಚು ಪ್ರಕರಣಗಳು ದಾಖಲಾಗಿವೆಯೇ?", "suite": "Q058"},
    {"en": "Are there any unusual spikes right now?",
     "kn": "ಈಗ ಯಾವುದಾದರೂ ಅಸಾಮಾನ್ಯ ಏರಿಕೆ ಇದೆಯೇ?", "suite": "Q039"},
    {"en": "Is crime rising in Bengaluru City this week?",
     "kn": "ಈ ವಾರ ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಅಪರಾಧ ಹೆಚ್ಚಾಗುತ್ತಿದೆಯೇ?", "suite": "Q009"},
    {"en": "Which police stations registered the most FIRs this week?",
     "kn": "ಈ ವಾರ ಅತಿ ಹೆಚ್ಚು FIR ದಾಖಲಾದ ಪೊಲೀಸ್ ಠಾಣೆಗಳು ಯಾವುವು?", "suite": "Q122"},
    {"en": "Which crime types rose the most in the last 6 months?",
     "kn": "ಕಳೆದ 6 ತಿಂಗಳಲ್ಲಿ ಯಾವ ಅಪರಾಧ ಪ್ರಕಾರಗಳು ಹೆಚ್ಚು ಏರಿಕೆ ಕಂಡಿವೆ?", "suite": "Q012"},
    {"en": "Top 5 crime types in Karnataka this year with their share",
     "kn": "ಈ ವರ್ಷ ಕರ್ನಾಟಕದಲ್ಲಿ ಅತಿ ಹೆಚ್ಚು ದಾಖಲಾದ ಅಪರಾಧ ಪ್ರಕಾರಗಳು", "suite": "Q011"},
    # where to put people
    {"en": "Where should the night patrol focus in Bengaluru City?",
     "kn": "ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ರಾತ್ರಿ ಗಸ್ತು ಎಲ್ಲಿ ಕೇಂದ್ರೀಕರಿಸಬೇಕು?", "suite": "Q013"},
    {"en": "Top areas for chain snatching in Bengaluru City",
     "kn": "ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಸರಗಳ್ಳತನ ಹೆಚ್ಚು ಇರುವ ಪ್ರದೇಶಗಳು", "suite": "Q148"},
    {"en": "Which day of the week has the most theft in Bengaluru City?",
     "kn": "ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ವಾರದ ಯಾವ ದಿನ ಕಳ್ಳತನ ಹೆಚ್ಚು?", "suite": "Q014"},
    # follow-ups the chat already offers under an answer, kept on the empty screen too
    {"en": "Which districts have the most theft?",
     "kn": "ಯಾವ ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಕಳ್ಳತನ ಹೆಚ್ಚು?", "suite": "chat"},
    {"en": "Top beats for theft in Bengaluru City",
     "kn": "ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಕಳ್ಳತನ ಹೆಚ್ಚು ಇರುವ ಬೀಟ್‌ಗಳು", "suite": "chat"},
    {"en": "Top beats for burglary in Bengaluru City",
     "kn": "ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಮನೆಗಳ್ಳತನ ಹೆಚ್ಚು ಇರುವ ಬೀಟ್‌ಗಳು", "suite": "chat"},
    {"en": "Conviction rate for theft in Bengaluru City",
     "kn": "ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಕಳ್ಳತನ ಪ್ರಕರಣಗಳ ಶಿಕ್ಷೆ ದರ", "suite": "chat"},
    {"en": "Which police stations recorded the most cybercrime in 2022?",
     "kn": "2022 ರಲ್ಲಿ ಅತಿ ಹೆಚ್ಚು ಸೈಬರ್ ಅಪರಾಧ ದಾಖಲಿಸಿದ ಪೊಲೀಸ್ ಠಾಣೆಗಳು ಯಾವುವು?", "suite": "chat"},
    # one case. The case sheet is written in English only, so these are offered in English
    # on the Kannada screen too (kn None) rather than asked in Kannada and answered in English.
    {"en": "Retrieve FIR 100011245202300001 and summarise it",
     "kn": None, "suite": "Q002"},
    {"en": "Timeline of FIR C00418",
     "kn": None, "suite": "Q003"},
    {"en": "Find cases similar to FIR C00418",
     "kn": None, "suite": "Q006"},
    # the caseload
    {"en": "Cases under investigation for more than 90 days in Mysuru City",
     "kn": "ಮೈಸೂರು ನಗರದಲ್ಲಿ 90 ದಿನಗಳಿಗಿಂತ ಹೆಚ್ಚು ಕಾಲ ತನಿಖೆಯಲ್ಲಿರುವ ಪ್ರಕರಣಗಳು", "suite": "Q004"},
    {"en": "Case status breakdown in Bengaluru City this year",
     "kn": "ಈ ವರ್ಷ ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಪ್ರಕರಣಗಳ ಸ್ಥಿತಿ", "suite": "Q111"},
    {"en": "Which districts have the highest charge-sheet rate this year?",
     "kn": "ಈ ವರ್ಷ ಅತಿ ಹೆಚ್ಚು ದೋಷಾರೋಪ ಪಟ್ಟಿ ದರ ಇರುವ ಜಿಲ್ಲೆಗಳು", "suite": "Q113"},
    # links across cases
    {"en": "Are any UPI IDs shared across multiple cyber fraud cases?",
     "kn": "ಹಲವು ಸೈಬರ್ ವಂಚನೆ ಪ್ರಕರಣಗಳಲ್ಲಿ ಒಂದೇ UPI ID ಇದೆಯೇ?", "suite": "Q036"},
    {"en": "Which vehicles appear in FIRs across 3 or more districts?",
     "kn": "3 ಅಥವಾ ಹೆಚ್ಚು ಜಿಲ್ಲೆಗಳ FIR ಗಳಲ್ಲಿ ಕಾಣಿಸಿಕೊಂಡ ವಾಹನಗಳು", "suite": "Q018"},
    # people, in aggregate only
    {"en": "Accused age groups in theft cases",
     "kn": "ಕಳ್ಳತನ ಪ್ರಕರಣಗಳಲ್ಲಿ ಆರೋಪಿಗಳ ವಯಸ್ಸಿನ ಗುಂಪುಗಳು", "suite": "Q023"},
    {"en": "Victims of crimes against women by age group",
     "kn": "ಮಹಿಳೆಯರ ವಿರುದ್ಧದ ಅಪರಾಧಗಳ ಸಂತ್ರಸ್ತರು ವಯಸ್ಸಿನ ಪ್ರಕಾರ", "suite": "Q024"},
    # what the record can and cannot say
    {"en": "FIRs with missing location coordinates",
     "kn": "ಸ್ಥಳದ ನಿರ್ದೇಶಾಂಕಗಳಿಲ್ಲದ FIR ಗಳು", "suite": "Q143"},
    {"en": "Theft by hour of day in Bengaluru City",
     "kn": "ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ದಿನದ ಯಾವ ಗಂಟೆಯಲ್ಲಿ ಕಳ್ಳತನ ಹೆಚ್ಚು?", "suite": "Q014"},
    {"en": "Monthly burglary in Mysuru City in 2025",
     "kn": "2025 ರಲ್ಲಿ ಮೈಸೂರು ನಗರದಲ್ಲಿ ತಿಂಗಳವಾರು ಮನೆಗಳ್ಳತನ ಪ್ರಕರಣಗಳು", "suite": "Q047"},
]
