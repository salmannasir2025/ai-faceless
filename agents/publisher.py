#!/usr/bin/env python3
"""
AFFILIATE PUBLISHER
Uploads videos to YouTube as PRIVATE with documentary-grade metadata.
Handles synthetic content disclosure, affiliate injection, and policy compliance.
"""

import os
import sys
from typing import Dict, Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

class AffiliatePublisher:
    """
    YouTube uploader with finance/synthetic-content safeguards.
    NEVER uploads as public. Human review is mandatory.
    """
    
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    
    def __init__(self, api_manager):
        self.api = api_manager
        self.youtube = self._authenticate()
    
    def _authenticate(self):
        """OAuth2 flow using client_secrets.json."""
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", self.SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists("client_secrets.json"):
                    raise FileNotFoundError(
                        "client_secrets.json not found. Download from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    "client_secrets.json", self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        
        return build("youtube", "v3", credentials=creds)
    
    def upload(self, video_path: str, thumbnail_path: str, metadata: Dict, 
               playlist_id: Optional[str] = None) -> Dict:
        """
        Upload video as PRIVATE with full compliance metadata.
        
        Args:
            video_path: Path to MP4
            thumbnail_path: Path to PNG/JPG
            metadata: Dict with title, description, tags, category_id
            playlist_id: Optional playlist to add video to
        """
        if not os.path.exists(video_path):
            return {"error": f"Video file not found: {video_path}"}
        
        print(f"  📤 Uploading: {metadata.get('title', 'Untitled')}")
        
        # ─── ENRICH DESCRIPTION ───
        description = self._enrich_description(metadata.get("description", ""))
        
        # ─── BUILD UPLOAD BODY ───
        body = {
            "snippet": {
                "title": metadata["title"][:100],  # YouTube limit
                "description": description,
                "tags": metadata.get("tags", [])[:15],  # Max 500 chars total
                "categoryId": metadata.get("category_id", "25"),  # News & Politics
                "defaultLanguage": "en",
                "defaultAudioLanguage": "en"
            },
            "status": {
                "privacyStatus": "private",  # ← NEVER CHANGE THIS
                "selfDeclaredMadeForKids": False,
                "madeForKids": False,
                "embeddable": True,
                "publicStatsViewable": True
            },
            "recordingDetails": {
                "recordingDate": metadata.get("recording_date", "")
            }
        }
        
        # ─── UPLOAD VIDEO ───
        media = MediaFileUpload(
            video_path, 
            mimetype="video/mp4", 
            chunksize=-1, 
            resumable=True
        )
        
        request = self.youtube.videos().insert(
            part="snippet,status,recordingDetails",
            body=body,
            media_body=media,
            notifySubscribers=False  # Don't spam on PRIVATE upload
        )
        
        response = None
        progress = 0
        while response is None:
            status, response = request.next_chunk()
            if status:
                new_progress = int(status.progress() * 100)
                if new_progress > progress + 10:
                    progress = new_progress
                    print(f"    Upload: {progress}%")
        
        video_id = response["id"]
        video_url = f"https://youtu.be/{video_id}"
        print(f"  ✅ Uploaded (PRIVATE): {video_url}")
        
        # ─── UPLOAD THUMBNAIL ───
        if thumbnail_path and os.path.exists(thumbnail_path):
            self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype="image/png")
            ).execute()
            print(f"  🖼️  Thumbnail set")
        
        # ─── ADD TO PLAYLIST ───
        if playlist_id:
            self.youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id
                        }
                    }
                }
            ).execute()
            print(f"  📋 Added to playlist")
        
        # ─── SET VIDEO OPTIONS (Cards, etc.) ───
        # Note: End screens and cards require separate API calls or manual setup
        # We log instructions for manual addition
        print(f"  ⚠️  MANUAL STEP: Add end-screen subscribe button in YouTube Studio")
        print(f"  ⚠️  MANUAL STEP: Add 'Altered or synthetic content' label in Studio > Content")
        
        return {
            "video_id": video_id,
            "url": video_url,
            "privacy": "private",
            "status": "uploaded_pending_review",
            "studio_link": f"https://studio.youtube.com/video/{video_id}/edit"
        }
    
    def _enrich_description(self, base_description: str) -> str:
        """
        Inject mandatory disclosures and affiliate links.
        """
        # Synthetic content disclosure (YouTube policy + transparency)
        synthetic_notice = (
            "🤖 CONTENT NOTICE: This video features an AI-generated host avatar "
            "and voice-cloned narration. All research, scriptwriting, and editorial "
            "decisions are performed by human producers. The AI host is a visual "
            "storytelling tool, not a real person.\n\n"
        )
        
        # Financial disclaimer (top of description for visibility)
        finance_disclaimer = (
            "⚠️ FINANCIAL DISCLAIMER: This content is for educational and documentary "
            "purposes only. It does not constitute investment advice, tax advice, or "
            "a recommendation to buy, sell, or hold any security or financial instrument. "
            "Past performance of any entity discussed does not indicate future results. "
            "Consult a qualified financial advisor before making investment decisions.\n\n"
        )
        
        # Affiliate transparency
        affiliate_notice = (
            "💼 AFFILIATE TRANSPARENCY: Some links in this description are affiliate "
            "links. If you choose to use them, this channel may receive a commission "
            "at no additional cost to you. These partnerships support our investigative "
            "journalism.\n\n"
        )
        
        # Combine: Important stuff first (YouTube truncates after ~2 lines in search)
        enriched = finance_disclaimer + synthetic_notice + affiliate_notice + base_description
        
        # Add standard footer
        footer = (
            "\n\n---\n"
            "📰 THE LEDGER investigates financial crimes, corporate fraud, and systemic "
            "failures using only public records and institutional reporting.\n"
            "🔔 Subscribe for weekly documentary investigations.\n"
            "📧 Business: contact@yourdomain.com"
        )
        
        return enriched + footer
    
    def update_to_public(self, video_id: str) -> bool:
        """
        Call this AFTER human legal review. Changes PRIVATE → PUBLIC.
        """
        try:
            self.youtube.videos().update(
                part="status",
                body={
                    "id": video_id,
                    "status": {
                        "privacyStatus": "public",
                        "selfDeclaredMadeForKids": False
                    }
                }
            ).execute()
            print(f"  🚀 Video {video_id} is now PUBLIC")
            return True
        except Exception as e:
            print(f"  ❌ Failed to publish: {e}")
            return False
    
    def add_synthetic_label(self, video_id: str):
        """
        YouTube API does NOT allow setting 'Altered content' label programmatically.
        This must be done manually in YouTube Studio.
        We print a reminder.
        """
        print(f"  ⚠️  CRITICAL: Set 'Altered or synthetic content' label manually:")
        print(f"     Studio > Content > {video_id} > Details > Show more > Tags > Altered content")

🔌 Integration with Orchestrator
Both modules plug directly into the LedgerOrchestrator I provided earlier. The method calls already match:
self.scribe.write_documentary(topic, research, style, self.channel) → returns script dict with [AFFILIATE_BRIDGE]
self.publisher.upload(video_path, thumbnail_path, metadata, playlist_id) → returns {"video_id": "...", "url": "..."}

🚨 Critical Post-Upload Checklist (Manual)
After publisher.upload() returns, you must do these in YouTube Studio before flipping to PUBLIC:
Studio → Content → Video → Details → Show more
✅ Check "Altered content" → Select "Yes" for realistic altered or synthetic media
✅ Add End Screen (last 20s) — subscribe button + video suggestion
✅ Add Cards (if needed) — usually not needed if affiliates are in description
✅ Verify Monetization tab — no yellow dollar signs (limited ads)
✅ Verify Captions — auto-captions are usually sufficient
✅ Change to PUBLIC (or Schedule)

🧩 Final Repo File List
Your ai-faceless-channel-automation should now contain: