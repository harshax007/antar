// Kannada for what the register writes in English: crime heads and dates. The same names as
// the backend (app/agents/display_names.py _KN_CRIME), so a crime reads the same in a chat
// answer and on a screen. A head with no Kannada name is shown as the register writes it.

const KN_CRIME = {
  "THEFT": "ಕಳ್ಳತನ", "ROBBERY": "ದರೋಡೆ", "DACOITY": "ಡಕಾಯಿತಿ", "BURGLARY": "ಮನೆಗಳ್ಳತನ",
  "HOUSE BREAKING": "ಮನೆಗಳ್ಳತನ", "CHAIN SNATCHING": "ಸರಗಳ್ಳತನ", "MURDER": "ಕೊಲೆ",
  "ATTEMPT TO MURDER": "ಕೊಲೆ ಯತ್ನ", "CHEATING": "ವಂಚನೆ", "CYBER CRIME": "ಸೈಬರ್ ಅಪರಾಧ",
  "CHEATING FRAUD": "ವಂಚನೆ", "DOMESTIC VIOLENCE": "ಕೌಟುಂಬಿಕ ಹಿಂಸೆ",
  "MISSING PERSON": "ಕಾಣೆಯಾದ ವ್ಯಕ್ತಿ", "CASES OF HURT": "ಹಲ್ಲೆ",
  "MOTOR VEHICLE ACCIDENTS FATAL": "ಮಾರಣಾಂತಿಕ ರಸ್ತೆ ಅಪಘಾತ",
  "MOTOR VEHICLE ACCIDENTS NON-FATAL": "ರಸ್ತೆ ಅಪಘಾತ (ಮಾರಣಾಂತಿಕವಲ್ಲದ)",
  "VEHICLE THEFT": "ವಾಹನ ಕಳ್ಳತನ", "MOTOR VEHICLE THEFT": "ವಾಹನ ಕಳ್ಳತನ", "RAPE": "ಅತ್ಯಾಚಾರ",
  "KIDNAPPING AND ABDUCTION": "ಅಪಹರಣ", "KIDNAPPING": "ಅಪಹರಣ",
  "NDPS": "ಮಾದಕ ವಸ್ತು (NDPS)", "RIOTS": "ಗಲಭೆ", "RIOTING": "ಗಲಭೆ", "PUBLIC SAFETY": "ಸಾರ್ವಜನಿಕ ಸುರಕ್ಷತೆ",
  "DOWRY": "ವರದಕ್ಷಿಣೆ",
  "KARNATAKA POLICE ACT 1963": "ಕರ್ನಾಟಕ ಪೊಲೀಸ್ ಕಾಯ್ದೆ 1963",
  "KARNATAKA STATE LOCAL ACT": "ಕರ್ನಾಟಕ ರಾಜ್ಯ ಸ್ಥಳೀಯ ಕಾಯ್ದೆ",
  "CRPC": "ಸಿಆರ್‌ಪಿಸಿ (CrPC)",
  "MOLESTATION": "ಲೈಂಗಿಕ ಕಿರುಕುಳ",
  "BURGLARY - NIGHT": "ರಾತ್ರಿ ಮನೆಗಳ್ಳತನ", "BURGLARY - DAY": "ಹಗಲು ಮನೆಗಳ್ಳತನ",
  "NARCOTIC DRUGS & PSHYCOTROPIC SUBSTANCES": "ಮಾದಕ ವಸ್ತು (NDPS)", "NARCOTICS": "ಮಾದಕ ವಸ್ತು",
  "POCSO": "ಪೋಕ್ಸೋ (POCSO)",
  "CRUELTY BY HUSBAND": "ಪತಿಯಿಂದ ಕ್ರೌರ್ಯ",
  "NEGLIGENT ACT": "ನಿರ್ಲಕ್ಷ್ಯದ ಕೃತ್ಯ",
  "CRIMINAL INTIMIDATION": "ಕ್ರಿಮಿನಲ್ ಬೆದರಿಕೆ",
  "CRIMES RELATED TO WOMEN": "ಮಹಿಳೆಯರಿಗೆ ಸಂಬಂಧಿಸಿದ ಅಪರಾಧಗಳು",
  "CRIMINAL TRESPASS": "ಅಕ್ರಮ ಪ್ರವೇಶ",
  "SCHEDULED CASTE AND THE SCHEDULED TRIBES": "ಪರಿಶಿಷ್ಟ ಜಾತಿ ಮತ್ತು ಪರಿಶಿಷ್ಟ ಪಂಗಡ ಕಾಯ್ದೆ",
  "OFFENCES AGAINST PUBLIC SERVANTS (PUBLIC SERVANT IS A VICTIM)": "ಸಾರ್ವಜನಿಕ ನೌಕರರ ವಿರುದ್ಧ ಅಪರಾಧಗಳು",
  "SUICIDE": "ಆತ್ಮಹತ್ಯೆ",
  "ELECTION": "ಚುನಾವಣಾ ಅಪರಾಧಗಳು",
  "CRIMINAL BREACH OF TRUST": "ನಂಬಿಕೆ ದ್ರೋಹ",
  "FORGERY": "ನಕಲಿ ದಾಖಲೆ (ಫೋರ್ಜರಿ)",
  "DEATHS DUE TO RASHNESS/NEGLIGENCE": "ನಿರ್ಲಕ್ಷ್ಯದಿಂದ ಸಾವು",
  "IMMORAL TRAFFIC": "ಅನೈತಿಕ ಸಾಗಣೆ",
  "ARSON": "ಬೆಂಕಿ ಹಚ್ಚುವಿಕೆ",
  "DOWRY DEATHS": "ವರದಕ್ಷಿಣೆ ಸಾವು",
  "ASSAULT": "ಆಕ್ರಮಣ",
  "CULPABLE HOMICIDE NOT AMOUNTING TO MURDER": "ಕೊಲೆಯಲ್ಲದ ಅಪರಾಧಿಕ ನರಹತ್ಯೆ",
  "ARMS ACT 1959": "ಶಸ್ತ್ರಾಸ್ತ್ರ ಕಾಯ್ದೆ 1959",
  "EXPLOSIVES": "ಸ್ಫೋಟಕಗಳು",
  "CHILDREN ACT": "ಮಕ್ಕಳ ಕಾಯ್ದೆ",
  "PUBLIC NUISANCE": "ಸಾರ್ವಜನಿಕ ಉಪದ್ರವ",
  "CYBERCRIME": "ಸೈಬರ್ ಅಪರಾಧ",
};

const key = (s) => String(s || "").replace(/_/g, " ").replace(/\s+/g, " ").trim().toUpperCase();

/** The Kannada name of a crime head, or null when there is none. */
export const crimeKn = (name) => KN_CRIME[key(name)] || null;

export const MONTH_KN = ["ಜನವರಿ", "ಫೆಬ್ರವರಿ", "ಮಾರ್ಚ್", "ಏಪ್ರಿಲ್", "ಮೇ", "ಜೂನ್", "ಜುಲೈ", "ಆಗಸ್ಟ್",
  "ಸೆಪ್ಟೆಂಬರ್", "ಅಕ್ಟೋಬರ್", "ನವೆಂಬರ್", "ಡಿಸೆಂಬರ್"];

/** '15 ಮೇ 2026' (or '15 ಮೇ' with year: false) for a Date or an ISO day. */
export function dateKn(v, { year = true } = {}) {
  const d = v instanceof Date ? v : new Date(/^\d{4}-\d{2}-\d{2}$/.test(String(v)) ? `${v}T00:00:00` : v);
  if (Number.isNaN(d.getTime())) return String(v ?? "");
  return `${d.getDate()} ${MONTH_KN[d.getMonth()]}${year ? ` ${d.getFullYear()}` : ""}`;
}

/** 'ಮೇ 2026' */
export function monthKn(v) {
  const d = v instanceof Date ? v : new Date(/^\d{4}-\d{2}(-\d{2})?$/.test(String(v)) ? `${String(v).slice(0, 7)}-01T00:00:00` : v);
  if (Number.isNaN(d.getTime())) return String(v ?? "");
  return `${MONTH_KN[d.getMonth()]} ${d.getFullYear()}`;
}
