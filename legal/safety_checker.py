import re

class LegalSafetyChecker:
    """Scans scripts for policy violations before production."""
    
    RED_FLAGS = [
        r"\bhow\s+(?:to|do\s+you)\s+(?:launder|hide|evade|fake)\b",  # instructional illegality
        r"\bcontact\s+(?:him|her|them)\s+(?:to|for)\s+(?:buy|purchase)\b",  # enabling
        r"\b(undetectable|untraceable|100%\s+safe)\b",  # false safety claims
    ]
    
    def __init__(self):
        self.living_persons = set()  # Populate from config or API if needed
    
    def scan(self, script: str, sources: list) -> dict:
        """
        Returns: {
            "passed": bool,
            "issues": list,
            "risk_level": "low" | "medium" | "high"
        }
        """
        issues = []
        script_lower = script.lower()
        
        # Check for instructional illegality
        for pattern in self.RED_FLAGS:
            if re.search(pattern, script_lower):
                issues.append(f"RED FLAG: Potential instructional illegality matched '{pattern}'")
        
        # Check financial advice disclaimer
        if "not financial advice" not in script_lower and "educational purposes" not in script_lower:
            issues.append("MISSING: Financial disclaimer required for finance content")
        
        # Check synthetic disclosure mention (YouTube requires this in content too)
        if "altered or synthetic" not in script_lower and "ai generated" not in script_lower:
            issues.append("WARNING: Consider adding synthetic content mention for transparency")
        
        # Check for unproven allegations against living persons
        # Simple heuristic: if name appears without "convicted" or "pleaded" nearby
        # (In production, cross-reference against PACER/SEC conviction lists)
        
        risk = "high" if any("RED FLAG" in i for i in issues) else \
               "medium" if issues else "low"
        
        return {
            "passed": risk != "high",
            "issues": issues,
            "risk_level": risk
        }

5. config/documentary_prompts.json (NEW)
Store your 5-Act prompt templates here so Scribe can load them.
JSONCopy
{
  "documentary_5_act": {
    "system_role": "You are a documentary scriptwriter for 'The Ledger'. Write in a cold, authoritative, measured tone. Every factual claim must be attributed to a named source. No sensationalism.",
    "structure": {
      "act_1": "HOOK (0:00-1:30): Open with a physical object or impossible number. Immediate stakes. Why this threatens viewer financial safety.",
      "act_2": "INVESTIGATION (1:30-7:00): Timeline reconstruction using ONLY court documents. Use phrase 'According to the [DATE] [DOCUMENT]...' for every claim. Include 3 direct quotes with page numbers.",
      "act_3": "SYSTEM (7:00-9:00): Zoom out to macro implications. Cite academic or regulatory context. Connect to present day.",
      "act_4": "BRIDGE (9:00-9:45): Natural affiliate transition. 'Cases like this are why I use [Ledger/Bybit]...' Frame as security lesson, not sales pitch.",
      "act_5": "VERDICT (9:45-10:30): Human story conclusion. Perpetrator fate. Open-ended question for comments."
    },
    "rules": [
      "140-160 words per minute",
      "Write visual cues in [brackets]",
      "No accusations against living non-convicted persons",
      "Include disclaimer at start: 'This video is for educational and documentary purposes only'",
      "Total spoken length: 8-12 minutes"
    ],
    "voice_direction": {
      "pace": "Measured, 150 WPM",
      "tone": "Melancholic authority",
      "energy": "First 60 seconds 10% more energy than rest",
      "pauses": "Mark dramatic pauses as [PAUSE 2s]"
    }
  }
}

6. Modified main.py (KEY CHANGE)
Add --channel and --affiliate flags to your existing CLI.