"""CrimeGroup_Name → analytic category.

A line-for-line port of `categorize()` in antar-frontend/lib/crimeGraph.js, so the map
forecast and the crime graph put every FIR in the same bucket. Change both together.
"""

CATEGORIES: dict[str, str] = {
    "VIOLENT": "Violent Crimes",
    "MURDER": "Murder",
    "KIDNAP": "Kidnapping & Abduction",
    "WOMEN": "Crimes vs Women",
    "CHILDREN": "Crimes vs Children",
    "SCST": "SC/ST Atrocities",
    "ECONOMIC": "Economic Offences",
    "CYBER": "Cyber Crimes",
    "PROPERTY": "Property Crimes",
    "NARCOTICS": "Narcotics & Seizures",
    "MISSING": "Missing Persons",
    "CORRUPTION": "Corruption / Public Servants",
    "FOREIGN": "Crimes vs/by Foreigners",
    "ENVIRON": "Environment Offences",
    "ROAD": "Road Accidents",
    "LOCAL": "Police & Local Acts",
    "OTHER": "Other",
}

_ROAD_KEYS = ("MOTOR VEHICLE ACCIDENT", "NEGLIGENT ACT", "RASHNESS", "NEGLIGENCE")
_LOCAL_KEYS = ("KARNATAKA POLICE ACT", "KARNATAKA STATE LOCAL ACT", "CRPC", "PUBLIC SAFETY",
               "COTPA", "TOBACCO", "ELECTION", "CONSUMER")


def _has(g: str, *keys: str) -> bool:
    return any(k in g for k in keys)


def categorize(group: str | None) -> str:
    g = (group or "").upper().replace("_", " ")
    if "CYBER" in g: return "CYBER"
    if _has(g, "POCSO", "CHILDREN"): return "CHILDREN"
    if "IMMORAL TRAFFIC" in g: return "WOMEN"
    if _has(g, "CRUELTY BY HUSBAND", "WOMEN", "MOLEST", "DOWRY", "RAPE"): return "WOMEN"
    if "PUBLIC SERVANT IS A VICTIM" in g: return "VIOLENT"
    if "SNATCH" in g: return "PROPERTY"
    if _has(g, *_ROAD_KEYS): return "ROAD"
    if _has(g, *_LOCAL_KEYS): return "LOCAL"
    if g == "MURDER" or _has(g, "DOWRY DEATH", "CULPABLE HOMICIDE"): return "MURDER"
    if _has(g, "KIDNAP", "ABDUCT"): return "KIDNAP"
    if _has(g, "SCHEDULED CASTE", "SC/ST"): return "SCST"
    if "MISSING" in g: return "MISSING"
    if _has(g, "CHEAT", "BREACH OF TRUST", "FORGERY", "COUNTERFEIT", "ECONOMIC"): return "ECONOMIC"
    if _has(g, "THEFT", "ROBBERY", "BURGLARY", "DACOITY", "TRESPASS", "MISCHIEF", "PROPERTY"):
        return "PROPERTY"
    if _has(g, "NARCOTIC", "EXCISE", "SEIZURE"): return "NARCOTICS"
    if _has(g, "ATTEMPT TO MURDER", "HURT", "RIOT", "INTIMIDATION", "AFFRAY", "ASSAULT"):
        return "VIOLENT"
    if _has(g, "PUBLIC SERVANT", "CORRUPT"): return "CORRUPTION"
    if _has(g, "FOREIGN", "PASSPORT"): return "FOREIGN"
    if _has(g, "ANIMAL", "FOREST", "ENVIRON"): return "ENVIRON"
    return "OTHER"
