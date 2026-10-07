
import re

with open("antar-frontend/components/ForecastPanel.jsx", "r", encoding="utf-8") as f:
    code = f.read()

# Replace AsOfChip component
code = re.sub(
    r"export function AsOfChip.*?return \(\s*<div className=\"fx-chip\".*?</div>\s*\);\s*\}",
    "export function AsOfChip({ fc, kn }) {\n  return null;\n}",
    code,
    flags=re.DOTALL
)

with open("antar-frontend/components/ForecastPanel.jsx", "w", encoding="utf-8") as f:
    f.write(code)

