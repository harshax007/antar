import re
import sys

file_path = r'D:\Project\antar-frontend\components\GlobalGuide.jsx'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Define the new predict block
new_predict = """  predict: {
    title: L("Predict Guide", "ಮುನ್ಸೂಚನೆ ಮಾರ್ಗದರ್ಶಿ"),
    lead: L("I actively analyze historical FIRs across all zones to estimate crime risk for the next 7 days. Every forecast I generate is fully explainable.",
            "ಮುಂಬರುವ 7 ದಿನಗಳ ಅಪರಾಧ ಅಪಾಯವನ್ನು ಅಂದಾಜು ಮಾಡಲು ನಾನು ಐತಿಹಾಸಿಕ FIR ಗಳನ್ನು ಸಕ್ರಿಯವಾಗಿ ವಿಶ್ಲೇಷಿಸುತ್ತೇನೆ. ನನ್ನ ಪ್ರತಿಯೊಂದು ಮುನ್ಸೂಚನೆಯು ಸಂಪೂರ್ಣವಾಗಿ ವಿವರಿಸಬಲ್ಲದು."),
    blocks: [
      { h: L("My Capabilities", "ನನ್ನ ಸಾಮರ್ಥ್ಯಗಳು"), items: [
        [L("Spatiotemporal Clustering", "ನೈಜ-ಸಮಯದ ಸಮೂಹ ವಿಶ್ಲೇಷಣೆ"), L("I utilize ST-DBSCAN algorithms to instantly detect emerging crime clusters before they become trends.", "ಅಪರಾಧ ಸಮೂಹಗಳನ್ನು ಅವು ಟ್ರೆಂಡ್‌ಗಳಾಗುವ ಮುನ್ನವೇ ಪತ್ತೆಹಚ್ಚಲು ನಾನು ST-DBSCAN ಅಲ್ಗಾರಿದಮ್‌ಗಳನ್ನು ಬಳಸುತ್ತೇನೆ.")],
        [L("Anomaly Detection (MAD-z)", "ಅಸಂಗತತೆ ಪತ್ತೆ (MAD-z)"), L("I filter out statistical noise. A Z-score above 2.5 tells me a spike is a true anomaly, not a random fluctuation.", "ನಾನು ಸಾಂಖ್ಯಿಕ ಶಬ್ದವನ್ನು ಫಿಲ್ಟರ್ ಮಾಡುತ್ತೇನೆ. 2.5 ಕ್ಕಿಂತ ಹೆಚ್ಚಿನ Z-ಸ್ಕೋರ್ ನನಗೆ ಸ್ಪೈಕ್ ನಿಜವಾದ ಅಸಂಗತತೆ ಎಂದು ಹೇಳುತ್ತದೆ.")],
        [L("Split-Conformal Forecasting", "ಸ್ಪ್ಲಿಟ್-ಕಾನ್ಫಾರ್ಮಲ್ ಮುನ್ಸೂಚನೆ"), L("I do not just guess; I provide exact expected incident ranges (e.g., 6-9 cases) with 80% to 90% mathematical confidence.", "ನಾನು ಕೇವಲ ಊಹಿಸುವುದಿಲ್ಲ; 80% ರಿಂದ 90% ಗಣಿತದ ವಿಶ್ವಾಸದೊಂದಿಗೆ ನಿಖರವಾದ ನಿರೀಕ್ಷಿತ ಘಟನೆಗಳ ಶ್ರೇಣಿಯನ್ನು ನಾನು ಒದಗಿಸುತ್ತೇನೆ.")],
      ] },
      { h: L("What I Display", "ನಾನು ಪ್ರದರ್ಶಿಸುವುದು"), items: [
        [L("Forecast Board", "ಮುನ್ಸೂಚನೆ ಬೋರ್ಡ್"), L("My live recalculation of risk by zone and crime type, updating the moment a new FIR enters the registry.", "ಹೊಸ FIR ದಾಖಲಾದ ಕ್ಷಣವೇ ನವೀಕರಿಸುವ ಮೂಲಕ, ವಲಯ ಮತ್ತು ಅಪರಾಧದ ಪ್ರಕಾರದ ಮೂಲಕ ನನ್ನ ಲೈವ್ ಅಪಾಯದ ಮರು ಲೆಕ್ಕಾಚಾರ.")],
        [L("Silence Drops", "ಮೌನ ಕುಸಿತಗಳು"), L("If reports suddenly stop, I flag this as a 'silence drop', which often indicates under-reporting rather than increased safety.", "ವರದಿಗಳು ಇದ್ದಕ್ಕಿದ್ದಂತೆ ನಿಂತರೆ, ನಾನು ಇದನ್ನು 'ಮೌನ ಕುಸಿತ' ಎಂದು ಗುರುತಿಸುತ್ತೇನೆ, ಇದು ಹೆಚ್ಚಾಗಿ ಕಡಿಮೆಯಾದ ವರದಿಯನ್ನು ಸೂಚಿಸುತ್ತದೆ.")],
        [L("Agent Reasoning Trace", "ಏಜೆಂಟ್ ತಾರ್ಕಿಕ ಜಾಡು"), L("When you click a forecast, I show you exactly which signals, seasonal drivers, and historical patterns shaped my conclusion.", "ನೀವು ಮುನ್ಸೂಚನೆಯನ್ನು ಕ್ಲಿಕ್ ಮಾಡಿದಾಗ, ಯಾವ ಸಂಕೇತಗಳು ಮತ್ತು ಐತಿಹಾಸಿಕ ಮಾದರಿಗಳು ನನ್ನ ತೀರ್ಮಾನವನ್ನು ರೂಪಿಸಿದವು ಎಂಬುದನ್ನು ನಾನು ನಿಖರವಾಗಿ ತೋರಿಸುತ್ತೇನೆ.")],
      ] },
    ],
    note: L("My forecasts are designed to optimize tactical patrol deployments. They are analytical assessments, not legal evidence.", "ನನ್ನ ಮುನ್ಸೂಚನೆಗಳನ್ನು ಯುದ್ಧತಂತ್ರದ ಗಸ್ತು ನಿಯೋಜನೆಗಳನ್ನು ಅತ್ಯುತ್ತಮವಾಗಿಸಲು ವಿನ್ಯಾಸಗೊಳಿಸಲಾಗಿದೆ. ಅವು ವಿಶ್ಲೇಷಣಾತ್ಮಕ ಮೌಲ್ಯಮಾಪನಗಳೇ ಹೊರತು ಕಾನೂನು ಪುರಾವೆಗಳಲ್ಲ."),
  },"""

# Regex to find the existing predict: { ... } block
# It ends right before brain: {
predict_regex = r'  predict:\s*\{.*?note:\s*L\("Forecasts support patrol planning\. They are not evidence\.",[^)]+\),\s*\},\s*'
# Wait, parsing the JSON-like structure via regex is tricky. Let's use basic string matching.

start_str = '  predict: {'
end_str = '  brain: {'

start_idx = content.find(start_str)
end_idx = content.find(end_str, start_idx)

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_predict + "\n\n" + content[end_idx:]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Replaced predict block successfully.")
else:
    print("Could not find start or end index.")