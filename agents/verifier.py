#!/usr/bin/env python3
"""
LEGAL VERIFIER
Cross-references documentary scripts against court documents and institutional sources.
Flags unverified claims, hallucinated quotes, and risky attributions.
"""

import re
import os
from typing import Dict, List, Set, Tuple
from difflib import SequenceMatcher
from datetime import datetime


class LegalVerifier:
    """
    Fact-checking agent specialized for financial crime documentaries.
    Never trusts the script. Only trusts primary sources.
    """

    # Minimum similarity for a quote to be considered "verified"
    QUOTE_SIMILARITY_THRESHOLD = 0.80

    # Confidence thresholds
    CONFIDENCE_PASS = 0.85
    CONFIDENCE_WARN = 0.60

    def __init__(self, api_manager):
        self.api = api_manager
        self.issues = []
        self.warnings = []

    def verify(self, script: Dict, research: Dict) -> Dict:
        """
        Main entry. Returns verdict dict compatible with orchestrator.
        """
        print("  🔎 Verifying script against sources...")

        self.issues = []
        self.warnings = []

        full_text = script.get("full_text", "")
        sources = research.get("sources", [])
        court_docs = research.get("court_docs", [])
        research_quotes = research.get("quotes", [])
        entities = research.get("entities", {})

        # 1. Extract all claims from script
        claims = self._extract_claims(full_text)

        # 2. Verify each claim has a source attribution
        attribution_result = self._check_attributions(full_text, claims, sources)

        # 3. Verify quoted text actually exists in source material
        quote_result = self._verify_quotes(full_text, research_quotes)

        # 4. Check for hallucinated entities (people/companies not in research)
        entity_result = self._check_entities(full_text, entities, sources)

        # 5. Check for living-person defamation risk
        person_result = self._check_living_persons(full_text, sources, court_docs)

        # 6. Check for forbidden language (instructional, enabling, guarantees)
        policy_result = self._check_policy_violations(full_text)

        # 7. Calculate confidence
        total_checks = (
            attribution_result["checked"] +
            quote_result["checked"] +
            entity_result["checked"] +
            person_result["checked"] +
            policy_result["checked"]
        )
        total_passed = (
            attribution_result["passed"] +
            quote_result["passed"] +
            entity_result["passed"] +
            person_result["passed"] +
            policy_result["passed"]
        )

        confidence = total_passed / total_checks if total_checks > 0 else 0.0

        # Compile verdict
        verdict = {
            "passed": confidence >= self.CONFIDENCE_PASS and len(self.issues) == 0,
            "confidence": round(confidence, 2),
            "claims_checked": total_checks,
            "claims_passed": total_passed,
            "issues": self.issues,
            "warnings": self.warnings,
            "breakdown": {
                "attributions": attribution_result,
                "quotes": quote_result,
                "entities": entity_result,
                "persons": person_result,
                "policy": policy_result
            }
        }
        status_icon = "✅" if verdict["passed"] else "⚠️"
        print(f"  {status_icon} Verification: {confidence:.0%} confidence ({total_passed}/{total_checks} checks)")

        for issue in self.issues:
            print(f"     ❌ {issue}")
        for warn in self.warnings:
            print(f"     ⚠️  {warn}")

        return verdict

    # ─── CLAIM EXTRACTION ───

    def _extract_claims(self, text: str) -> List[Dict]:
        """
        Extract factual statements that need sourcing.
        Looks for patterns like:
        - "According to X..."
        - "In DATE, ENTITY did Y..."
        - "$AMOUNT was..."
        """
        claims = []

        # Pattern 1: "According to [Source]" sentences
        according_pattern = r'According to [^.]*\.'
        for match in re.finditer(according_pattern, text, re.IGNORECASE):
            claims.append({
                "type": "attributed",
                "text": match.group(),
                "span": match.span()
            })

        # Pattern 2: Dollar amounts (high-risk claims)
        money_pattern = r'\$[\d,]+(?:\.\d{2})?\s*(?:billion|million|thousand)?'
        for match in re.finditer(money_pattern, text, re.IGNORECASE):
            # Grab the sentence containing the dollar amount
            start = text.rfind('.', 0, match.start()) + 1
            end = text.find('.', match.end()) + 1
            sentence = text[start:end].strip()
            claims.append({
                "type": "financial",
                "text": sentence,
                "amount": match.group(),
                "span": (start, end)
            })

        # Pattern 3: Date-specific events
        date_pattern = r'(?:In|On|By|During)\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s*\d{4}[^.]*\.'
        for match in re.finditer(date_pattern, text, re.IGNORECASE):
            claims.append({
                "type": "dated_event",
                "text": match.group(),
                "span": match.span()
            })

        # Pattern 4: Legal outcomes (convicted, sentenced, pleaded)
        legal_pattern = r'[^.]*(?:convicted|sentenced|pleaded guilty|found liable|ordered to pay)[^.]*\.'
        for match in re.finditer(legal_pattern, text, re.IGNORECASE):
            claims.append({
                "type": "legal_outcome",
                "text": match.group(),
                "span": match.span()
            })

        return claims

    # ─── ATTRIBUTION CHECK ───

    def _check_attributions(self, text: str, claims: List[Dict], sources: List[Dict]) -> Dict:
        """
        Ensure every major claim has an "According to..." or similar attribution.
        """
        checked = 0
        passed = 0

        source_names = set()
        for s in sources:
            src_name = s.get("source", "").lower()
            title = s.get("title", "").lower()
            source_names.add(src_name)
            source_names.add(title)

        for claim in claims:
            if claim["type"] == "financial":
                checked += 1
                # Financial claims MUST have attribution nearby
                claim_text_lower = claim["text"].lower()
                has_attribution = any(
                    phrase in claim_text_lower
                    for phrase in ["according to", "court documents show", "the report states",
                                   "the filing alleges", "records indicate", "the complaint states"]
                )
                if has_attribution:
                    passed += 1
                else:
                    self.issues.append(
                        f"Financial claim '{claim['amount']}' lacks source attribution: {claim['text'][:80]}..."
                    )

            elif claim["type"] == "legal_outcome":
                checked += 1
                # Legal outcomes MUST attribute to a court or agency
                claim_lower = claim["text"].lower()
                valid_source = any(
                    court in claim_lower
                    for court in ["court", "judge", "jury", "sec", "cftc", "doj", "department of justice"]
                )
                if valid_source:
                    passed += 1
                else:
                    self.issues.append(
                        f"Legal outcome lacks court attribution: {claim['text'][:80]}..."
                    )

        return {"checked": checked, "passed": passed, "type": "attribution"}

    # ─── QUOTE VERIFICATION ───

    def _verify_quotes(self, text: str, research_quotes: List[Dict]) -> Dict:
        """
        Check that quoted text in script actually exists in research quotes.
        Uses fuzzy matching because LLMs paraphrase.
        """
        checked = 0
        passed = 0

        # Extract quotes from script (text in quotation marks)
        script_quotes = re.findall(r'"([^"]{10,500})"', text)

        if not research_quotes:
            self.warnings.append("No research quotes available for verification")
            return {"checked": 0, "passed": 0, "type": "quotes"}

        # Build corpus of research text
        research_texts = [q.get("text", "") for q in research_quotes]

        for sq in script_quotes:
            checked += 1
            best_match = 0.0
            best_source = ""

            for rq_text in research_texts:
                similarity = SequenceMatcher(None, sq.lower(), rq_text.lower()).ratio()
                if similarity > best_match:
                    best_match = similarity
                    best_source = rq_text[:50]

            if best_match >= self.QUOTE_SIMILARITY_THRESHOLD:
                passed += 1
            else:
                self.issues.append(
                    f"Quote not found in sources (best match: {best_match:.0%}): '{sq[:80]}...'"
                )

        return {"checked": checked, "passed": passed, "type": "quotes"}

    # ─── ENTITY CHECK ───

    def _check_entities(self, text: str, entities: Dict, sources: List[Dict]) -> Dict:
        """
        Flag entities mentioned in script that don't appear in research.
        Reduces hallucination risk.
        """
        checked = 0
        passed = 0

        # Build known entity list from research
        known_entities = set()
        for company in entities.get("companies_mentioned", []):
            known_entities.add(company.lower())
        for src in sources:
            known_entities.add(src.get("source", "").lower())
            known_entities.add(src.get("title", "").lower())

        # Extract capitalized entities from script (simple heuristic)
        # Look for 2-4 word capitalized phrases
        pattern = r'\b([A-Z][a-zA-Z&]+(?:\s+[A-Z][a-zA-Z&]+){1,3})\b'
        script_entities = set(re.findall(pattern, text))

        for entity in script_entities:
            checked += 1
            entity_lower = entity.lower()

            # Check if entity or substring exists in known entities
            known = any(
                entity_lower in known or known in entity_lower
                for known in known_entities
            )

            if known or len(entity) < 6:  # Short words are likely false positives
                passed += 1
            else:
                self.warnings.append(
                    f"Entity '{entity}' not found in research sources — verify manually"
                )

        return {"checked": checked, "passed": passed, "type": "entities"}

    # ─── LIVING PERSON CHECK ───

    def _check_living_persons(self, text: str, sources: List[Dict], court_docs: List[Dict]) -> Dict:
        """
        Critical: Ensure no living person is accused of a crime they weren't convicted of.
        """
        checked = 0
        passed = 0

        # Extract person names (simple heuristic: Capitalized First Last)
        name_pattern = r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b'
        potential_names = re.findall(name_pattern, text)

        # Build list of convicted persons from court docs
        convicted_persons = set()
        for doc in court_docs:
            title = doc.get("title", "")
            # Look for "United States v. NAME" or "NAME pleaded guilty"
            if " v. " in title:
                parts = title.split(" v. ")
                if len(parts) > 1:
                    convicted_persons.add(parts[1].strip().lower())

        for name in potential_names:
            checked += 1
            name_lower = name.lower()

            # Skip common false positives
            if name_lower in {"the ledger", "this video", "new york", "united states",
                              "hong kong", "wall street", "silicon valley", "sec filing",
                              "supreme court", "federal reserve"}:
                passed += 1
                continue

            # Check if name appears in court docs (convicted) or news (alleged)
            in_court_docs = any(name_lower in doc.get("title", "").lower() for doc in court_docs)
            in_sources = any(name_lower in s.get("title", "").lower() or
                           name_lower in s.get("summary", "").lower()
                           for s in sources)

            if in_court_docs:
                passed += 1
            elif in_sources:
                # Mentioned in news but not court docs = ALLEGED only
                # Check if script uses "alleged" or is reporting on a conviction
                surrounding = self._get_context(text, name, window=200)
                has_alleged = "alleged" in surrounding.lower() or "accused" in surrounding.lower()
                has_convicted = "convicted" in surrounding.lower() or "pleaded" in surrounding.lower()

                if has_alleged or has_convicted:
                    passed += 1
                else:
                    self.issues.append(
                        f"LIVING PERSON RISK: '{name}' mentioned without 'alleged/convicted' qualifier. "
                        f"Context: '{surrounding[:100]}...'"
                    )
            else:
                # Name not in any source = possible hallucination
                self.warnings.append(
                    f"Name '{name}' not found in research — verify not hallucinated"
                )
                passed += 1  # Warning only, not blocking

        return {"checked": checked, "passed": passed, "type": "living_persons"}

    # ─── POLICY VIOLATIONS ───

    def _check_policy_violations(self, text: str) -> Dict:
        """
        Check for language that violates YouTube or legal policy.
        """
        checked = 0
        passed = 0

        violations = [
            (r'\bhow\s+(?:to|do\s+I)\s+(?:hide|launder|evade|avoid\s+taxes)\b',
             "Instructional financial crime"),
            (r'\b(undetectable|untraceable|100%\s+(?:safe|anonymous))\b',
             "False safety claim"),
            (r'\bcontact\s+(?:him|her|them)\s+(?:to\s+(?:buy|purchase|invest))\b',
             "Enabling illegal commerce"),
            (r'\bguaranteed\s+(?:return|profit|income)\b',
             "Financial guarantee (securities fraud trigger)"),
            (r'\bmust\s+(?:buy|sell|invest\s+now)\b',
             "Investment pressure language")
        ]

        for pattern, description in violations:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            for match in matches:
                checked += 1
                self.issues.append(
                    f"POLICY VIOLATION: {description} — '{match.group()}'"
                )

        # Check disclaimer presence (counts as 1 check)
        checked += 1
        has_disclaimer = any(
            phrase in text.lower()
            for phrase in ["not financial advice", "educational purposes only",
                          "not investment advice", "documentary purposes"]
        )
        if has_disclaimer:
            passed += 1
        else:
            self.issues.append("Missing required financial/educational disclaimer")

        return {"checked": checked, "passed": passed, "type": "policy"}

    # ─── UTILITIES ───

    def _get_context(self, text: str, target: str, window: int = 150) -> str:
        """Get surrounding text for context analysis."""
        idx = text.find(target)
        if idx == -1:
            return ""
        start = max(0, idx - window)
        end = min(len(text), idx + len(target) + window)
        return text[start:end]


# ─── LEGACY ADAPTER ───

class Verifier(LegalVerifier):
    """
    Backward-compatible name for existing imports.
    """
    pass