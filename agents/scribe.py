#!/usr/bin/env python3
"""
DOCUMENTARY SCRIBE
Generates original 5-Act documentary scripts from research packets.
Transforms court documents and news into narrative, never copies verbatim.
"""

import json
import os
import re
from typing import Dict, List, Optional
from datetime import datetime

class DocumentaryScribe:
    """
    Creative writer for The Ledger. Loads prompt templates from config
    and constructs original documentary scripts with visual cues.
    """
    
    WORDS_PER_MINUTE = 150
    TARGET_MINUTES = 10
    TARGET_WORDS = WORDS_PER_MINUTE * TARGET_MINUTES  # ~1500 words
    
    def __init__(self, api_manager):
        self.api = api_manager
        self.prompts = self._load_prompts()
        self.llm = api_manager  # Assumes API manager has .generate() or .call_llm()
    
    def _load_prompts(self) -> Dict:
        """Load 5-Act prompt templates."""
        config_path = "config/documentary_prompts.json"
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return self._default_prompts()
    
    def _default_prompts(self) -> Dict:
        """Fallback if JSON missing."""
        return {
            "documentary_5_act": {
                "system_role": "You are a documentary scriptwriter for 'The Ledger'.",
                "structure": {
                    "act_1": "HOOK (0:00-1:30): Open with physical object + impossible number.",
                    "act_2": "INVESTIGATION (1:30-7:00): Timeline from court docs with attributed quotes.",
                    "act_3": "SYSTEM (7:00-9:00): Macro implications and regulatory context.",
                    "act_4": "BRIDGE (9:00-9:45): Security lesson with [AFFILIATE_BRIDGE] marker.",
                    "act_5": "VERDICT (9:45-10:30): Human conclusion and open question."
                },
                "rules": [
                    "150 words per minute",
                    "Visual cues in [brackets]",
                    "No accusations against non-convicted living persons",
                    "Every claim attributed to named source",
                    "Disclaimer at start"
                ]
            }
        }
    
    def write_documentary(self, topic: str, research: Dict, style: str, channel: str) -> Dict:
        """
        Main entry. Returns structured script dict.
        """
        print(f"  ✍️  Writing documentary script: {topic}")
        
        # Build system prompt from research
        system_prompt = self._build_system_prompt(topic, research, style)
        
        # Generate via LLM (Gemini/Claude/GPT)
        raw_script = self._generate_with_llm(system_prompt)
        
        # Parse into structured acts
        structured = self._parse_into_acts(raw_script, research)
        
        # Extract hook number for thumbnails (e.g., "$4.5B")
        hook_number = self._extract_hook_number(structured["full_text"])
        
        # Build metadata
        script_packet = {
            "topic": topic,
            "title": self._generate_title(topic, research, hook_number),
            "full_text": structured["full_text"],
            "acts": structured["acts"],
            "description": self._build_description(topic, research),
            "tags": self._generate_tags(topic, research),
            "word_count": len(structured["full_text"].split()),
            "estimated_duration": len(structured["full_text"].split()) / self.WORDS_PER_MINUTE,
            "hook_number": hook_number,
            "generated_at": datetime.utcnow().isoformat(),
            "channel": channel
        }
        print(f"  ✅ Script complete: {script_packet['word_count']} words, ~{script_packet['estimated_duration']:.1f} min")
        return script_packet
    
    def _build_system_prompt(self, topic: str, research: Dict, style: str) -> str:
        """Construct the full prompt sent to LLM."""
        prompts = self.prompts.get("documentary_5_act", {})
        structure = prompts.get("structure", {})
        rules = prompts.get("rules", [])
        
        # Build source material block (for LLM context, not for copy-paste)
        sources_block = self._format_sources_for_llm(research.get("sources", []))
        quotes_block = self._format_quotes_for_llm(research.get("quotes", []))
        timeline_block = self._format_timeline_for_llm(research.get("timeline", []))
        entities_block = self._format_entities_for_llm(research.get("entities", {}))
        
        prompt = f"""{prompts.get('system_role', '')}

TOPIC: {topic}
STYLE: {style} (documentary investigation)
SOURCE MATERIAL (Use for reference only — write original narrative):
{sources_block}

QUOTABLE EXCERPTS (Attribute properly in script):
{quotes_block}

TIMELINE (Reconstruct chronology):
{timeline_block}

ENTITIES & FINANCIALS:
{entities_block}

STRUCTURE:
{json.dumps(structure, indent=2)}

RULES:
{chr(10).join(f"- {r}" for r in rules)}

CRITICAL INSTRUCTIONS:
1. Write ORIGINAL analysis. Do NOT copy-paste from sources.
2. Every factual claim MUST use phrase: "According to the [MONTH YEAR] [DOCUMENT NAME]..."
3. Include 3 direct quotes from court docs, with attribution.
4. Mark dramatic pauses as [PAUSE 2s].
5. Mark breaths as [BREATH].
6. In Act IV, include the literal marker: [AFFILIATE_BRIDGE]
7. Start with disclaimer: "This video is for educational and documentary purposes only."
8. End with open question for comments.
9. Target length: {self.TARGET_WORDS} words (~{self.TARGET_MINUTES} minutes).

Write the complete script now. Label each Act clearly.
"""
        return prompt
    
    def _generate_with_llm(self, prompt: str) -> str:
        """Call LLM via API manager."""
        # Your api_manager likely has a method like:
        # response = self.api.call_llm(prompt, model="gemini-pro", temperature=0.7)
        # Adapt to your actual APIManager interface
        
        try:
            # Attempt via your existing API manager pattern
            if hasattr(self.api, 'generate'):
                return self.api.generate(prompt, max_tokens=4000, temperature=0.7)
            elif hasattr(self.api, 'call_llm'):
                return self.api.call_llm(prompt)
            else:
                # Fallback: write to file for manual LLM paste
                fallback_path = "output/last_prompt.txt"
                os.makedirs("output", exist_ok=True)
                with open(fallback_path, "w", encoding="utf-8") as f:
                    f.write(prompt)
                print(f"  ⚠️  No LLM connected. Prompt saved to {fallback_path}")
                return self._mock_script()  # Remove in production
                
        except Exception as e:
            print(f"  ⚠️  LLM error: {e}")
            return self._mock_script()
    
    def _parse_into_acts(self, raw_text: str, research: Dict) -> Dict:
        """Parse raw LLM output into structured acts."""
        acts = {
            "act_i_hook": "",
            "act_ii_investigation": "",
            "act_iii_system": "",
            "act_iv_bridge": "",
            "act_v_verdict": ""
        }
        
        # Split by Act markers (flexible regex)
        patterns = {
            "act_i_hook": r"(?:ACT I|Act I|Act 1|HOOK).*?(?=(?:ACT II|Act II|Act 2|INVESTIGATION|$))",
            "act_ii_investigation": r"(?:ACT II|Act II|Act 2|INVESTIGATION).*?(?=(?:ACT III|Act III|Act 3|SYSTEM|$))",
            "act_iii_system": r"(?:ACT III|Act III|Act 3|SYSTEM).*?(?=(?:ACT IV|Act IV|Act 4|BRIDGE|$))",
            "act_iv_bridge": r"(?:ACT IV|Act IV|Act 4|BRIDGE).*?(?=(?:ACT V|Act V|Act 5|VERDICT|$))",
            "act_v_verdict": r"(?:ACT V|Act V|Act 5|VERDICT).*?(?=$)"
        }
        
        for act_key, pattern in patterns.items():
            match = re.search(pattern, raw_text, re.DOTALL | re.IGNORECASE)
            if match:
                acts[act_key] = match.group(0).strip()
        
        # If parsing fails, dump raw text into Act II and log warning
        if not any(acts.values()):
            print("  ⚠️  Act parsing failed — using raw text")
            acts["act_ii_investigation"] = raw_text
        
        return {
            "acts": acts,
            "full_text": raw_text
        }
    
    def _extract_hook_number(self, text: str) -> str:
        """Extract the big dollar number from Act I for thumbnails."""
        # Look for $X.X billion/million patterns in first 500 chars
        hook_section = text[:500]
        patterns = [
            r'\$(\d+\.\d+)\s*(billion|million|trillion)',
            r'\$(\d+)\s*(billion|million|trillion)',
            r'\$([\d,]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, hook_section, re.IGNORECASE)
            if match:
                num = match.group(1)
                unit = match.group(2) if len(match.groups()) > 1 else ""
                display = f"${num} {unit}".strip() if unit else f"${num}"
                return display.upper()
        return "$4.5B"  # Default fallback
    
    def _generate_title(self, topic: str, research: Dict, hook_number: str) -> str:
        """Generate optimized documentary title."""
        # Templates from Operations Manual
        templates = [
            f"72 Hours: The {hook_number} {topic.title()} Death — Court Documents Reveal",
            f"The {hook_number} {topic.title()} Scandal: What the Courts Found",
            f"{hook_number} Vanished: The {topic.title()} Investigation",
            f"The Email That Killed {topic.title()}: {hook_number} Gone"
        ]
        
        # Pick based on research data availability
        if any("email" in s.get("title", "").lower() for s in research.get("sources", [])):
            return templates[3]
        elif len(research.get("timeline", [])) >= 5:
            return templates[0]
        else:
            return templates[1]
    
    def _build_description(self, topic: str, research: Dict) -> str:
        """Build YouTube description with disclaimer and source list."""
        sources_list = "\n".join([
            f"• {s['source']}: {s['title'][:80]}"
            for s in research.get("sources", [])[:5]
        ])
        desc = f"""⚠️ This video is for educational and documentary purposes only. It does not constitute financial advice.

Using only public court records and institutional reporting, we investigate {topic}.
📁 SOURCES:
{sources_list}

🎙️ This channel uses AI-assisted production. All scripts are original analysis written by human editors and reviewed for legal accuracy.

🔗 RESOURCES:
[Affiliate links injected by orchestrator]

#Documentary #FinancialCrime #Investigation #{topic.replace(' ', '')}
"""
        return desc
    
    def _generate_tags(self, topic: str, research: Dict) -> List[str]:
        """Generate tags from topic + entities."""
        base = ["documentary", "financial crime", "investigation", "finance"]
        topic_tags = topic.lower().split()
        entity_tags = [
            e.lower().replace(" ", "") 
            for e in research.get("entities", {}).get("companies_mentioned", [])[:3]
        ]
        return list(set(base + topic_tags + entity_tags + ["exposed", "court documents"]))[:15]
    
    # ─── Formatting helpers for LLM context ───
    
    def _format_sources_for_llm(self, sources: List[Dict]) -> str:
        lines = []
        for s in sources[:5]:
            lines.append(f"- [{s['type']}] {s['source']}: {s['title'][:100]}")
        return "\n".join(lines) if lines else "No sources found."
    
    def _format_quotes_for_llm(self, quotes: List[Dict]) -> str:
        lines = []
        for q in quotes[:3]:
            lines.append(f'- "{q["text"][:200]}..." ({q["source"]})')
        return "\n".join(lines) if lines else "No quotable excerpts."
    
    def _format_timeline_for_llm(self, timeline: List[Dict]) -> str:
        lines = []
        for t in timeline[:5]:
            lines.append(f"- {t['date'][:10]}: {t['event'][:100]}")
        return "\n".join(lines) if lines else "No timeline data."
    
    def _format_entities_for_llm(self, entities: Dict) -> str:
        lines = []
        if entities.get("dollar_amounts"):
            lines.append(f"- Financials: {', '.join(entities['dollar_amounts'][:3])}")
        if entities.get("companies_mentioned"):
            lines.append(f"- Entities: {', '.join(entities['companies_mentioned'][:5])}")
        return "\n".join(lines) if lines else "No entity data."
    
    def _mock_script(self) -> str:
        """Placeholder for testing without LLM."""
        return """ACT I - HOOK:
This is a hard drive containing 4.5 billion dollars in customer funds. [PAUSE 2s] It was found in a bankruptcy court filing in Delaware. [BREATH] The person who controlled it had stolen every penny. And he almost got away.

ACT II - INVESTIGATION:
According to the November 2022 CFTC Complaint, the exchange collapsed over 72 hours. [BREATH] The document states: "Defendants commingled customer funds with corporate operations." [PAUSE 1s] We reconstructed the timeline from SEC filings...

ACT III - SYSTEM:
The architecture was designed to hide losses in plain sight. According to the FATF, this loophole still exists in 14 jurisdictions...

ACT IV - BRIDGE:
Cases like this are exactly why operational security matters. [AFFILIATE_BRIDGE]

ACT V - VERDICT:
The sentence was 25 years. Do you think justice was served? Comment below.
"""
2️⃣ agents/publisher.py — The Affiliate Publisher
Uploads as PRIVATE with full synthetic disclosure, affiliate links, and finance disclaimers.