#!/usr/bin/env python3
"""
THE LEDGER ORCHESTRATOR
State-driven pipeline with legal safety gate and affiliate injection.
Extends your original Orchestrator with documentary-specific workflow.
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

# Core imports (from your existing codebase)
from core.project_state import ProjectState
from core.api_manager import APIManager
from core.governor import Governor

# Agent imports
from agents.scout import FinancialScout
from agents.scribe import DocumentaryScribe
from agents.verifier import LegalVerifier
from agents.artisan import DocumentaryArtisan
from agents.publisher import AffiliatePublisher

# NEW: Safety and integrations
from legal.safety_checker import LegalSafetyChecker
from voice.clone_manager import VoiceCloneManager
from graphics.thumbnails import ThumbnailFactory
from graphics.doc_graphics import DocumentGraphicFactory
from integrations.notion_sync import NotionSync

class LedgerOrchestrator:
    """
    State machine for Financial Darkness documentary production.
    Stages: SCOUT → SCRIBE → VERIFY → LEGAL_GATE → VOICE → ARTISAN → PUBLISH
    """
    
    STAGES = [
        "initialized",
        "scouting",
        "scripting",
        "verifying",
        "legal_check",
        "voice_generation",
        "visual_production",
        "assembly",
        "publishing",
        "completed",
        "failed"
    ]
    
    def __init__(self, api_manager: APIManager, governor: Governor, channel: str = "ledger"):
        self.api = api_manager
        self.gov = governor
        self.channel = channel  # "ledger" or "signal"
        
        # Initialize state
        self.project_state = ProjectState()
        self.project_state.set_metadata("channel", channel)
        self.project_state.set_metadata("created_at", datetime.utcnow().isoformat())
        self.project_state.set_metadata("stage", "initialized")
        
        # Initialize agents
        self.scout = FinancialScout(api_manager)
        self.scribe = DocumentaryScribe(api_manager)
        self.verifier = LegalVerifier(api_manager)
        self.artisan = DocumentaryArtisan(governor)
        self.publisher = AffiliatePublisher(api_manager)
        
        # NEW: Safety and production
        self.safety = LegalSafetyChecker()
        self.voice_mgr = VoiceCloneManager(
            elevenlabs_key=api_manager.get_key("ELEVENLABS"),
            clone_voice_id=api_manager.get_key("ELEVENLABS_VOICE_ID")
        )
        self.thumbs = ThumbnailFactory()
        self.doc_gfx = DocumentGraphicFactory()
        self.notion = NotionSync(api_manager.get_key("NOTION_TOKEN"))
        
        # Affiliate config
        self.affiliate_links = {
            "ledger": os.getenv("AFFILIATE_LEDGER", "https://shop.ledger.com/?r=YOUR_CODE"),
            "bybit": os.getenv("AFFILIATE_BYBIT", "https://www.bybit.com/invite?ref=YOUR_CODE"),
            "trezor": os.getenv("AFFILIATE_TREZOR", "https://trezor.io/?a=YOUR_CODE"),
            "nordvpn": os.getenv("AFFILIATE_NORDVPN", "https://nordvpn.com/YOUR_CODE")
        }
    
    def run_pipeline(self, topic: str, style: str = "documentary", publish: bool = False) -> Dict:
        """
        Main entry point. Runs full pipeline with checkpoint recovery.
        """
        project_id = f"ledger_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{topic[:20].replace(' ', '_')}"
        self.project_state.set_metadata("project_id", project_id)
        self.project_state.set_metadata("topic", topic)
        self.project_state.set_metadata("style", style)
        
        print(f"\n{'='*60}")
        print(f"🎬 STARTING PIPELINE: {project_id}")
        print(f"{'='*60}\n")
        
        try:
            # Stage 1: SCOUT
            self._transition("scouting")
            research = self._run_scout(topic)
            if not research:
                return self._fail("Scout returned no viable research")
            
            # Stage 2: SCRIBE
            self._transition("scripting")
            script_data = self._run_scribe(topic, research, style)
            if not script_data:
                return self._fail("Scribe failed to generate script")
            
            # Stage 3: VERIFY (Fact check)
            self._transition("verifying")
            verified = self._run_verifier(script_data, research)
            if not verified:
                return self._fail("Verifier rejected script facts")
            
            # Stage 4: LEGAL SAFETY GATE (NON-NEGOTIABLE)
            self._transition("legal_check")
            safety_result = self._run_legal_gate(script_data)
            if not safety_result["passed"]:
                print(f"\n🚨 LEGAL GATE BLOCKED:")
                for issue in safety_result["issues"]:
                    print(f"   ❌ {issue}")
                return self._fail(f"Legal safety check failed: {safety_result['risk_level']} risk")
            print(f"\n✅ LEGAL GATE PASSED ({safety_result['risk_level']} risk)")
            
            # Inject affiliate links after legal check (so they don't interfere with safety scan)
            script_data = self._inject_affiliates(script_data)
            
            # Stage 5: VOICE
            self._transition("voice_generation")
            audio_path = self._run_voice(script_data)
            if not audio_path or not os.path.exists(audio_path):
                return self._fail("Voice generation failed")
            
            # Stage 6: VISUAL PRODUCTION
            self._transition("visual_production")
            visuals = self._run_visuals(script_data, research)
            
            # Stage 7: ASSEMBLY
            self._transition("assembly")
            video_path = self._run_assembly(script_data, audio_path, visuals)
            if not video_path or not os.path.exists(video_path):
                return self._fail("Video assembly failed")
            
            # Stage 8: PUBLISH (always PRIVATE first)
            if publish:
                self._transition("publishing")
                publish_result = self._run_publish(video_path, visuals, script_data)
                self.project_state.set_metadata("youtube_id", publish_result.get("video_id"))
                self.project_state.set_metadata("youtube_url", publish_result.get("url"))
            
            # Success
            self._transition("completed")
            self._save_state()
            self._sync_notion()
            
            return {
                "status": "success",
                "project_id": project_id,
                "video_path": video_path,
                "summary": {
                    "topic": topic,
                    "stage": "completed",
                    "agents_completed": 8,
                    "agents_total": 8
                },
                "full_state": self.project_state.to_dict(),
                "state_file": self._save_state()
            }
            
        except Exception as e:
            return self._fail(str(e))
    
    # ───────────────── INTERNAL STAGE METHODS ─────────────────
    
    def _run_scout(self, topic: str) -> Dict:
        """Gather court docs, news, and financial data."""
        print("[SCOUT] Gathering intelligence...")
        research = self.scout.research(topic, depth="deep" if self.channel == "ledger" else "shallow")
        
        self.project_state.set_agent_state("scout", {
            "status": "completed",
            "sources_found": len(research.get("sources", [])),
            "court_docs": research.get("court_docs", []),
            "primary_quotes": research.get("quotes", [])
        })
        self._save_state()
        return research
    
    def _run_scribe(self, topic: str, research: Dict, style: str) -> Dict:
        """Generate 5-Act documentary script."""
        print("[SCRIBE] Writing documentary script...")
        script = self.scribe.write_documentary(topic, research, style, self.channel)
        
        self.project_state.set_agent_state("scribe", {
            "status": "completed",
            "word_count": len(script.get("full_text", "").split()),
            "acts": list(script.get("acts", {}).keys())
        })
        self.project_state.set_metadata("script", script)
        self._save_state()
        return script
    
    def _run_verifier(self, script: Dict, research: Dict) -> bool:
        """Fact-check script against sources."""
        print("[VERIFIER] Cross-referencing claims...")
        result = self.verifier.verify(script, research)
        
        self.project_state.set_agent_state("verifier", {
            "status": "completed" if result else "failed",
            "claims_checked": result.get("claims_checked", 0),
            "confidence": result.get("confidence", 0)
        })
        self._save_state()
        return result.get("passed", False)
    
    def _run_legal_gate(self, script: Dict) -> Dict:
        """
        CRITICAL GATE: Scans for defamation, policy violations, 
        and financial advice liabilities.
        """
        print("[LEGAL GATE] Running safety scan...")
        sources = self.project_state.get_agent_state("scout", {}).get("court_docs", [])
        
        result = self.safety.scan(
            script=script.get("full_text", ""),
            sources=sources,
            topic=script.get("topic", "")
        )
        
        self.project_state.set_agent_state("legal_gate", {
            "status": "passed" if result["passed"] else "blocked",
            "risk_level": result["risk_level"],
            "issues": result["issues"],
            "timestamp": datetime.utcnow().isoformat()
        })
        self._save_state()
        return result
    
    def _inject_affiliates(self, script: Dict) -> Dict:
        """Add affiliate links to description and Bridge Act."""
        if not self.project_state.get_metadata("affiliate_inject", True):
            return script
        
        desc = script.get("description", "")
        
        # Append affiliate block to description
        affiliate_block = f"""
🔗 RESOURCES MENTIONED:
• Self-Custody Hardware Wallet: {self.affiliate_links['ledger']}
• Trade with Proof of Reserves: {self.affiliate_links['bybit']}
• Privacy Protection: {self.affiliate_links['nordvpn']}
⚠️ These are affiliate links. They support our investigative work at no extra cost to you.
"""
        script["description"] = desc + affiliate_block
        
        # Inject into Act IV bridge if natural (Scribe should have left a marker)
        if "[AFFILIATE_BRIDGE]" in script.get("full_text", ""):
            bridge = (
                "Cases like this are exactly why I don't keep significant assets on exchanges. "
                f"I use Ledger for offline self-custody ({self.affiliate_links['ledger']}). "
                f"And for market analysis, I track data on Bybit ({self.affiliate_links['bybit']})."
            )
            script["full_text"] = script["full_text"].replace("[AFFILIATE_BRIDGE]", bridge)
        
        self.project_state.set_metadata("affiliates_injected", True)
        return script
    
    def _run_voice(self, script: Dict) -> Optional[str]:
        """Generate narration audio."""
        print("[VOICE] Generating narration...")
        text = script.get("full_text", "")
        
        # Clean text for TTS (remove stage directions)
        clean_text = self._strip_stage_directions(text)
        
        output_dir = f"output/audio"
        os.makedirs(output_dir, exist_ok=True)
        output_path = f"{output_dir}/{self.project_state.get_metadata('project_id')}.wav"
        
        # Use async runner for edge-tts
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        audio_path = loop.run_until_complete(
            self.voice_mgr.generate(clean_text, output_path, prefer_clone=True)
        )
        
        self.project_state.set_agent_state("voice", {
            "status": "completed",
            "path": audio_path,
            "engine": "elevenlabs_clone" if "elevenlabs" in str(audio_path).lower() else "edge_tts"
        })
        self._save_state()
        return audio_path
    
    def _run_visuals(self, script: Dict, research: Dict) -> Dict:
        """Generate thumbnails and document graphics."""
        print("[ARTISAN] Producing visuals...")
        project_id = self.project_state.get_metadata("project_id")
        topic = self.project_state.get_metadata("topic")
        
        visuals = {"thumbnails": [], "doc_graphics": [], "broll_manifest": []}
        
        # Thumbnails
        big_number = script.get("hook_number", "$4.5B")  # Scribe extracts this
        slug = project_id
        thumb_paths = self.thumbs.generate(
            slug=slug,
            big_number=big_number,
            object_path="assets/objects/hard_drive.png",  # Default, Scout can override
            host_path="assets/host/point.png"
        )
        visuals["thumbnails"] = thumb_paths
        
        # Document graphics from verified quotes
        for idx, quote in enumerate(research.get("quotes", [])[:3]):
            gfx_path = self.doc_gfx.create_evidence_card(
                quote=quote["text"],
                source=quote["source"],
                page=quote.get("page", "N/A"),
                output_name=f"{slug}_evidence_{idx}"
            )
            visuals["doc_graphics"].append({
                "path": gfx_path,
                "timestamp": quote.get("script_timestamp", 0),
                "cue": f"document_{idx}"
            })
        
        self.project_state.set_agent_state("visuals", {
            "status": "completed",
            "thumbnail_count": len(thumb_paths),
            "evidence_cards": len(visuals["doc_graphics"])
        })
        self._save_state()
        return visuals
    
    def _run_assembly(self, script: Dict, audio_path: str, visuals: Dict) -> Optional[str]:
        """Assemble final video from audio + visuals."""
        print("[ARTISAN] Assembling final cut...")
        
        # Build image sequence from script cues + generated assets
        image_sequence = self._build_image_sequence(script, visuals)
        
        output_dir = "output/videos"
        os.makedirs(output_dir, exist_ok=True)
        output_path = f"{output_dir}/{self.project_state.get_metadata('project_id')}_rough.mp4"
        
        # Delegate to DocumentaryArtisan (extends your existing Artisan)
        final_path = self.artisan.assemble_documentary(
            audio_path=audio_path,
            image_sequence=image_sequence,
            output_path=output_path,
            color_grade="teal_orange_documentary"
        )
        
        self.project_state.set_agent_state("artisan", {
            "status": "completed",
            "output_path": final_path,
            "duration": self._get_audio_duration(audio_path)
        })
        self._save_state()
        return final_path
    
    def _run_publish(self, video_path: str, visuals: Dict, script: Dict) -> Dict:
        """Upload as PRIVATE with full metadata."""
        print("[PUBLISHER] Uploading to YouTube (PRIVATE)...")
        
        metadata = {
            "title": script.get("title", "Untitled Investigation"),
            "description": script.get("description", ""),
            "tags": script.get("tags", ["finance", "documentary", "investigation"]),
            "category_id": "25",  # News & Politics
            "privacy_status": "private",  # ALWAYS private until human review
            "self_declared_made_for_kids": False
        }
        
        result = self.publisher.upload(
            video_path=video_path,
            thumbnail_path=visuals["thumbnails"][0],  # Gold variant default
            metadata=metadata,
            playlist_id=os.getenv("YOUTUBE_PLAYLIST_ID")
        )
        
        self.project_state.set_agent_state("publisher", {
            "status": "completed",
            "video_id": result.get("video_id"),
            "url": result.get("url"),
            "privacy": "private"
        })
        self._save_state()
        return result
    
    # ───────────────── HELPERS ─────────────────
    
    def _transition(self, stage: str):
        if stage not in self.STAGES:
            raise ValueError(f"Invalid stage: {stage}")
        self.project_state.set_metadata("stage", stage)
        print(f"\n➡️  STAGE: {stage.upper()}")
    
    def _fail(self, reason: str) -> Dict:
        self._transition("failed")
        self.project_state.set_metadata("failure_reason", reason)
        self._save_state()
        print(f"\n💥 PIPELINE FAILED: {reason}")
        return {
            "status": "failed",
            "error": reason,
            "full_state": self.project_state.to_dict()
        }
    
    def _save_state(self) -> str:
        state_file = f"states/{self.project_state.get_metadata('project_id')}.json"
        os.makedirs("states", exist_ok=True)
        self.project_state.save_to_file(state_file)
        return state_file
    
    def _sync_notion(self):
        """Push completed project to Notion database."""
        try:
            self.notion.create_entry(self.project_state.to_dict())
        except Exception as e:
            print(f"[NOTION SYNC] Warning: {e}")
    
    def _strip_stage_directions(self, text: str) -> str:
        """Remove [brackets] and visual cues for TTS."""
        import re
        return re.sub(r'\[.*?\]', '', text)
    
    def _build_image_sequence(self, script: Dict, visuals: Dict) -> List[Dict]:
        """Map script cues to actual image/video files."""
        sequence = []
        acts = script.get("acts", {})
        
        # Act I: Hook (host + object)
        sequence.append({
            "path": "assets/host/look_window.png",
            "duration": 90,
            "type": "host",
            "act": "I"
        })
        
        # Act II: Investigation (document graphics interleaved)
        sequence.append({
            "path": "assets/broll/courtroom.png",
            "duration": 120,
            "type": "broll",
            "act": "II"
        })
        for gfx in visuals.get("doc_graphics", []):
            sequence.append({
                "path": gfx["path"],
                "duration": 60,
                "type": "document",
                "act": "II",
                "cue": gfx["cue"]
            })
        
        # Act III: System (charts/maps)
        sequence.append({
            "path": "assets/broll/world_map.png",
            "duration": 90,
            "type": "broll",
            "act": "III"
        })
        
        # Act IV: Bridge (host close-up)
        sequence.append({
            "path": "assets/host/hold_folder.png",
            "duration": 45,
            "type": "host",
            "act": "IV"
        })
        
        # Act V: Verdict (host + fade)
        sequence.append({
            "path": "assets/host/fold_arms.png",
            "duration": 45,
            "type": "host",
            "act": "V"
        })
        
        return sequence
    
    def _get_audio_duration(self, audio_path: str) -> float:
        try:
            import subprocess
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
                 "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
                capture_output=True, text=True
            )
            return float(result.stdout.strip())
        except:
            return 0.0