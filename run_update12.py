import sys

file_path = 'D:/Project/antar-frontend/app/(app)/predict/PredictScreen.jsx'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

good_fn = """
  const cap = (s) => s ? s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, " ") : "";
  const generateNarrative = (item) => {
    if (!item) return "";
    const name = item.zone;
    const ctype = cap(item.crime_type);
    const z = item.z_score ? `with an anomaly score of ${item.z_score}` : "";
    const rs = item.risk === "HIGH" ? "critical" : item.risk === "MEDIUM" ? "elevated" : "moderate";
    const dir = item.direction === "silence" ? "an unusual drop (possible under-reporting)" : "a predicted spike";
    if (kn) {
      return `ಅಂತರ AI ವಿಶ್ಲೇಷಣೆ: ${name} ವಲಯದಲ್ಲಿ ${ctype} ಪ್ರಕರಣಗಳಲ್ಲಿ ${dir === "a predicted spike" ? "ಹೆಚ್ಚಳ" : "ಕಡಿಮೆ"} ಕಂಡುಬಂದಿದೆ. ಇದು ${rs === "critical" ? "ತೀವ್ರ" : rs === "elevated" ? "ಹೆಚ್ಚಿದ" : "ಸಾಧಾರಣ"} ಮಟ್ಟದ ಅಪಾಯವನ್ನು ಸೂಚಿಸುತ್ತದೆ.`;
    }
    return `Antar AI Analysis has identified a ${rs} risk of ${dir} for ${ctype} in ${name} ${z}. The underlying cause is linked to: ${item.why || "historical trend patterns"}.`;
  };

const avgConf"""

content = content.replace('const avgConf', good_fn)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated successfully")