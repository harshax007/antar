import sys

file_path = 'D:/Project/antar-frontend/components/GlobalGuide.jsx'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_chat = """  chat: {
    title: L("Chat Guide", "ಚಾಟ್ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("Interact with the FIR database using natural language in English or Kannada. Ask questions, request summaries, or trigger expert agents.",
            "ಇಂಗ್ಲಿಷ್ ಅಥವಾ ಕನ್ನಡದಲ್ಲಿ ನೈಸರ್ಗಿಕ ಭಾಷೆಯನ್ನು ಬಳಸಿಕೊಂಡು FIR ಡೇಟಾಬೇಸ್‌ನೊಂದಿಗೆ ಸಂವಹನ ನಡೆಸಿ. ಪ್ರಶ್ನೆಗಳನ್ನು ಕೇಳಿ, ಸಾರಾಂಶಗಳನ್ನು ವಿನಂತಿಸಿ ಅಥವಾ ತಜ್ಞ ಏಜೆಂಟ್‌ಗಳನ್ನು ಬಳಸಿ."),
    blocks: [
      { h: L("Reading Responses", "ಪ್ರತ್ಯುತ್ತರಗಳನ್ನು ಅರ್ಥೈಸಿಕೊಳ್ಳುವುದು"), items: [
        [L("The Bottom Line First", "ಮೊದಲಿಗೆ ನೇರ ಉತ್ತರ"), L("Antar provides the direct answer immediately, followed by the supporting evidence and reasoning.", "ಅಂತರ ತಕ್ಷಣವೇ ನೇರ ಉತ್ತರವನ್ನು ನೀಡುತ್ತದೆ, ಅದರ ನಂತರ ಪೂರಕ ಸಾಕ್ಷ್ಯ ಮತ್ತು ತಾರ್ಕಿಕ ವಿವರಣೆಯನ್ನು ನೀಡುತ್ತದೆ.")],
        [L("Source Citations", "ಮೂಲ ಉಲ್ಲೇಖಗಳು"), L("Every factual claim is backed by specific FIR record numbers. Click them to view the original case file.", "ಪ್ರತಿಯೊಂದು ವಾಸ್ತವಿಕ ಹೇಳಿಕೆಯು ನಿರ್ದಿಷ್ಟ FIR ದಾಖಲೆ ಸಂಖ್ಯೆಗಳಿಂದ ಬೆಂಬಲಿತವಾಗಿದೆ. ಮೂಲ ಪ್ರಕರಣದ ಫೈಲ್ ಅನ್ನು ವೀಕ್ಷಿಸಲು ಅವುಗಳ ಮೇಲೆ ಕ್ಲಿಕ್ ಮಾಡಿ.")],
        [L("Evidence Badges (K-D-I)", "ಸಾಕ್ಷ್ಯ ಬ್ಯಾಡ್ಜ್‌ಗಳು (K-D-I)"), L("Answers are strictly tagged: K (Known fact from FIR), D (Derived calculation), or I (Inferred/Prediction).", "ಉತ್ತರಗಳನ್ನು ಕಟ್ಟುನಿಟ್ಟಾಗಿ ಟ್ಯಾಗ್ ಮಾಡಲಾಗಿದೆ: K (FIR ನಿಂದ ತಿಳಿದಿರುವ ವಾಸ್ತವ), D (ಪಡೆದ ಲೆಕ್ಕಾಚಾರ), ಅಥವಾ I (ಊಹಿಸಲಾದ/ಮುನ್ಸೂಚನೆ).")],
      ] },
      { h: L("Core Agent Commands", "ಮುಖ್ಯ ಏಜೆಂಟ್ ಆಜ್ಞೆಗಳು"), items: [
        [L("/query", "/query"), L("Forces a strict structural search of the database (e.g. '/query how many thefts in Koramangala').", "ಡೇಟಾಬೇಸ್‌ನ ಕಟ್ಟುನಿಟ್ಟಾದ ರಚನಾತ್ಮಕ ಹುಡುಕಾಟವನ್ನು ಒತ್ತಾಯಿಸುತ್ತದೆ (ಉದಾ. '/query ಕೋರಮಂಗಲದಲ್ಲಿ ಎಷ್ಟು ಕಳ್ಳತನಗಳಿವೆ').")],
        [L("/connect", "/connect"), L("Invokes the Linkage agent to build suspect networks and uncover hidden syndicates across cases.", "ಶಂಕಿತ ನೆಟ್‌ವರ್ಕ್‌ಗಳನ್ನು ನಿರ್ಮಿಸಲು ಮತ್ತು ಪ್ರಕರಣಗಳಾದ್ಯಂತ ಗುಪ್ತ ಸಿಂಡಿಕೇಟ್‌ಗಳನ್ನು ಬಹಿರಂಗಪಡಿಸಲು ಲಿಂಕೇಜ್ ಏಜೆಂಟ್ ಅನ್ನು ಕರೆಯುತ್ತದೆ.")],
        [L("/anticipate", "/anticipate"), L("Triggers the Forecast engine to run risk models on a specific zone or crime type.", "ನಿರ್ದಿಷ್ಟ ವಲಯ ಅಥವಾ ಅಪರಾಧದ ಪ್ರಕಾರದಲ್ಲಿ ಅಪಾಯದ ಮಾದರಿಗಳನ್ನು ಚಲಾಯಿಸಲು ಮುನ್ಸೂಚನೆ ಎಂಜಿನ್ ಅನ್ನು ಪ್ರಚೋದಿಸುತ್ತದೆ.")],
        [L("/osint", "/osint"), L("Scans open web sources for external intelligence (always explicitly flagged as UNVERIFIED).", "ಬಾಹ್ಯ ಗುಪ್ತಚರಕ್ಕಾಗಿ ಮುಕ್ತ ವೆಬ್ ಮೂಲಗಳನ್ನು ಸ್ಕ್ಯಾನ್ ಮಾಡುತ್ತದೆ (ಯಾವಾಗಲೂ UNVERIFIED ಎಂದು ಸ್ಪಷ್ಟವಾಗಿ ಫ್ಲ್ಯಾಗ್ ಮಾಡಲಾಗುತ್ತದೆ).")],
      ] },
      { h: L("Interaction Controls", "ಸಂವಹನ ನಿಯಂತ್ರಣಗಳು"), items: [
        [L("Voice Input (Mic)", "ಧ್ವನಿ ಇನ್‌ಪುಟ್ (ಮೈಕ್)"), L("Speak your query directly. The system automatically transcribes English and Kannada.", "ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ನೇರವಾಗಿ ಮಾತನಾಡಿ. ಸಿಸ್ಟಮ್ ಸ್ವಯಂಚಾಲಿತವಾಗಿ ಇಂಗ್ಲಿಷ್ ಮತ್ತು ಕನ್ನಡವನ್ನು ಲಿಪ್ಯಂತರ ಮಾಡುತ್ತದೆ.")],
        [L("Audio Playback", "ಆಡಿಯೋ ಪ್ಲೇಬ್ಯಾಕ್"), L("Click the listen icon to have Antar read the intelligence brief aloud.", "ಅಂತರ ಇಂಟೆಲಿಜೆನ್ಸ್ ಬ್ರೀಫ್ ಅನ್ನು ಗಟ್ಟಿಯಾಗಿ ಓದುವುದನ್ನು ಕೇಳಲು ಆಲಿಸಿ ಐಕಾನ್ ಕ್ಲಿಕ್ ಮಾಡಿ.")],
        [L("Export to PDF", "PDF ಗೆ ರಫ್ತು ಮಾಡಿ"), L("Download the entire session as a tamper-evident, audit-ready PDF report for case files.", "ಪ್ರಕರಣದ ಫೈಲ್‌ಗಳಿಗಾಗಿ ಸಂಪೂರ್ಣ ಸೆಶನ್ ಅನ್ನು ಟ್ಯಾಂಪರ್-ಎವಿಡೆಂಟ್, ಆಡಿಟ್-ರೆಡಿ PDF ವರದಿಯಾಗಿ ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ.")],
      ] },
      { h: L("Trust & Verification", "ನಂಬಿಕೆ ಮತ್ತು ಪರಿಶೀಲನೆ"), items: [
        [L("Zero Hallucination Guard", "ಶೂನ್ಯ ಭ್ರಮೆ ಕಾವಲು"), L("If no relevant FIR exists, Antar will explicitly state 'Nothing found' rather than guessing.", "ಯಾವುದೇ ಸಂಬಂಧಿತ FIR ಇಲ್ಲದಿದ್ದರೆ, ಊಹಿಸುವ ಬದಲು ಅಂತರ ಸ್ಪಷ್ಟವಾಗಿ 'ಏನೂ ಕಂಡುಬಂದಿಲ್ಲ' ಎಂದು ಹೇಳುತ್ತದೆ.")],
        [L("Reasoning Trace", "ತಾರ್ಕಿಕ ಜಾಡು"), L("Click the 'Thought for X seconds' pill to audit the exact steps the AI took to gather your answer.", "ನಿಮ್ಮ ಉತ್ತರವನ್ನು ಸಂಗ್ರಹಿಸಲು AI ತೆಗೆದುಕೊಂಡ ನಿಖರವಾದ ಹಂತಗಳನ್ನು ಆಡಿಟ್ ಮಾಡಲು 'X ಸೆಕೆಂಡುಗಳ ಕಾಲ ಯೋಚಿಸಿದೆ' ಪಿಲ್ ಅನ್ನು ಕ್ಲಿಕ್ ಮಾಡಿ.")],
      ] },
    ],
    examples: {
      en: ["how many vehicle thefts in Bengaluru City?", "show me the suspect network for FIR 2023-BLR-04412", "what is the forecast for chain snatching next week?"],
      kn: ["ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಎಷ್ಟು ವಾಹನ ಕಳ್ಳತನಗಳಾಗಿವೆ?", "FIR 2023-BLR-04412 ಗಾಗಿ ಶಂಕಿತ ನೆಟ್‌ವರ್ಕ್ ಅನ್ನು ನನಗೆ ತೋರಿಸಿ", "ಮುಂದಿನ ವಾರ ಚೈನ್ ಸ್ನ್ಯಾಚಿಂಗ್‌ನ ಮುನ್ಸೂಚನೆ ಏನು?"]
    }
  },"""

start_str = '  chat: {'
end_str = '  predict: {'

start_idx = content.find(start_str)
end_idx = content.find(end_str, start_idx)

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_chat + "\n\n" + content[end_idx:]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Replaced chat block successfully.")
else:
    print("Could not find start or end index.")