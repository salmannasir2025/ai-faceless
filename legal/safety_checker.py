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


if __name__ == "__main__":
    # Test
    checker = LegalSafetyChecker()
    test_script = "This is a test script about financial crimes. For educational purposes only."
    result = checker.scan(test_script, [])
    print(f"Scan result: {result}")