"""
Antar — Standalone Multi-Module OSINT & Forensic Reconnaissance Engine
======================================================================
Operates as an isolated, standalone open-source intelligence and forensic decoding
workbench for Karnataka State Police (KSP) investigators:
  1. ForensicDecoderModule: Deterministic Indian identifier decoding (70+ Karnataka RTOs,
     30+ UPI VPA Payment Service Providers & Nodal Banks, Indian E.164 Telecom & Email/Handle).
  2. Link map: the items an identifier points to (RTO, bank, circle), built from the identifier itself.
  3. Phone-number decoder: E.164 form, TRAI series and the circle the number was first allocated to.
  4. Handle check links: public profile and court-index links for an officer to open by hand.
  5. Step log: what was done, in order.
  None of these runs an outside tool or opens a page; each works from the identifier typed in.
  The output keys keep their earlier names (maltego_linkage, phone_infoga, sherlock_handles,
  bbot_scan_tree) because the Search page and the tests read them.
  6. StatutoryRequisitionModule: BNSS §94 / §106 & IT Act law-enforcement notice generator.

CRITICAL ISOLATION & SECURITY GUARDRAILS:
  • Standalone module: NEVER queries `main.db`, never touches FIRs, and never mutates Antar state.
  • All external OSINT/recon outputs are strictly quarantined (`unverified=True`, `status: "quarantined"`).
  • OSINT findings NEVER auto-merge into institutional facts.
"""

from __future__ import annotations

import hashlib
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any


# ── Karnataka RTO Registry (KA-01 to KA-70) ──────────────────────────────────
_KA_RTO_MAP: dict[str, tuple[str, str]] = {
    "KA-01": ("Bengaluru Central (Koramangala)", "Bengaluru City"),
    "KA-02": ("Bengaluru West (Rajajinagar)", "Bengaluru City"),
    "KA-03": ("Bengaluru East (Indiranagar)", "Bengaluru City"),
    "KA-04": ("Bengaluru North (Yeshwanthpur)", "Bengaluru City"),
    "KA-05": ("Bengaluru South (Jayanagar)", "Bengaluru City"),
    "KA-06": ("Tumakuru RTO", "Tumakuru"),
    "KA-07": ("Kolar RTO", "Kolar"),
    "KA-08": ("Kolar Gold Fields (KGF)", "Kolar"),
    "KA-09": ("Mysuru West RTO", "Mysuru"),
    "KA-10": ("Chamarajanagar RTO", "Chamarajanagar"),
    "KA-11": ("Mandya RTO", "Mandya"),
    "KA-12": ("Madikeri (Kodagu) RTO", "Kodagu"),
    "KA-13": ("Hassan RTO", "Hassan"),
    "KA-14": ("Shivamogga RTO", "Shivamogga"),
    "KA-15": ("Sagara ARTO", "Shivamogga"),
    "KA-16": ("Chitradurga RTO", "Chitradurga"),
    "KA-17": ("Davanagere RTO", "Davanagere"),
    "KA-18": ("Chikkamagaluru RTO", "Chikkamagaluru"),
    "KA-19": ("Mangaluru RTO", "Dakshina Kannada"),
    "KA-20": ("Udupi RTO", "Udupi"),
    "KA-21": ("Puttur ARTO", "Dakshina Kannada"),
    "KA-22": ("Belagavi RTO", "Belagavi"),
    "KA-23": ("Chikkodi ARTO", "Belagavi"),
    "KA-24": ("Bailhongal ARTO", "Belagavi"),
    "KA-25": ("Dharwad / Hubballi West RTO", "Dharwad"),
    "KA-26": ("Gadag RTO", "Gadag"),
    "KA-27": ("Haveri RTO", "Haveri"),
    "KA-28": ("Vijayapura (Bijapur) RTO", "Vijayapura"),
    "KA-29": ("Bagalkot RTO", "Bagalkot"),
    "KA-30": ("Karwar RTO", "Uttara Kannada"),
    "KA-31": ("Sirsi ARTO", "Uttara Kannada"),
    "KA-32": ("Kalaburagi (Gulbarga) RTO", "Kalaburagi"),
    "KA-33": ("Yadgir RTO", "Yadgir"),
    "KA-34": ("Ballari RTO", "Ballari"),
    "KA-35": ("Hosapete ARTO", "Vijayanagara"),
    "KA-36": ("Raichur RTO", "Raichur"),
    "KA-37": ("Koppal RTO", "Koppal"),
    "KA-38": ("Bidar RTO", "Bidar"),
    "KA-39": ("Bhalki ARTO", "Bidar"),
    "KA-40": ("Chikkaballapura RTO", "Chikkaballapura"),
    "KA-41": ("Jnana Bharathi (Rajarajeshwari Nagar)", "Bengaluru City"),
    "KA-42": ("Ramanagara RTO", "Ramanagara"),
    "KA-43": ("Devanahalli (KIAL Corridor)", "Bengaluru Rural"),
    "KA-44": ("Tiptur ARTO", "Tumakuru"),
    "KA-45": ("Hunsur ARTO", "Mysuru"),
    "KA-46": ("Sakleshpur ARTO", "Hassan"),
    "KA-47": ("Honnavar ARTO", "Uttara Kannada"),
    "KA-48": ("Jamkhandi ARTO", "Bagalkot"),
    "KA-49": ("Gokak ARTO", "Belagavi"),
    "KA-50": ("Yelahanka RTO", "Bengaluru City"),
    "KA-51": ("Electronic City RTO", "Bengaluru City"),
    "KA-52": ("Nelamangala ARTO", "Bengaluru Rural"),
    "KA-53": ("Krishnarajapuram (Whitefield) RTO", "Bengaluru City"),
    "KA-54": ("Nagamangala ARTO", "Mandya"),
    "KA-55": ("Mysuru East RTO", "Mysuru"),
    "KA-56": ("Basavakalyan ARTO", "Bidar"),
    "KA-57": ("Shantinagar (STU / Commercial)", "Bengaluru City"),
    "KA-59": ("Chandapura (Anekal) ARTO", "Bengaluru Urban"),
    "KA-63": ("Hubballi East RTO", "Dharwad"),
    "KA-64": ("Madhugiri ARTO", "Tumakuru"),
    "KA-65": ("Dandeli ARTO", "Uttara Kannada"),
    "KA-66": ("Tarikere ARTO", "Chikkamagaluru"),
    "KA-67": ("Sedam ARTO", "Kalaburagi"),
    "KA-68": ("Ranebennur ARTO", "Haveri"),
    "KA-69": ("Ramdurg ARTO", "Belagavi"),
    "KA-70": ("Bantwal ARTO", "Dakshina Kannada"),
}

_STATE_CODE_MAP: dict[str, str] = {
    "KA": "Karnataka", "MH": "Maharashtra", "TN": "Tamil Nadu", "KL": "Kerala",
    "AP": "Andhra Pradesh", "TS": "Telangana", "TG": "Telangana", "DL": "Delhi NCT",
    "UP": "Uttar Pradesh", "GJ": "Gujarat", "RJ": "Rajasthan", "WB": "West Bengal",
    "HR": "Haryana", "PB": "Punjab", "MP": "Madhya Pradesh", "GA": "Goa",
    "OR": "Odisha", "OD": "Odisha", "BR": "Bihar", "JH": "Jharkhand",
    "CG": "Chhattisgarh", "AS": "Assam", "UK": "Uttarakhand", "HP": "Himachal Pradesh",
    "BH": "All-India Bharat Series (BH)",
}

# ── Indian UPI Payment Service Provider (PSP) & Nodal Bank Directory ─────────
_UPI_PSP_MAP: dict[str, tuple[str, str]] = {
    "ybl": ("PhonePe", "Yes Bank Ltd"),
    "ibl": ("PhonePe", "ICICI Bank Ltd"),
    "axl": ("PhonePe", "Axis Bank Ltd"),
    "okaxis": ("Google Pay (GPay)", "Axis Bank Ltd"),
    "okhdfcbank": ("Google Pay (GPay)", "HDFC Bank Ltd"),
    "oksbi": ("Google Pay (GPay)", "State Bank of India (SBI)"),
    "okicici": ("Google Pay (GPay)", "ICICI Bank Ltd"),
    "paytm": ("Paytm", "Paytm Payments Bank / Axis / Yes Bank"),
    "ptyes": ("Paytm", "Yes Bank Ltd"),
    "ptaxis": ("Paytm", "Axis Bank Ltd"),
    "pthdfc": ("Paytm", "HDFC Bank Ltd"),
    "ptsbi": ("Paytm", "State Bank of India (SBI)"),
    "apl": ("Amazon Pay", "Axis Bank Ltd"),
    "rapl": ("Amazon Pay", "RBL Bank Ltd"),
    "yapl": ("Amazon Pay", "Yes Bank Ltd"),
    "upi": ("BHIM (NPCI)", "NPCI / Linked Issuer Bank"),
    "fbl": ("Federal Bank / Fi / Jupiter", "Federal Bank Ltd"),
    "axisb": ("CRED / Axis Pay", "Axis Bank Ltd"),
    "yescred": ("CRED", "Yes Bank Ltd"),
    "waaxis": ("WhatsApp Pay", "Axis Bank Ltd"),
    "wahdfcbank": ("WhatsApp Pay", "HDFC Bank Ltd"),
    "waicici": ("WhatsApp Pay", "ICICI Bank Ltd"),
    "wasbi": ("WhatsApp Pay", "State Bank of India (SBI)"),
    "sbi": ("YONO SBI", "State Bank of India (SBI)"),
    "icici": ("iMobile Pay", "ICICI Bank Ltd"),
    "hdfcbank": ("PayZapp / HDFC", "HDFC Bank Ltd"),
    "kotak": ("Kotak 811", "Kotak Mahindra Bank"),
    "indus": ("IndusPay", "IndusInd Bank"),
    "barodampay": ("bob World", "Bank of Baroda"),
    "cnrb": ("Canara ai1", "Canara Bank (Bengaluru HQ)"),
    "kbl": ("KBL Mobile", "Karnataka Bank Ltd (Mangaluru HQ)"),
}

_PLATE_RE = re.compile(
    r"^\s*([A-Z]{2})[\s\-]?(\d{1,2})(?:[\s\-]?([A-Z]{1,3}))?(?:[\s\-]?(\d{1,4}))?\s*$",
    re.IGNORECASE,
)
_BH_PLATE_RE = re.compile(
    r"^\s*(\d{2})\s*BH\s*(\d{4})\s*([A-Z]{1,2})\s*$",
    re.IGNORECASE,
)


def _classify_and_decode_target(query: str) -> dict[str, Any]:
    """Deterministically classifies the target and decodes Indian forensic attributes."""
    q = query.strip()
    digits = re.sub(r"\D", "", q)
    q_hash = hashlib.sha256(q.lower().encode("utf-8")).hexdigest()[:16].upper()

    # 1. Check Indian Vehicle Registration Plate (Standard or BH-Series)
    m_plate = _PLATE_RE.match(q)
    m_bh = _BH_PLATE_RE.match(q)
    if m_bh or (m_plate and m_plate.group(1).upper() in _STATE_CODE_MAP and (m_plate.group(4) or len(q) <= 6)):
        if m_bh:
            yr, num, series = m_bh.group(1), m_bh.group(2), m_bh.group(3).upper()
            normalized = f"{yr}-BH-{num}-{series}"
            return {
                "target_type": "vehicle_plate",
                "target_label": "Bharat Series (BH) Vehicle Registration",
                "normalized": normalized,
                "state": "All-India Bharat Series (MoRTH)",
                "rto_code": f"{yr}-BH",
                "rto_office": "Central Vahan National Registry",
                "district": "Pan-India Transferable",
                "series": series,
                "number": num,
                "sha256_fingerprint": f"HASH-{q_hash}",
                "decoded_fields": [
                    {"label": "Normalized Plate", "value": normalized},
                    {"label": "Registration Class", "value": f"Bharat Series (20{yr})"},
                    {"label": "Registry Authority", "value": "MoRTH Vahan Central Database"},
                    {"label": "Surveillance Vector", "value": "NHAI NETC FASTag & Smart City ANPR"},
                ],
                "pivots": [
                    {
                        "label": "Parivahan / Vahan e-Services Portal",
                        "url": "https://parivahan.gov.in/parivahan/",
                    },
                    {
                        "label": "Open-Web Plate Mention Scan",
                        "url": f"https://duckduckgo.com/?q={urllib.parse.quote(normalized)}",
                    },
                ],
            }

        st = m_plate.group(1).upper()
        rto_num = int(m_plate.group(2))
        rto_code = f"{st}-{rto_num:02d}"
        series = (m_plate.group(3) or "").upper()
        reg_no = (m_plate.group(4) or "").zfill(4) if m_plate.group(4) else ""
        normalized = "-".join(p for p in (st, f"{rto_num:02d}", series, reg_no) if p)
        state_name = _STATE_CODE_MAP.get(st, "India")
        rto_office, district = _KA_RTO_MAP.get(
            rto_code,
            (f"{state_name} Regional Transport Office ({rto_code})", state_name),
        )
        return {
            "target_type": "vehicle_plate",
            "target_label": "Indian Vehicle Registration / RTO Identifier",
            "normalized": normalized,
            "state": state_name,
            "rto_code": rto_code,
            "rto_office": rto_office,
            "district": district,
            "series": series or "RTO Prefix Only",
            "number": reg_no or "N/A",
            "sha256_fingerprint": f"HASH-{q_hash}",
            "decoded_fields": [
                {"label": "Normalized Registration", "value": normalized},
                {"label": "RTO Code & Office", "value": f"{rto_code} · {rto_office}"},
                {"label": "Revenue District / State", "value": f"{district}, {state_name}"},
                {"label": "Series / Sequence", "value": f"Series {series or '—'} · No. {reg_no or '—'}"},
                {"label": "Telemetry Channels", "value": "Vahan 4.0 · e-Challan · NETC FASTag · ICCC ANPR"},
            ],
            "pivots": [
                {
                    "label": "Karnataka Transport / Vahan Lookup",
                    "url": "https://parivahan.gov.in/parivahan/",
                },
                {
                    "label": "Open-Web Registration Trace",
                    "url": f"https://duckduckgo.com/?q={urllib.parse.quote(normalized + ' OR ' + rto_code)}",
                },
            ],
        }

    # 2. Check UPI Virtual Payment Address (VPA) vs Email
    if "@" in q and not q.startswith("@") and " " not in q:
        local_part, domain_part = q.split("@", 1)
        dom_low = domain_part.lower().strip()
        local_digits = re.sub(r"\D", "", local_part)
        if "." not in dom_low or dom_low in _UPI_PSP_MAP:
            psp_app, sponsor_bank = _UPI_PSP_MAP.get(
                dom_low,
                ("UPI Payment Handle", f"NPCI PSP (@{dom_low})"),
            )
            linked_mobile = (
                f"+91-{local_digits[-10:]}"
                if len(local_digits) >= 10 and local_digits[-10] in "6789"
                else None
            )
            return {
                "target_type": "upi_vpa",
                "target_label": "UPI Virtual Payment Address (Financial Handle)",
                "normalized": f"{local_part.lower()}@{dom_low}",
                "vpa_prefix": local_part,
                "psp_handle": f"@{dom_low}",
                "psp_app": psp_app,
                "sponsor_bank": sponsor_bank,
                "linked_mobile": linked_mobile,
                "sha256_fingerprint": f"HASH-{q_hash}",
                "decoded_fields": [
                    {"label": "Normalized UPI VPA", "value": f"{local_part.lower()}@{dom_low}"},
                    {"label": "TPAP / Payment App", "value": psp_app},
                    {"label": "Sponsoring PSP Bank", "value": sponsor_bank},
                    {
                        "label": "Prefix Attribution",
                        "value": f"Embedded Mobile {linked_mobile}" if linked_mobile else f"Custom Alias '{local_part}'",
                    },
                    {"label": "Escalation Channel", "value": "NPCI Law Enforcement Cell & NCRP 1930"},
                ],
                "pivots": [
                    {
                        "label": "Open-Web Scam / Mule Account Check",
                        "url": f"https://duckduckgo.com/?q={urllib.parse.quote(q + ' fraud OR scam OR upi')}",
                    },
                    {
                        "label": "NCRP National Cyber Crime Portal",
                        "url": "https://cybercrime.gov.in/",
                    },
                ],
            }
        else:
            return {
                "target_type": "email",
                "target_label": "Electronic Mail Identifier",
                "normalized": q.lower(),
                "local_part": local_part,
                "domain": dom_low,
                "sha256_fingerprint": f"HASH-{q_hash}",
                "decoded_fields": [
                    {"label": "Normalized Email", "value": q.lower()},
                    {"label": "Username Prefix", "value": local_part},
                    {"label": "Mail Domain", "value": dom_low},
                    {"label": "Evidence Hash (SHA-256)", "value": f"HASH-{q_hash}"},
                ],
                "pivots": [
                    {
                        "label": "Open-Web Email Exposure Dork",
                        "url": f"https://duckduckgo.com/?q={urllib.parse.quote(q.lower())}",
                    },
                    {
                        "label": "Domain Public Footprint",
                        "url": f"https://duckduckgo.com/?q={urllib.parse.quote('site:' + dom_low)}",
                    },
                ],
            }

    # 3. Check Indian Phone / Mobile Number or Hash
    is_phone = (
        (len(digits) == 10 and digits[0] in "6789")
        or (len(digits) == 12 and digits.startswith("91") and digits[2] in "6789")
        or (len(digits) == 11 and digits.startswith("0") and digits[1] in "6789")
        or q.upper().startswith(("HASH-", "PH-"))
    )
    if is_phone:
        nat_num = digits[-10:] if len(digits) >= 10 else digits
        e164 = f"+91-{nat_num}" if len(nat_num) == 10 else q
        first_digit = nat_num[0] if nat_num else ""
        series_map = {
            "9": "TRAI 9-Series (Primary GSM / Legacy Mobile Allocation)",
            "8": "TRAI 8-Series (GSM / 4G LTE Allocation)",
            "7": "TRAI 7-Series (4G LTE / 5G Allocation)",
            "6": "TRAI 6-Series (VoLTE / 4G-5G Allocation)",
        }
        prefix4 = nat_num[:4] if len(nat_num) >= 4 else ""
        if prefix4.startswith(("9845", "9900", "9880", "9945", "9740", "9686", "8971")):
            circle_hint = "First allocated in Karnataka circle (may have been ported since)"
        elif prefix4.startswith(("9844", "9901", "9886", "9731", "9611", "9448", "9449", "9480")):
            circle_hint = "First allocated in Karnataka circle, BSNL block (may have been ported since)"
        elif len(nat_num) == 10:
            circle_hint = "Indian mobile number; the circle cannot be told from the number (numbers can be ported)"
        else:
            circle_hint = "Cryptographic Phone Hash Identifier"

        ph_hash = hashlib.sha256(nat_num.encode("utf-8")).hexdigest()[:16].upper() if nat_num else q_hash
        return {
            "target_type": "phone",
            "target_label": "Indian Mobile / Telecom Subscriber Identifier",
            "normalized": e164,
            "national_number": nat_num,
            "trai_series": series_map.get(first_digit, "Cryptographic Telecom Hash"),
            "circle": circle_hint,
            "sha256_fingerprint": f"HASH-{ph_hash}",
            "decoded_fields": [
                {"label": "E.164 Normalized", "value": e164},
                {"label": "TRAI Numbering Series", "value": series_map.get(first_digit, "Hash / Non-standard")},
                {"label": "Circle first allocated", "value": circle_hint},
                {"label": "Note", "value": "Mobile numbers can move between operators and circles (MNP); the current operator comes only from the operator or the MNP clearing house."},
                {"label": "SHA-256 Privacy Hash", "value": f"HASH-{ph_hash}"},
                {"label": "Statutory Nodal", "value": "DoT LSA Karnataka / TSP Nodal Officer (BNSS §94)"},
            ],
            "pivots": [
                {
                    "label": "WhatsApp Public Surface Check",
                    "url": f"https://wa.me/91{nat_num}" if len(nat_num) == 10 else "https://web.whatsapp.com/",
                },
                {
                    "label": "Open-Web Number Mention Scan",
                    "url": f"https://duckduckgo.com/?q={urllib.parse.quote(nat_num or q)}",
                },
            ],
        }

    # 4. Handle vs Named Person / Entity
    is_handle = q.startswith("@") or (" " not in q and any(c in q for c in ("_", ".", "-")))
    clean_handle = re.sub(r"[^A-Za-z0-9_.-]", "", q.lstrip("@")).lower() or "target"
    return {
        "target_type": "handle" if is_handle else "person_or_entity",
        "target_label": "Digital Handle / Alias" if is_handle else "Named Subject / Location / Entity",
        "normalized": f"@{clean_handle}" if is_handle else q,
        "clean_handle": clean_handle,
        "sha256_fingerprint": f"HASH-{q_hash}",
        "decoded_fields": [
            {"label": "Target Subject", "value": q},
            {"label": "Classification", "value": "Digital Username / Handle" if is_handle else "Person / Alias / Entity"},
            {"label": "Normalized Handle", "value": f"@{clean_handle}"},
            {"label": "Session Fingerprint", "value": f"HASH-{q_hash}"},
        ],
        "pivots": [
            {
                "label": "Indian Kanoon Judicial Archive Search",
                "url": f"https://indiankanoon.org/search/?formInput={urllib.parse.quote(q)}",
            },
            {
                "label": "Karnataka News & Open-Web Search",
                "url": f"https://duckduckgo.com/?q={urllib.parse.quote(q + ' karnataka OR police OR court')}",
            },
        ],
    }


def _build_statutory_requisition(query: str, decoded: dict[str, Any]) -> dict[str, Any]:
    """Generates a ready-to-use BNSS §94 / §106 & IT Act law-enforcement requisition draft."""
    ttype = decoded["target_type"]
    norm = decoded["normalized"]
    ts_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if ttype == "phone":
        return {
            "available": True,
        "statute": "Section 94, Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023 (formerly §91 CrPC)",
            "recipient": "Nodal Law Enforcement Officer — Telecom Service Provider (Airtel / Jio / Vi / BSNL), Karnataka LSA",
            "subject": f"URGENT REQUISITION: Subscriber KYC (CAF), CDR, IMEI History & IPDR for {norm}",
            "records_requested": [
                f"1. Certified Customer Application Form (CAF) & PoI/PoA KYC documents for subscriber {norm}.",
                "2. Call Detail Records (CDR) & SMS headers with Cell-ID / Tower Lat-Long for the preceding 90 days.",
                "3. IMEI & IMSI numbers mapped to the MSISDN, including handset change history.",
                "4. Destination IP / Port logs (IPDR) under Section 63 BSA (formerly §65B IEA) certificate.",
            ],
            "template_text": (
                f"NOTICE UNDER SECTION 94 OF THE BHARATIYA NAGARIK SURAKSHA SANHITA (BNSS), 2023\n"
                f"To: The Nodal Officer (Law Enforcement), Telecom Circle Karnataka\n"
                f"Timestamp: {ts_str}\n"
                f"Target Identifier: {norm} ({decoded.get('sha256_fingerprint')})\n\n"
                f"Whereas an investigation/enquiry is being conducted by Karnataka State Police, and the following "
                f"electronic telecom records for subscriber number {norm} are necessary and desirable for the "
                f"purpose of the investigation:\n"
                f"  (a) Certified CAF & KYC documents along with alternate contact number;\n"
                f"  (b) Call Detail Records (CDR) with Cell Tower IDs & azimuth coordinates;\n"
                f"  (c) Associated IMEI/IMSI history and Section 63 Bharatiya Sakshya Adhiniyam (BSA) certificate.\n"
                f"You are hereby directed to produce the above records expeditiously."
            ),
        }

    if ttype == "upi_vpa":
        bank = decoded.get("sponsor_bank", "Sponsoring PSP Bank")
        psp = decoded.get("psp_app", "TPAP Provider")
        return {
            "available": True,
        "statute": "Sections 94 & 106, Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023",
            "recipient": f"Nodal Cyber Cell Officer — {bank} & {psp} / NPCI Law Enforcement Desk",
            "subject": f"REQUISITION FOR UPI VPA KYC, LINKED BANK ACCOUNT & TRANSACTION TRAIL: {norm}",
            "records_requested": [
                f"1. Full KYC, PAN, Aadhaar-masked reference, and linked Savings/Current Account number for UPI VPA {norm}.",
                "2. Registered mobile number, device fingerprint (Device ID / IMEI), and registration IP logs.",
                "3. Counterparty statement of UPI UTR inflows/outflows & beneficiary bank IFSC details.",
                "4. Immediate lien / debit freeze on disputed proceeds under Section 106 BNSS / NCRP 1930 protocol.",
            ],
            "template_text": (
                f"NOTICE UNDER SECTIONS 94 & 106 OF THE BHARATIYA NAGARIK SURAKSHA SANHITA (BNSS), 2023\n"
                f"To: The Nodal Officer, {bank} / {psp} (NPCI UPI Member)\n"
                f"Timestamp: {ts_str}\n"
                f"Target UPI VPA: {norm}\n\n"
                f"In exercise of powers under Section 94 BNSS 2023, you are requested to furnish:\n"
                f"  (a) Account holder name, primary account number, IFSC, and KYC documents mapped to VPA {norm};\n"
                f"  (b) Registered mobile number ({decoded.get('linked_mobile') or 'on record'}), Device ID, and login IP logs;\n"
                f"  (c) Complete UTR transaction statement and Layer-1 beneficiary bank details.\n"
                f"Supported by a certificate under Section 63 of the Bharatiya Sakshya Adhiniyam (BSA), 2023."
            ),
        }

    if ttype == "vehicle_plate":
        rto = decoded.get("rto_office", "Regional Transport Office")
        return {
            "available": True,
        "statute": "Section 94, Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023 & Motor Vehicles Act",
            "recipient": f"Regional Transport Officer ({rto}) / ICCC ANPR & NHAI NETC FASTag Nodal Cell",
            "subject": f"REQUISITION FOR VAHAN B-EXTRACT, FASTAG TOLL LOGS & ANPR SIGHTINGS: {norm}",
            "records_requested": [
                f"1. Certified Vahan B-Register Extract (current & prior ownership, chassis/engine no., hypothecation) for {norm}.",
                "2. Registered owner mobile number & address submitted at registration / insurance renewal.",
                "3. NHAI NETC FASTag toll plaza passage timestamps & lane camera captures.",
                "4. Bengaluru / District Smart City ICCC ANPR camera sightings.",
            ],
            "template_text": (
                f"NOTICE UNDER SECTION 94 OF THE BHARATIYA NAGARIK SURAKSHA SANHITA (BNSS), 2023\n"
                f"To: The Regional Transport Officer ({rto}) & ICCC Command Center\n"
                f"Timestamp: {ts_str}\n"
                f"Vehicle Registration: {norm}\n\n"
                f"Please furnish for official police investigation:\n"
                f"  (a) Certified B-Extract of Registration {norm} including Engine/Chassis No. and Owner Mobile;\n"
                f"  (b) Hypothecation / Financer details and active insurance policy particulars;\n"
                f"  (c) FASTag wallet tag-ID and toll plaza movement logs / ANPR corridor captures."
            ),
        }

    if ttype != "handle":
        # A personal name or a place has no holder to send a notice to: a §94 notice goes to
        # whoever holds the record (an operator, a bank, an RTO, a platform). Drafting one
        # addressed to nobody invited it to be sent somewhere it should not go.
        return {
            "available": False,
            "statute": "",
            "recipient": "",
            "subject": "",
            "records_requested": [],
            "template_text": "",
            "reason": ("No notice was drafted. A Section 94 BNSS notice goes to whoever holds the record, so it needs "
                       "an identifier with a holder: a phone number (operator), a UPI ID (bank), a vehicle number (RTO) "
                       "or an online handle (platform). A name alone has no recipient."),
        }
    return {
        "available": True,
        "statute": "Section 94, BNSS 2023 & Section 79(3)(b) Information Technology Act, 2000",
        "recipient": "Grievance / Nodal Law Enforcement Officer — Significant Social Media Intermediary (SSMI)",
        "subject": f"PRESERVATION & BASIC SUBSCRIBER INFORMATION (BSI) REQUEST FOR: {norm}",
        "records_requested": [
            f"1. Basic Subscriber Information (BSI) including registration email, phone number, and creation timestamp for '{norm}'.",
            "2. Login IP addresses (with port and UTC timestamps) for the last 60 days.",
            "3. Account preservation for 90 days pending formal legal process.",
        ],
        "template_text": (
            f"LAW ENFORCEMENT PRESERVATION & PRODUCTION NOTICE (SECTION 94 BNSS, 2023)\n"
            f"To: The Resident Grievance / Nodal Officer (India)\n"
            f"Timestamp: {ts_str}\n"
            f"Target Subject / Handle: {norm}\n\n"
            f"Pursuant to Section 94 of the Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023, please preserve and "
            f"furnish Basic Subscriber Information (registration MSISDN, email, creation IP, and recent access IP logs) "
            f"associated with target identifier '{norm}'."
        ),
    }


def run_multi_module_recon(
    query: str,
    internal_rows: list[dict] | dict | None = None,
    sources: list[str] | None = None,
    depth: str = "standard",
) -> dict[str, Any]:
    """
    Runs concurrent standalone reconnaissance and Indian forensic decoding modules over `query`.
    When called from `/api/osint/recon`, `internal_rows` is None — this module NEVER touches
    the FIR database or Antar core state.
    """
    # The same screen the open-web search applies: visible text only, bounded, and nothing
    # instruction-shaped. Unscreened, "ignore previous instructions ..." was copied into the
    # step log and into the BNSS notice draft.
    from app.core.rag_security import normalize_untrusted, detect_injection
    query_clean = normalize_untrusted(query or "", max_len=120).strip()
    refused = bool(query_clean) and bool(detect_injection(query_clean))
    if not query_clean or refused:
        return {
            "refused": refused,
            "reason": ("The text entered reads as an instruction, not an identifier, so nothing was decoded."
                       if refused else "No identifier entered."),
            "query": "",
            "isolation_mode": "STANDALONE_NO_FIR_ACCESS",
            "forensic_decoder": {},
            "statutory_requisition": {},
            "maltego_linkage": {"nodes": [], "edges": []},
            "phone_infoga": {},
            "sherlock_handles": [],
            "bbot_scan_tree": [],
            "osint_claims": [],
            "corroboration_summary": {"total_claims": 0, "corroborated_count": 0},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Optional legacy parameter support for unit tests only; production API passes None.
    raw_rows = internal_rows or []
    records: list[dict] = []
    if isinstance(raw_rows, list):
        records = [r for r in raw_rows if isinstance(r, dict)]
    elif isinstance(raw_rows, dict):
        for v in raw_rows.values():
            if isinstance(v, list):
                records.extend([r for r in v if isinstance(r, dict)])
            elif isinstance(v, dict):
                records.append(v)
    rows = records

    decoded = _classify_and_decode_target(query_clean)
    requisition = _build_statutory_requisition(query_clean, decoded)

    # 1. Step log
    scan_tree = [
        {
            "id": "EVT-01",
            "event_type": "SCAN_INIT",
            "source": "StepLog",
            "detail": (
                f"Initialized standalone OSINT reconnaissance for target '{query_clean}' "
                f"(depth={depth}, isolation=NO_FIR_ACCESS)"
            ),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": "EVT-02",
            "event_type": "FORENSIC_DECODE",
            "source": "IndianForensicDecoder",
            "detail": f"Classified target as [{decoded['target_type'].upper()}]: {decoded['target_label']} ({decoded['normalized']})",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    ]

    # 2. Phone-number decoder
    phone_info = _run_phone_infoga_module(query_clean, decoded, rows, scan_tree)

    # 3. Link map
    maltego_graph = _run_maltego_linkage_module(query_clean, decoded, rows, scan_tree)

    # 4. Handle check links (nothing is opened)
    sherlock_handles = _run_sherlock_module(query_clean, decoded, scan_tree)

    # 5. OSINT Verification Vectors & Corroboration
    osint_claims = _run_osint_corroboration(query_clean, decoded, rows, sherlock_handles, scan_tree)

    corroborated_count = sum(1 for c in osint_claims if c.get("corroborates"))

    return {
        "query": query_clean,
        "isolation_mode": "STANDALONE_NO_FIR_ACCESS",
        "forensic_decoder": decoded,
        "statutory_requisition": requisition,
        "maltego_linkage": maltego_graph,
        "phone_infoga": phone_info,
        "sherlock_handles": sherlock_handles,
        "bbot_scan_tree": scan_tree,
        "osint_claims": osint_claims,
        "corroboration_summary": {
            "total_claims": len(osint_claims),
            "corroborated_count": corroborated_count,
            "quarantine_status": "ACTIVE (Strict §0.4-2 standalone quarantine — zero FIR coupling)",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _run_phone_infoga_module(
    query: str,
    decoded: dict[str, Any],
    rows: list[dict],
    scan_tree: list[dict],
) -> dict[str, Any]:
    """Performs Indian telecom numbering plan, E.164, and embedded MSISDN analysis."""
    digits_only = re.sub(r"\D", "", query)
    embedded_mobile = decoded.get("linked_mobile")
    is_phone_query = (
        decoded.get("target_type") == "phone"
        or bool(embedded_mobile)
        or len(digits_only) >= 8
        or query.upper().startswith(("HASH-", "PH-"))
    )

    matching_firs = []
    associated_zones = set()
    associated_names = set()

    for r in rows:
        ph = str(r.get("phone_hash", ""))
        row_str = str(r).lower()
        if (ph and query in ph) or query.lower() in row_str:
            matching_firs.append(r.get("id") or r.get("fir_num", "UNKNOWN"))
            if r.get("zone"):
                associated_zones.add(r["zone"])
            if r.get("suspect_name"):
                associated_names.add(r["suspect_name"])

    nat_num = decoded.get("national_number") or (re.sub(r"\D", "", embedded_mobile)[-10:] if embedded_mobile else "")
    e164_val = (
        decoded.get("normalized")
        if decoded.get("target_type") == "phone"
        else (embedded_mobile or (f"+91-{digits_only[-10:]}" if len(digits_only) >= 10 else query))
    )
    line_classification = (
        decoded.get("trai_series")
        if decoded.get("target_type") == "phone"
        else ("Embedded Mobile in UPI VPA" if embedded_mobile else ("Cellular / Mobile Telecom" if is_phone_query else "Alphanumeric / Non-MSISDN Target"))
    )
    circle_val = decoded.get("circle") or ("Not known from the number (numbers can be ported)" if is_phone_query else "N/A (not a phone number)")

    result = {
        "is_phone_query": is_phone_query,
        # Unified keys so both Search UI (`phone_query`, `line_type`, `co_occurring_records`) and legacy tests work
        "phone_query": e164_val if is_phone_query else f"{query} (No MSISDN detected)",
        "normalized_input": e164_val,
        "format_valid": bool(is_phone_query),
        "country": "India (+91 / TRAI E.164)" if is_phone_query else "N/A",
        "line_type": line_classification,
        "carrier_type": line_classification,
        "telecom_circle": circle_val,
        "sha256_fingerprint": decoded.get("sha256_fingerprint", ""),
        "whatsapp_surface": f"https://wa.me/91{nat_num}" if len(nat_num) == 10 else None,
        "telegram_surface": f"https://t.me/+91{nat_num}" if len(nat_num) == 10 else None,
        "nodal_authority": "DoT LSA Karnataka / TSP Nodal Officer (BNSS §94)" if is_phone_query else "N/A",
        "co_occurring_records": matching_firs,
        "matching_firs": matching_firs,
        "associated_zones": list(associated_zones),
        "associated_names": list(associated_names),
    }

    scan_tree.append({
        "id": "EVT-03",
        "event_type": "TELECOM_SCAN",
        "source": "PhoneNumberDecoder",
        "detail": (
            f"Phone number decoded: '{e164_val}' ({line_classification}; circle={circle_val})"
            if is_phone_query
            else f"Target '{query}' checked by the phone-number decoder: not a phone number (SHA-256={decoded.get('sha256_fingerprint')})"
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return result


def _run_maltego_linkage_module(
    query: str,
    decoded: dict[str, Any],
    rows: list[dict],
    scan_tree: list[dict],
) -> dict[str, Any]:
    """The items the identifier itself points to (RTO, bank, circle). Nothing is looked up outside."""
    nodes = []
    edges = []
    seen_nodes = set()

    def _add_node(node_id: str, label: str, kind: str, verified: bool = False, badge: str = "OSINT / UNVERIFIED") -> None:
        if node_id in seen_nodes:
            return
        seen_nodes.add(node_id)
        nodes.append({
            "id": node_id,
            "label": label,
            "kind": kind,
            "type": kind.upper(),
            "node_type": kind.upper(),
            "verified": verified,
            "badge": badge,
            "state": "K" if verified else "U",
        })

    seed_id = f"TARGET:{query}"
    _add_node(seed_id, decoded.get("normalized") or query, "seed", verified=False, badge="TARGET")

    ttype = decoded.get("target_type", "person_or_entity")
    if ttype == "vehicle_plate":
        rto_id = f"RTO:{decoded['rto_code']}"
        _add_node(rto_id, f"{decoded['rto_code']} · {decoded['rto_office']}", "rto_jurisdiction")
        edges.append({"source": seed_id, "target": rto_id, "label": "registered_at", "verified": False})

        dist_id = f"DIST:{decoded['district']}"
        _add_node(dist_id, f"{decoded['district']}, {decoded['state']}", "jurisdiction")
        edges.append({"source": rto_id, "target": dist_id, "label": "district", "verified": False})

        vahan_id = "SURFACE:VAHAN_FASTAG"
        _add_node(vahan_id, "Vahan 4.0 / NETC FASTag / ANPR", "telemetry")
        edges.append({"source": seed_id, "target": vahan_id, "label": "statutory_lookup", "verified": False})

    elif ttype == "upi_vpa":
        psp_id = f"PSP:{decoded['psp_app']}"
        _add_node(psp_id, f"{decoded['psp_app']} ({decoded['psp_handle']})", "psp_provider")
        edges.append({"source": seed_id, "target": psp_id, "label": "routed_via", "verified": False})

        bank_id = f"BANK:{decoded['sponsor_bank']}"
        _add_node(bank_id, decoded["sponsor_bank"], "sponsor_bank")
        edges.append({"source": psp_id, "target": bank_id, "label": "settled_by", "verified": False})

        if decoded.get("linked_mobile"):
            mob_id = f"MSISDN:{decoded['linked_mobile']}"
            _add_node(mob_id, decoded["linked_mobile"], "phone")
            edges.append({"source": seed_id, "target": mob_id, "label": "embedded_msisdn", "verified": False})

        npci_id = "AUTHORITY:NPCI_1930"
        _add_node(npci_id, "NPCI / NCRP 1930 Cyber Cell", "statutory_nodal")
        edges.append({"source": bank_id, "target": npci_id, "label": "bnss_94_106", "verified": False})

    elif ttype == "phone":
        circle_id = f"CIRCLE:{decoded['circle']}"
        _add_node(circle_id, decoded["circle"], "telecom_circle")
        edges.append({"source": seed_id, "target": circle_id, "label": "first_allocated_in", "verified": False})

        series_id = f"SERIES:{decoded['trai_series'][:13]}"
        _add_node(series_id, decoded["trai_series"], "numbering_plan")
        edges.append({"source": seed_id, "target": series_id, "label": "trai_plan", "verified": False})

        hash_id = f"HASH:{decoded['sha256_fingerprint']}"
        _add_node(hash_id, decoded["sha256_fingerprint"], "crypto_hash")
        edges.append({"source": seed_id, "target": hash_id, "label": "sha256", "verified": False})

        msg_id = "SURFACE:WA_TG_PROBE"
        _add_node(msg_id, "WhatsApp / Telegram Surface", "messaging_surface")
        edges.append({"source": seed_id, "target": msg_id, "label": "public_handle_probe", "verified": False})

    else:
        handle_id = f"HANDLE:@{decoded.get('clean_handle', 'target')}"
        _add_node(handle_id, f"@{decoded.get('clean_handle', 'target')}", "digital_handle")
        edges.append({"source": seed_id, "target": handle_id, "label": "alias_vector", "verified": False})

        kanoon_id = "ARCHIVE:JUDICIAL_INDEX"
        _add_node(kanoon_id, "eCourts / Indian Kanoon Index", "legal_archive")
        edges.append({"source": seed_id, "target": kanoon_id, "label": "dork_vector", "verified": False})

        news_id = "ARCHIVE:REGIONAL_MEDIA"
        _add_node(news_id, "Karnataka Media & Public Gazette", "news_archive")
        edges.append({"source": seed_id, "target": news_id, "label": "open_web_scan", "verified": False})

    # Optional legacy row expansion (only used if a unit test explicitly passes mock rows)
    q_low = query.lower()
    for r in rows:
        r_id = str(r.get("id") or r.get("fir_num") or "REC-X")
        s_name = str(r.get("suspect_name") or "Subject")
        ph = str(r.get("phone_hash", ""))
        zone = str(r.get("zone") or "Karnataka")

        if not (q_low in str(r).lower() or q_low in s_name.lower() or q_low in ph.lower() or q_low in zone.lower()):
            continue

        fir_node_id = f"FIR:{r_id}"
        _add_node(fir_node_id, f"Record {r_id}", "fir", verified=True, badge="VERIFIED")
        edges.append({"source": seed_id, "target": fir_node_id, "label": "involves", "verified": True})

        sus_node_id = f"PERSON:{s_name}"
        _add_node(sus_node_id, s_name, "suspect", verified=True, badge="VERIFIED")
        edges.append({"source": fir_node_id, "target": sus_node_id, "label": "named_accused", "verified": True})

        if ph:
            phone_node_id = f"PHONE:{ph}"
            _add_node(phone_node_id, f"PhHash:{ph[:8]}...", "phone", verified=True, badge="VERIFIED")
            edges.append({"source": sus_node_id, "target": phone_node_id, "label": "uses_phone", "verified": True})

        zone_node_id = f"ZONE:{zone}"
        _add_node(zone_node_id, zone, "zone", verified=True, badge="VERIFIED")
        edges.append({"source": fir_node_id, "target": zone_node_id, "label": "jurisdiction", "verified": True})

    scan_tree.append({
        "id": "EVT-04",
        "event_type": "GRAPH_LINKAGE",
        "source": "LinkMap",
        "detail": f"Link map built from the identifier: {len(nodes)} items and {len(edges)} links (none checked against an outside source)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {"nodes": nodes, "edges": edges}


def _run_sherlock_module(
    query: str,
    decoded: dict[str, Any],
    scan_tree: list[dict],
) -> list[dict]:
    """Links an officer can open by hand to check whether a profile exists. None is opened here.
    All discovered handles are strictly quarantined (`unverified=True`, `status="quarantined"`).
    """
    clean_handle = re.sub(r"[^A-Za-z0-9_.-]", "", query.lstrip("@")).lower() or "target"
    url_q = urllib.parse.quote(query.strip())

    platforms = [
        {
            "platform": "Telegram Public Handle",
            "category": "Messaging",
            "handle": clean_handle,
            "url": f"https://t.me/{clean_handle}",
        },
        {
            "platform": "Instagram Surface",
            "category": "Social Media",
            "handle": clean_handle,
            "url": f"https://www.instagram.com/{clean_handle}/",
        },
        {
            "platform": "X (Twitter) Search",
            "category": "Social Media",
            "handle": clean_handle,
            "url": f"https://x.com/search?q={url_q}",
        },
        {
            "platform": "Facebook Public Directory",
            "category": "Social Media",
            "handle": clean_handle,
            "url": f"https://www.facebook.com/public/{clean_handle}",
        },
        {
            "platform": "GitHub Code & Commit Footprint",
            "category": "Developer / Tech",
            "handle": clean_handle,
            "url": f"https://github.com/{clean_handle}",
        },
        {
            "platform": "Indian Kanoon Judicial Index",
            "category": "Court / Legal",
            "handle": query.strip(),
            "url": f"https://indiankanoon.org/search/?formInput={url_q}",
        },
    ]

    handles = []
    for p in platforms:
        handles.append({
            "platform": p["platform"],
            "category": p["category"],
            "handle": p["handle"],
            "url": p["url"],
            "unverified": True,
            "status": "quarantined",
            "badge": "OSINT / UNVERIFIED",
        })

    scan_tree.append({
        "id": "EVT-05",
        "event_type": "HANDLE_LINKS",
        "source": "HandleCheckLinks",
        "detail": f"Prepared {len(handles)} links to check by hand; none was opened, so none is a finding",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return handles


def _run_osint_corroboration(
    query: str,
    decoded: dict[str, Any],
    rows: list[dict],
    handles: list[dict],
    scan_tree: list[dict],
) -> list[dict]:
    """Generates deterministic open-source verification vectors (never fake claims).
    If `rows` are passed in a unit test, annotates `corroborates` for test compatibility.
    """
    url_q = urllib.parse.quote(query.strip())
    claims = [
        {
            "id": "OSINT-V01",
            "text": (
                f"Decoded [{decoded.get('target_label', 'Identifier')}] for target '{query}': "
                f"normalized as '{decoded.get('normalized', query)}' ({decoded.get('sha256_fingerprint', '')})."
            ),
            "source_url": f"https://duckduckgo.com/?q={url_q}",
            "unverified": True,
            "badge": "OSINT / QUARANTINED",
        },
        {
            "id": "OSINT-V02",
            "text": (
                f"Open-source judicial and public archive verification vector for '{query}' "
                f"(Indian Kanoon / High Court of Karnataka / Gazette lookup)."
            ),
            "source_url": f"https://indiankanoon.org/search/?formInput={url_q}",
            "unverified": True,
            "badge": "OSINT / QUARANTINED",
        },
    ]

    for c in claims:
        txt_low = c["text"].lower()
        corroborated_ids = []
        for r in rows:
            r_id = str(r.get("id") or r.get("fir_num") or "")
            zone = str(r.get("zone") or "").lower()
            s_name = str(r.get("suspect_name") or "").lower()

            if (zone and zone in txt_low) or (s_name and s_name in txt_low):
                if r_id:
                    corroborated_ids.append(f"FIR:{r_id}")

        if corroborated_ids:
            c["corroborates"] = corroborated_ids
            c["bonus_score"] = 0.10

    corroborated_total = sum(1 for c in claims if c.get("corroborates"))
    scan_tree.append({
        "id": "EVT-06",
        "event_type": "OSINT_CORROBORATION",
        "source": "OSINTQuarantineGate",
        "detail": (
            f"Verified standalone quarantine gate for '{query}': {len(claims)} forensic vectors cataloged "
            f"(external claims strictly isolated from FIR records)"
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return claims

