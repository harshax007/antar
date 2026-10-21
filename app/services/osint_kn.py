"""
Antar - OSINT results in Kannada
================================
`/api/osint/investigate?lang=kn` answers in Kannada. The checks themselves run once, in
English (osint_checks.py); this module rewrites what an officer reads - the summary, the
live-check sentences and labels, the official checks, the identifier's name and its points to
note - from the same facts. Nothing is re-checked and no number changes. Left as they are:
identifiers, portal and bank names, web page titles and snippets (the pages' own words), and the
BNSS notice draft, which goes to record holders who work in English.
"""

from __future__ import annotations

import copy
import re

_LABEL = {
    "Mobile number": "ಮೊಬೈಲ್ ಸಂಖ್ಯೆ", "UPI ID": "UPI ಐಡಿ", "Vehicle number": "ವಾಹನ ಸಂಖ್ಯೆ",
    "Vehicle number (Bharat series)": "ವಾಹನ ಸಂಖ್ಯೆ (ಭಾರತ್ ಸರಣಿ)", "Email address": "ಇಮೇಲ್ ವಿಳಾಸ",
    "Online username": "ಆನ್‌ಲೈನ್ ಬಳಕೆದಾರ ಹೆಸರು", "Name (person, company or place)": "ಹೆಸರು (ವ್ಯಕ್ತಿ, ಕಂಪನಿ ಅಥವಾ ಸ್ಥಳ)",
    "Bank account": "ಬ್ಯಾಂಕ್ ಖಾತೆ", "Bank branch code (IFSC)": "ಬ್ಯಾಂಕ್ ಶಾಖೆ ಕೋಡ್ (IFSC)",
    "Handset IMEI": "ಮೊಬೈಲ್ IMEI", "Website": "ವೆಬ್‌ಸೈಟ್",
}

_FIELD = {
    "E.164 Normalized": "ಪ್ರಮಾಣಿತ ರೂಪ", "TRAI Numbering Series": "TRAI ಸಂಖ್ಯಾ ಸರಣಿ", "Circle first allocated": "ಮೊದಲು ನೀಡಿದ ವಲಯ",
    "Note": "ಗಮನಿಸಿ", "SHA-256 Privacy Hash": "SHA-256 ಗೌಪ್ಯ ಗುರುತು", "Statutory Nodal": "ಕಾನೂನು ನೋಡಲ್ ಅಧಿಕಾರಿ",
    "Normalized Registration": "ಪ್ರಮಾಣಿತ ನೋಂದಣಿ", "RTO Code & Office": "RTO ಕೋಡ್ ಮತ್ತು ಕಚೇರಿ",
    "Revenue District / State": "ಜಿಲ್ಲೆ / ರಾಜ್ಯ", "Series / Sequence": "ಸರಣಿ / ಕ್ರಮ", "Telemetry Channels": "ಮಾಹಿತಿ ಮೂಲಗಳು",
    "Normalized Plate": "ಪ್ರಮಾಣಿತ ಸಂಖ್ಯೆ", "Registration Class": "ನೋಂದಣಿ ವರ್ಗ", "Registry Authority": "ನೋಂದಣಿ ಪ್ರಾಧಿಕಾರ",
    "Surveillance Vector": "ಮೇಲ್ವಿಚಾರಣಾ ಮಾರ್ಗ", "Normalized UPI VPA": "ಪ್ರಮಾಣಿತ UPI ಐಡಿ", "TPAP / Payment App": "ಪಾವತಿ ಆ್ಯಪ್",
    "Sponsoring PSP Bank": "ಪ್ರಾಯೋಜಕ ಬ್ಯಾಂಕ್", "Prefix Attribution": "ಮುಂಭಾಗದ ಅರ್ಥ", "Escalation Channel": "ದೂರು ಮಾರ್ಗ",
    "Normalized Email": "ಪ್ರಮಾಣಿತ ಇಮೇಲ್", "Username Prefix": "ಬಳಕೆದಾರ ಹೆಸರು", "Mail Domain": "ಮೇಲ್ ಡೊಮೇನ್",
    "Evidence Hash (SHA-256)": "ಸಾಕ್ಷ್ಯ ಗುರುತು (SHA-256)", "Target Subject": "ವಿಷಯ", "Classification": "ವರ್ಗ",
    "Normalized Handle": "ಪ್ರಮಾಣಿತ ಹ್ಯಾಂಡಲ್", "Session Fingerprint": "ಸೆಶನ್ ಗುರುತು",
    "Account number": "ಖಾತೆ ಸಂಖ್ಯೆ", "IFSC": "IFSC", "Bank code": "ಬ್ಯಾಂಕ್ ಕೋಡ್", "Branch code": "ಶಾಖೆ ಕೋಡ್",
    "Escalation": "ದೂರು ಮಾರ್ಗ", "Bank": "ಬ್ಯಾಂಕ್", "IMEI": "IMEI",
    "Type allocation code (make and model)": "ಮಾದರಿ ಕೋಡ್ (ತಯಾರಿಕೆ ಮತ್ತು ಮಾದರಿ)", "Serial": "ಕ್ರಮ ಸಂಖ್ಯೆ",
    "Check digit": "ಪರಿಶೀಲನಾ ಅಂಕಿ", "Top-level domain": "ಉನ್ನತ ಮಟ್ಟದ ಡೊಮೇನ್", "Holder of records": "ದಾಖಲೆ ಹೊಂದಿರುವವರು",
}

_FACT = {
    "Bank": "ಬ್ಯಾಂಕ್", "Branch": "ಶಾಖೆ", "Address": "ವಿಳಾಸ", "District / State": "ಜಿಲ್ಲೆ / ರಾಜ್ಯ",
    "Branch phone": "ಶಾಖೆಯ ಫೋನ್", "Payments it takes": "ಸ್ವೀಕರಿಸುವ ಪಾವತಿಗಳು", "Registered on": "ನೋಂದಣಿ ದಿನಾಂಕ",
    "Age": "ವಯಸ್ಸು", "Expires": "ಅವಧಿ ಮುಗಿಯುವುದು", "Registrar": "ರಿಜಿಸ್ಟ್ರಾರ್", "Name servers": "ನೇಮ್ ಸರ್ವರ್‌ಗಳು",
    "Certificates": "ಪ್ರಮಾಣಪತ್ರಗಳು", "First certificate": "ಮೊದಲ ಪ್ರಮಾಣಪತ್ರ", "Names covered": "ಒಳಗೊಂಡ ಹೆಸರುಗಳು",
    "IMEI": "IMEI", "Type allocation code (TAC)": "ಮಾದರಿ ಕೋಡ್ (TAC)", "Serial number": "ಕ್ರಮ ಸಂಖ್ಯೆ", "Check digit": "ಪರಿಶೀಲನಾ ಅಂಕಿ",
}

_LIVE_NAME = {
    "Bank branch (IFSC registry)": "ಬ್ಯಾಂಕ್ ಶಾಖೆ (IFSC ದಾಖಲೆ)", "Website registration (WHOIS)": "ವೆಬ್‌ಸೈಟ್ ನೋಂದಣಿ (WHOIS)",
    "Security certificates issued": "ನೀಡಲಾದ ಭದ್ರತಾ ಪ್ರಮಾಣಪತ್ರಗಳು", "IMEI check digit": "IMEI ಪರಿಶೀಲನಾ ಅಂಕಿ",
}

# official checks: name -> (name, what, how, step) in Kannada
_OFFICIAL = {
    "I4C Suspect Registry": ("I4C ಶಂಕಿತರ ದಾಖಲೆ",
        "ಭಾರತದ ಯಾವುದೇ ಭಾಗದಲ್ಲಿ ಇದು ಸೈಬರ್-ವಂಚನೆ ದೂರಿನಲ್ಲಿ ವರದಿಯಾಗಿದೆಯೇ (I4C ಬ್ಯಾಂಕ್‌ಗಳೊಂದಿಗೆ ಹಂಚಿಕೊಳ್ಳುವ ರಾಷ್ಟ್ರೀಯ ದಾಖಲೆ).",
        "ಪೋರ್ಟಲ್ ತೆರೆಯಿರಿ, 'Report & Check Suspect' ನಂತರ 'Check Suspect' ಆರಿಸಿ, ಪ್ರಕಾರ ಆರಿಸಿ ಮೌಲ್ಯ ಅಂಟಿಸಿ. ಹೊಂದಾಣಿಕೆ ಎಂದರೆ ದೂರು, ಪುರಾವೆಯಲ್ಲ; ಹೊಂದಾಣಿಕೆ ಇಲ್ಲದಿದ್ದರೆ ನಿರ್ದೋಷಿ ಎಂದಲ್ಲ.",
        "ಭಾರತದಾದ್ಯಂತ ಸೈಬರ್-ವಂಚನೆ ದೂರುಗಳಿಗಾಗಿ I4C ಶಂಕಿತರ ದಾಖಲೆಯಲ್ಲಿ ಪರಿಶೀಲಿಸಿ."),
    "NCRP / 1930 helpline": ("NCRP / 1930 ಸಹಾಯವಾಣಿ",
        "ವಂಚನೆಯಲ್ಲಿ ಕಳೆದ ಹಣವನ್ನು ವರದಿ ಮಾಡುವ ಸ್ಥಳ, ಇದರಿಂದ ಬ್ಯಾಂಕ್ ಹಣವನ್ನು ತಡೆಹಿಡಿಯಬಹುದು.",
        "ಸಂತ್ರಸ್ತರು ಈಗಷ್ಟೇ ಹಣ ಕಳುಹಿಸಿದ್ದರೆ ಮೊದಲು 1930 ಗೆ ಕರೆ ಮಾಡಿ ಅಥವಾ ಪೋರ್ಟಲ್‌ನಲ್ಲಿ ದಾಖಲಿಸಿ; ತಡೆ ಮೊದಲ ಕೆಲವು ಗಂಟೆಗಳಲ್ಲಿ ಮಾತ್ರ ಕೆಲಸ ಮಾಡುತ್ತದೆ.",
        "ಸಂತ್ರಸ್ತರು ಈಗಷ್ಟೇ ಹಣ ಕಳುಹಿಸಿದ್ದರೆ, ಬ್ಯಾಂಕ್ ಹಣ ತಡೆಯಲು ಈಗಲೇ 1930 / NCRP ಗೆ ವರದಿ ಮಾಡಿ."),
    "Sanchar Saathi - Chakshu": ("ಸಂಚಾರ ಸಾಥಿ - ಚಕ್ಷು",
        "ವಂಚನೆ ಕರೆ ಅಥವಾ ಸಂದೇಶಗಳಿಗೆ ಬಳಸಿದ ಸಂಖ್ಯೆಯನ್ನು ವರದಿ ಮಾಡಿ, DoT ಪರಿಶೀಲಿಸಿ ಸಂಪರ್ಕ ಕಡಿತಗೊಳಿಸುತ್ತದೆ.",
        "'ಚಕ್ಷು' ತೆರೆಯಿರಿ, ಕರೆ ಅಥವಾ ಸಂದೇಶದ ವಿವರಗಳೊಂದಿಗೆ ಸಂಖ್ಯೆ ವರದಿ ಮಾಡಿ.",
        "ವಂಚನೆ ಕರೆ ಅಥವಾ ಸಂದೇಶಗಳಿಗೆ ಬಳಸಿದ್ದರೆ, ಸಂಪರ್ಕ ಕಡಿತಕ್ಕಾಗಿ ಸಂಚಾರ ಸಾಥಿ (ಚಕ್ಷು) ನಲ್ಲಿ ವರದಿ ಮಾಡಿ."),
    "WhatsApp profile (by hand)": ("WhatsApp ಪ್ರೊಫೈಲ್ (ಕೈಯಾರೆ)",
        "ಈ ಸಂಖ್ಯೆಗೆ WhatsApp ಖಾತೆ ಇದೆಯೇ, ಅದರ ಸಾರ್ವಜನಿಕ ಹೆಸರು ಮತ್ತು ಫೋಟೋ.",
        "ಅಧಿಕೃತ ಸಾಧನದಲ್ಲಿ ತೆರೆಯಿರಿ; ಏನು ಕಾಣುತ್ತದೆ ಮತ್ತು ಯಾವಾಗ ಎಂದು ಗುರುತಿಸಿ. ಸಂಖ್ಯೆಗೆ ಸಂದೇಶ ಕಳುಹಿಸಬೇಡಿ.",
        "ಅಧಿಕೃತ ಸಾಧನದಲ್ಲಿ ಅದರ WhatsApp ಪ್ರೊಫೈಲ್ ತೆರೆದು ಕಾಣುವ ಹೆಸರು ಮತ್ತು ಫೋಟೋ ಗುರುತಿಸಿ."),
    "Sanchar Saathi - CEIR": ("ಸಂಚಾರ ಸಾಥಿ - CEIR",
        "ಈ IMEI ಕಳೆದುಹೋದ ಅಥವಾ ಕಳುವಾದ ಫೋನ್ ಎಂದು ತಡೆಹಿಡಿಯಲಾಗಿದೆಯೇ, ಮತ್ತು ತಡೆದ ಠಾಣೆ ಯಾವುದು.",
        "'Request status' ತೆರೆಯಿರಿ ಅಥವಾ ಜಿಲ್ಲೆಯ CEIR ನೋಡಲ್ ಅಧಿಕಾರಿಯನ್ನು ಕೇಳಿ; ನೆಟ್‌ವರ್ಕ್‌ನಲ್ಲಿ ಕಂಡ ಕಳುವಾದ ಫೋನ್ ಪತ್ತೆಹಚ್ಚಬಹುದು.",
        "CEIR ನಲ್ಲಿ IMEI ಪರಿಶೀಲಿಸಿ: ಕಳುವು ಎಂದು ತಡೆದಿದ್ದರೆ, ತಡೆದ ಠಾಣೆಯಲ್ಲಿ ಮಾಲೀಕರ ದೂರು ಇರುತ್ತದೆ."),
    "Sanchar Saathi - Know Your Mobile": ("ಸಂಚಾರ ಸಾಥಿ - ನಿಮ್ಮ ಮೊಬೈಲ್ ತಿಳಿಯಿರಿ",
        "IMEI ಯಾವ ತಯಾರಿಕೆ ಮತ್ತು ಮಾದರಿಯದು, ಮತ್ತು ಅದು ನೈಜವೇ.",
        "'Know Genuineness of Your Mobile' ತೆರೆದು IMEI ನಮೂದಿಸಿ (ಅಥವಾ 'KYM <IMEI>' ಅನ್ನು 14422 ಗೆ SMS ಮಾಡಿ).",
        "ವಶಪಡಿಸಿದ ಫೋನ್‌ಗೆ ಹೋಲಿಸಲು ತಯಾರಿಕೆ ಮತ್ತು ಮಾದರಿಯನ್ನು KYM ನಲ್ಲಿ ಪರಿಶೀಲಿಸಿ ('KYM <IMEI>' ಅನ್ನು 14422 ಗೆ SMS)."),
    "eChallan (Parivahan)": ("ಇ-ಚಲನ್ (ಪರಿವಹನ್)",
        "ಬಾಕಿ ಮತ್ತು ಪಾವತಿಸಿದ ಸಂಚಾರ ದಂಡಗಳು: ಪ್ರತಿಯೊಂದೂ ವಾಹನ ಎಲ್ಲಿ, ಯಾವಾಗ ಕ್ಯಾಮೆರಾ ಅಥವಾ ಅಧಿಕಾರಿಗೆ ಸಿಕ್ಕಿತು ಎಂದು ಹೇಳುತ್ತದೆ.",
        "'Check Online Services' ನಂತರ 'Get Challan Details' ತೆರೆದು, ವಾಹನ ಸಂಖ್ಯೆ ಆರಿಸಿ ನಮೂದಿಸಿ.",
        "ಇ-ಚಲನ್ ನಲ್ಲಿ ದಂಡಗಳನ್ನು ನೋಡಿ: ಪ್ರತಿಯೊಂದೂ ವಾಹನ ಕಂಡ ದಿನಾಂಕ ಮತ್ತು ಸ್ಥಳ."),
    "Vahan / mParivahan (RC)": ("ವಾಹನ್ / ಎಂ-ಪರಿವಹನ್ (RC)",
        "ನೋಂದಣಿ ದಾಖಲೆ: ಮಾಲೀಕ, ತಯಾರಿಕೆ ಮತ್ತು ಮಾದರಿ, ಬಣ್ಣ, ವಿಮೆ, ಫಿಟ್‌ನೆಸ್ ಮತ್ತು ಸಾಲ (ಹೈಪೋಥಿಕೇಶನ್).",
        "ಪೊಲೀಸ್ ಪ್ರವೇಶ ವಾಹನ್ / CCTNS ಲಾಗಿನ್ ಮೂಲಕ; ನಾಗರಿಕರ ನೋಟ ಭಾಗಶಃ ಮಾತ್ರ.",
        "ವಾಹನ್ ನಲ್ಲಿ ನೋಂದಣಿ ದಾಖಲೆ ಪಡೆಯಿರಿ: ಮಾಲೀಕ, ತಯಾರಿಕೆ, ಬಣ್ಣ ಮತ್ತು ಸಾಲದಾತ."),
    "I4C - Check website / app": ("I4C - ವೆಬ್‌ಸೈಟ್ / ಆ್ಯಪ್ ಪರಿಶೀಲನೆ",
        "ಈ ವೆಬ್‌ಸೈಟ್ ಅಥವಾ ಆ್ಯಪ್ ಸೈಬರ್-ವಂಚನೆ ದೂರಿನಲ್ಲಿ ವರದಿಯಾಗಿದೆಯೇ.",
        "ಪೋರ್ಟಲ್‌ನಲ್ಲಿ 'Report & Check Suspect' ನಂತರ 'Check Suspect (Website/App)' ಆರಿಸಿ.",
        "ವಂಚನೆ ದೂರುಗಳಿಗಾಗಿ I4C ಪೋರ್ಟಲ್‌ನಲ್ಲಿ (Check Suspect: Website/App) ತಾಣವನ್ನು ಪರಿಶೀಲಿಸಿ."),
    "URLhaus malware check": ("URLhaus ಮಾಲ್‌ವೇರ್ ಪರಿಶೀಲನೆ",
        "ತಾಣ ಮಾಲ್‌ವೇರ್ ಹರಡುತ್ತಿರುವುದು ಕಂಡುಬಂದಿದೆಯೇ.", "ಈ ಡೊಮೇನ್‌ಗಾಗಿ ಸಾರ್ವಜನಿಕ ಹುಡುಕಾಟ ತೆರೆಯುತ್ತದೆ.",
        "ತಾಣ ಮಾಲ್‌ವೇರ್ ಹರಡಿದೆಯೇ ಎಂದು URLhaus ನಲ್ಲಿ ಪರಿಶೀಲಿಸಿ."),
    "Wayback Machine": ("ವೇಬ್ಯಾಕ್ ಮೆಷಿನ್",
        "ತೆಗೆದುಹಾಕಿದ್ದರೂ, ತಾಣ ಹಿಂದೆ ಹೇಗಿತ್ತು.", "ನೀವು ಅವಲಂಬಿಸುವ ಸಂಗ್ರಹಿತ ಪುಟಗಳನ್ನು (ದಿನಾಂಕ ಮತ್ತು ವಿಳಾಸ) ಪ್ರಕರಣ ದಿನಚರಿಗಾಗಿ ಉಳಿಸಿ.",
        "ತಾಣ ತೆಗೆಯುವ ಮೊದಲು ವೇಬ್ಯಾಕ್ ಮೆಷಿನ್‌ನಿಂದ ಅದರ ಸಂಗ್ರಹಿತ ಪುಟಗಳನ್ನು ಉಳಿಸಿ."),
    "eCourts - case status by party": ("ಇ-ಕೋರ್ಟ್ಸ್ - ಪಕ್ಷಕಾರರಿಂದ ಪ್ರಕರಣ ಸ್ಥಿತಿ",
        "ಈ ಹೆಸರು ಪಕ್ಷಕಾರರಾಗಿರುವ ಜಿಲ್ಲಾ ನ್ಯಾಯಾಲಯ ಪ್ರಕರಣಗಳು: ಪ್ರಕರಣ ಸಂಖ್ಯೆ, ನ್ಯಾಯಾಲಯ, ಮುಂದಿನ ದಿನಾಂಕ.",
        "'Case Status' ತೆರೆದು 'Party Name' ಆರಿಸಿ, ಕರ್ನಾಟಕ ಮತ್ತು ಜಿಲ್ಲೆ ಆರಿಸಿ, ಹೆಸರು ಟೈಪ್ ಮಾಡಿ.",
        "ಕರ್ನಾಟಕದ ಜಿಲ್ಲಾ ನ್ಯಾಯಾಲಯಗಳ ಪ್ರಕರಣಗಳಿಗಾಗಿ ಇ-ಕೋರ್ಟ್ಸ್ ನಲ್ಲಿ ಹೆಸರನ್ನು ಪಕ್ಷಕಾರರಾಗಿ ಹುಡುಕಿ."),
    "Indian Kanoon": ("ಇಂಡಿಯನ್ ಕಾನೂನ್",
        "ಈ ವ್ಯಕ್ತಿಯನ್ನು ಹೆಸರಿಸುವ ಹೈಕೋರ್ಟ್ ಮತ್ತು ಸುಪ್ರೀಂ ಕೋರ್ಟ್ ತೀರ್ಪುಗಳು, ಜಾಮೀನು ಆದೇಶಗಳು ಸೇರಿ.",
        "ನಿಖರ ಹೆಸರಿನ ಹುಡುಕಾಟ ತೆರೆಯುತ್ತದೆ; ಪ್ರತಿ ತೀರ್ಪು ಅದೇ ವ್ಯಕ್ತಿಯದೇ ಎಂದು (ತಂದೆಯ ಹೆಸರು, ವಿಳಾಸ) ಪರಿಶೀಲಿಸಿ.",
        "ಅವರನ್ನು ಹೆಸರಿಸುವ ಹೈಕೋರ್ಟ್ ತೀರ್ಪು ಮತ್ತು ಜಾಮೀನು ಆದೇಶಗಳಿಗಾಗಿ ಇಂಡಿಯನ್ ಕಾನೂನ್ ನಲ್ಲಿ ಹುಡುಕಿ."),
    "MCA - company and director search": ("MCA - ಕಂಪನಿ ಮತ್ತು ನಿರ್ದೇಶಕರ ಹುಡುಕಾಟ",
        "ಆ ಹೆಸರಿನ ಕಂಪನಿಗಳು ಮತ್ತು ನಿರ್ದೇಶಕರು: ನೋಂದಾಯಿತ ಕಂಪನಿಯ ಮೂಲಕ ವಂಚನೆ ನಡೆದಾಗ ಉಪಯುಕ್ತ.",
        "ಕಂಪನಿ ಹೆಸರು ಅಥವಾ ನಿರ್ದೇಶಕರಿಂದ ಹುಡುಕಿ; ಕಂಪನಿ ರಿಜಿಸ್ಟ್ರಾರ್‌ಗೆ ನೋಟಿಸ್‌ಗಾಗಿ CIN ಅಥವಾ DIN ಗುರುತಿಸಿ.",
        "ಕಂಪನಿ ಒಳಗೊಂಡಿದ್ದರೆ, ಅದರ ನಿರ್ದೇಶಕರು ಮತ್ತು ನೋಂದಾಯಿತ ವಿಳಾಸಕ್ಕಾಗಿ MCA ನಲ್ಲಿ ನೋಡಿ."),
    "News search (English and Kannada)": ("ಸುದ್ದಿ ಹುಡುಕಾಟ (ಇಂಗ್ಲಿಷ್ ಮತ್ತು ಕನ್ನಡ)",
        "ಇದನ್ನು ನಿಖರವಾಗಿ ಉಲ್ಲೇಖಿಸುವ ಸುದ್ದಿ ವರದಿಗಳು.", "ನಿಖರ ಪಠ್ಯಕ್ಕಾಗಿ ಸುದ್ದಿ ಹುಡುಕಾಟ ತೆರೆಯುತ್ತದೆ.",
        "ಇದಕ್ಕಾಗಿ ಸುದ್ದಿಯಲ್ಲಿ ಹುಡುಕಿ."),
}

_KIND = {"Court / Legal Archive": "ನ್ಯಾಯಾಲಯ ಪುಟ", "Public / Govt Registry": "ಸರ್ಕಾರಿ ಪುಟ",
         "News / Media Archive": "ಸುದ್ದಿ ವರದಿ", "Social / Digital Surface": "ಸಾಮಾಜಿಕ ಜಾಲತಾಣ ಪುಟ",
         "Commercial / Marketplace": "ಮಾರುಕಟ್ಟೆ ಪಟ್ಟಿ", "Open Web Surface": "ಇತರ ವೆಬ್‌ಸೈಟ್"}


def _facts(c: dict) -> dict:
    return {f["label"]: f["value"] for f in c.get("facts") or []}


def _live(c: dict) -> dict:
    """One live check, in Kannada, rebuilt from its facts and status."""
    c = copy.deepcopy(c)
    f = _facts(c)
    name, st = c.get("name"), c.get("status")
    c["key"] = name                      # the English name, which the screen matches on
    if name == "Bank branch (IFSC registry)":
        if st == "found":
            c["say"] = f"{f.get('Bank')}, {f.get('Branch')} ಶಾಖೆ ({f.get('District / State')}). ಖಾತೆದಾರರ ನೋಟಿಸ್ ಈ ಶಾಖೆಗೆ ಕಳುಹಿಸಬೇಕು."
            c["do"] = f"ಬ್ಯಾಂಕ್ ನೋಟಿಸ್ ಅನ್ನು {f.get('Bank')}, {str(f.get('Branch', '')).title()} ಶಾಖೆಯ ನೋಡಲ್ ಅಧಿಕಾರಿಗೆ ಕಳುಹಿಸಿ" \
                      + (f" (ಶಾಖೆಯ ಫೋನ್ {f['Branch phone']})." if f.get("Branch phone") not in (None, "not listed") else ".")
        elif st == "none":
            c["say"] = "ಈ IFSC RBI ಪಟ್ಟಿಯಲ್ಲಿ ಇಲ್ಲ. ಕೋಡ್ ಸರಿಯಾಗಿ ನಕಲಿಸಲಾಗಿದೆಯೇ ಪರಿಶೀಲಿಸಿ; ಪಾವತಿ ವಿನಂತಿಯಲ್ಲಿ ಕೃತಕ IFSC ವಂಚನೆಯ ಸೂಚನೆ."
            c["flag"] = "IFSC RBI ಪಟ್ಟಿಯಲ್ಲಿ ಇಲ್ಲ"
        else:
            c["say"] = "IFSC ದಾಖಲೆ ತಲುಪಲಿಲ್ಲ. ಏನನ್ನೂ ಪರಿಶೀಲಿಸಿಲ್ಲ."
    elif name == "Website registration (WHOIS)":
        if st == "found":
            age = f.get("Age", "-")
            days = int(re.sub(r"\D", "", age) or -1) if age != "-" else -1
            young = 0 <= days < 180
            c["say"] = (f"{days} ದಿನಗಳ ಹಿಂದೆ {f.get('Registrar')} ಮೂಲಕ ನೋಂದಣಿಯಾಗಿದೆ. " if days >= 0 else f"{f.get('Registrar')} ಮೂಲಕ ನೋಂದಣಿಯಾಗಿದೆ. ") \
                + ("ಇಷ್ಟು ಹೊಸ ವೆಬ್‌ಸೈಟ್ ವಂಚನೆ ತಾಣದ ಸಾಮಾನ್ಯ ಸೂಚನೆ." if young else "ಹೊಸದಾಗಿ ನೋಂದಣಿಯಾದ ತಾಣವಲ್ಲ.") \
                + " ನೋಂದಣಿದಾರರ ವಿವರ ರಿಜಿಸ್ಟ್ರಾರ್ ಬಳಿ ಇದೆ; BNSS ಸೆಕ್ಷನ್ 94 ಅಡಿ ಕೇಳಿ."
            c["do"] = f"ನೋಂದಣಿದಾರರ ಹೆಸರು, ಇಮೇಲ್, ಫೋನ್ ಮತ್ತು ಪಾವತಿ ವಿವರಕ್ಕಾಗಿ ರಿಜಿಸ್ಟ್ರಾರ್ ({f.get('Registrar')}) ಅನ್ನು ಕೇಳಿ."
            if young:
                c["flag"] = f"ವೆಬ್‌ಸೈಟ್ ಕೇವಲ {days} ದಿನಗಳ ಹಳೆಯದು"
        elif st == "none":
            c["say"] = "ಈ ಡೊಮೇನ್ ನೋಂದಣಿಯಾಗಿಲ್ಲ (ಅಥವಾ ನೋಂದಣಿ ಸಂಸ್ಥೆ ಪ್ರಕಟಿಸುವುದಿಲ್ಲ)."
        else:
            c["say"] = "ಡೊಮೇನ್ ನೋಂದಣಿ ಸಂಸ್ಥೆ ತಲುಪಲಿಲ್ಲ. ಏನನ್ನೂ ಪರಿಶೀಲಿಸಿಲ್ಲ."
    elif name == "Security certificates issued":
        if st == "found":
            c["say"] = f"{f.get('Certificates')} ಪ್ರಮಾಣಪತ್ರಗಳು, ಮೊದಲನೆಯದು {f.get('First certificate')} ರಂದು. ಅವುಗಳಲ್ಲಿನ ಇತರ ಹೆಸರುಗಳು ಅದೇ ಜನರ ಸಂಬಂಧಿತ ತಾಣಗಳಾಗಿರಬಹುದು."
        elif st == "none":
            c["say"] = "ಈ ಹೆಸರಿಗೆ ಯಾವುದೇ ಭದ್ರತಾ ಪ್ರಮಾಣಪತ್ರ ನೀಡಲಾಗಿಲ್ಲ."
        else:
            c["say"] = "ಪ್ರಮಾಣಪತ್ರ ದಾಖಲೆ ತಲುಪಲಿಲ್ಲ (ಅದು ಹೆಚ್ಚಾಗಿ ನಿಧಾನ). ಏನನ್ನೂ ಪರಿಶೀಲಿಸಿಲ್ಲ."
    elif name == "IMEI check digit":
        if st == "found":
            c["say"] = "ಸರಿಯಾದ ರೂಪದ IMEI. ಕಳೆದುಹೋದ ಅಥವಾ ಕಳುವಾದ ಫೋನ್ ಎಂದು ತಡೆದಿದೆಯೇ ಎಂದು ಸಂಚಾರ ಸಾಥಿ (CEIR) ನಲ್ಲಿ, ತಯಾರಿಕೆ ಮತ್ತು ಮಾದರಿಗಾಗಿ KYM ನಲ್ಲಿ ಪರಿಶೀಲಿಸಿ."
        else:
            c["say"] = "ಪರಿಶೀಲನಾ ಅಂಕಿ ತಪ್ಪಾಗಿದೆ: IMEI ತಪ್ಪಾಗಿ ನಕಲಿಸಲಾಗಿದೆ ಅಥವಾ ಅದು ನಕಲಿ / ಕ್ಲೋನ್ ಮಾಡಿದ IMEI. ಫೋನ್‌ನಿಂದ (*#06#) ಮತ್ತೆ ಪರಿಶೀಲಿಸಿ."
            c["flag"] = "IMEI ಪರಿಶೀಲನಾ ಅಂಕಿ ತಪ್ಪಾಗಿದೆ"
    c["name"] = _LIVE_NAME.get(name, name)
    for fact in c.get("facts") or []:
        fact["label"] = _FACT.get(fact["label"], fact["label"])
    return c


def _what(d: dict, live: list[dict]) -> str:
    t = d.get("target_type")
    bank = next((c.get("bank") for c in live if c.get("bank")), None)
    if t == "phone":
        circle = d.get("circle") or ""
        if "Karnataka" in circle:
            return "ಭಾರತೀಯ ಮೊಬೈಲ್ ಸಂಖ್ಯೆ. ಮೊದಲು ಕರ್ನಾಟಕದಲ್ಲಿ ನೀಡಲಾಗಿದೆ (ನಂತರ ಬೇರೆ ಸಂಸ್ಥೆ ಅಥವಾ ವಲಯಕ್ಕೆ ಹೋಗಿರಬಹುದು)."
        return "ಭಾರತೀಯ ಮೊಬೈಲ್ ಸಂಖ್ಯೆ. ಮೊದಲು ಯಾವ ರಾಜ್ಯದಲ್ಲಿ ನೀಡಲಾಯಿತು ಎಂದು ಸಂಖ್ಯೆಯಿಂದ ತಿಳಿಯಲಾಗದು."
    if t == "upi_vpa":
        return f"{d.get('psp_app')} ನಲ್ಲಿನ UPI ಐಡಿ, {d.get('sponsor_bank')} ಮೂಲಕ." \
               + (f" ಇದರಲ್ಲಿ ಮೊಬೈಲ್ ಸಂಖ್ಯೆ {d['linked_mobile']} ಇದೆ." if d.get("linked_mobile") else "")
    if t == "vehicle_plate":
        return f"{d.get('rto_office')} ({d.get('district')}, {d.get('state')}) ನಲ್ಲಿ ನೋಂದಣಿಯಾದ ವಾಹನ."
    if t == "email":
        return f"{d.get('domain')} ನಲ್ಲಿನ ಇಮೇಲ್ ವಿಳಾಸ."
    if t == "domain":
        return f"ವೆಬ್‌ಸೈಟ್: {d.get('domain')}."
    if t == "ifsc":
        return f"ಬ್ಯಾಂಕ್ ಶಾಖೆ ಕೋಡ್ (IFSC): {bank}." if bank else f"{d.get('bank_code')} ನ ಬ್ಯಾಂಕ್ ಶಾಖೆ ಕೋಡ್ (IFSC)."
    if t == "bank_account":
        if bank:
            return f"{bank} ನಲ್ಲಿನ ಬ್ಯಾಂಕ್ ಖಾತೆ (IFSC {d.get('ifsc')})."
        return "ಬ್ಯಾಂಕ್ ಖಾತೆ ಸಂಖ್ಯೆ" + (f", IFSC {d['ifsc']} ಶಾಖೆಯಲ್ಲಿ." if d.get("ifsc") else " (IFSC ನೀಡಿಲ್ಲ, ಆದ್ದರಿಂದ ಬ್ಯಾಂಕ್ ತಿಳಿದಿಲ್ಲ).")
    if t == "imei":
        return "ಮೊಬೈಲ್ ಫೋನ್‌ನ IMEI."
    if t == "handle":
        return f"ಆನ್‌ಲೈನ್ ಬಳಕೆದಾರ ಹೆಸರು: {d.get('normalized')}."
    return (f"ಹೆಸರು: {d.get('normalized')}. ಒಂದೇ ಹೆಸರು ಅನೇಕರಿಗೆ ಇರಬಹುದು; ಯಾವುದನ್ನಾದರೂ ಅವಲಂಬಿಸುವ ಮೊದಲು "
            "ತಂದೆಯ ಹೆಸರು, ವಿಳಾಸ ಅಥವಾ ವಯಸ್ಸಿನಿಂದ ಹೊಂದಿಸಿ.")


_ON = [("the number ", "ಸಂಖ್ಯೆ "), ("the registration ", "ನೋಂದಣಿ "), ("the name ", "ಹೆಸರು ")]
_ON_FIXED = {"the IMEI": "IMEI", "the IFSC": "IFSC", "the account number": "ಖಾತೆ ಸಂಖ್ಯೆ",
             "every part of the name, not together": "ಹೆಸರಿನ ಎಲ್ಲ ಭಾಗಗಳು, ಒಟ್ಟಿಗೆ ಅಲ್ಲ"}


def _on(v):
    """What a page matched on (osint_checks.match), in Kannada; the identifier itself is kept."""
    if not isinstance(v, str):
        return v
    if v in _ON_FIXED:
        return _ON_FIXED[v]
    for en, kn in _ON:
        if v.startswith(en):
            return kn + v[len(en):]
    return v


def to_kannada(report: dict) -> dict:
    """The /investigate answer, with everything an officer reads put into Kannada."""
    r = copy.deepcopy(report)
    fd = r.get("forensic_decoder") or {}
    fd["target_label"] = _LABEL.get(fd.get("target_label"), fd.get("target_label"))
    for f in fd.get("decoded_fields") or []:
        f["label"] = _FIELD.get(f["label"], f["label"])

    live = [_live(c) for c in r.get("live_checks") or []]
    r["live_checks"] = live

    official = []
    for o in r.get("official_checks") or []:
        k = _OFFICIAL.get(o.get("name"))
        official.append({**o, "key": o.get("name"), "name": k[0], "what": k[1], "how": k[2], "step": k[3]} if k else o)
    r["official_checks"] = official

    web = r.get("web") or {}
    if web.get("claims"):
        r["web"] = {**web, "claims": [{**c, "matched_on": _on(c.get("matched_on"))} for c in web["claims"]]}

    web = r.get("web") or {}
    claims = web.get("claims") or []
    checked = web.get("pages_checked", 0)
    if not web.get("reached", True):
        web_line = "ವೆಬ್ ಹುಡುಕಾಟ ಈಗ ತಲುಪಲಿಲ್ಲ, ಆದ್ದರಿಂದ ಅಲ್ಲಿ ಏನನ್ನೂ ಪರಿಶೀಲಿಸಿಲ್ಲ. ಒಂದು ನಿಮಿಷದ ನಂತರ ಮತ್ತೆ ಚಲಾಯಿಸಿ."
    elif not claims:
        web_line = f"ಯಾವುದೇ ಸಾರ್ವಜನಿಕ ಪುಟ ಇದನ್ನು ಉಲ್ಲೇಖಿಸಿಲ್ಲ: {checked} ಪುಟಗಳನ್ನು ಪರಿಶೀಲಿಸಲಾಗಿದೆ, ಯಾವುದರಲ್ಲೂ ಇಲ್ಲ." if checked \
            else "ಯಾವುದೇ ಸಾರ್ವಜನಿಕ ಪುಟ ಇದನ್ನು ಉಲ್ಲೇಖಿಸಿಲ್ಲ."
    else:
        kinds: dict[str, int] = {}
        for c in claims:
            k = _KIND.get(c.get("category"), "ಇತರ ವೆಬ್‌ಸೈಟ್")
            kinds[k] = kinds.get(k, 0) + 1
        parts = ", ".join(f"{v} {k}" for k, v in kinds.items())
        web_line = f"{checked} ರಲ್ಲಿ {len(claims)} ಸಾರ್ವಜನಿಕ ಪುಟಗಳು ಇದನ್ನು ಉಲ್ಲೇಖಿಸುತ್ತವೆ ({parts})."
        risky = sorted({w for c in claims for w in c.get("matched_keywords") or []})
        if risky:
            web_line += " ಕೆಲವು ಇವುಗಳ ಬಗ್ಗೆಯೂ ಹೇಳುತ್ತವೆ: " + ", ".join(risky[:4]) + "."

    flags = [c["flag"] for c in live if c.get("flag")]
    flags += [f"ಈ ಪದಗಳಿರುವ ಪುಟದಲ್ಲಿ ಹೆಸರಿದೆ: {', '.join(c['matched_keywords'][:3])}" for c in claims[:3] if c.get("matched_keywords")]
    steps = [c["do"] for c in live if c.get("status") == "found" and c.get("do")]
    steps += [o.get("step") for o in official[:3] if o.get("step")]
    notice = r.get("statutory_requisition") or {}
    if notice.get("available"):
        steps.append(f"ಕರಡು ನೋಟಿಸ್ ಅನ್ನು {notice.get('recipient', '').split(' — ')[0]} ಗೆ ಕಳುಹಿಸಿ ({notice.get('statute', '').split(',')[0]}).")
    steps.append("ಏನನ್ನು, ಯಾವಾಗ, ಎಲ್ಲಿ ಪರಿಶೀಲಿಸಲಾಯಿತು ಎಂದು ಪ್ರಕರಣ ದಿನಚರಿಯಲ್ಲಿ ಬರೆಯಿರಿ; ದೃಢೀಕರಿಸುವವರೆಗೆ ಇವು ಸುಳಿವುಗಳು, ಸಾಕ್ಷ್ಯವಲ್ಲ.")

    if r.get("brief"):
        r["brief"] = {"what": _what(fd, live), "web": web_line, "flags": flags, "next": steps[:6],
                      "live": [{"name": c["name"], "status": c["status"], "say": c["say"]} for c in live]}
    r["lang"] = "kn"
    return r
