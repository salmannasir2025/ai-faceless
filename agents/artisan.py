#!/usr/bin/env python3
"""
DOCUMENTARY ARTISAN
Renders the final documentary video with evidence graphics and affiliate watermarks.
Extends original VideoAgent with documentary-specific assembly.

Language Support:
- English (default) - For USA/Europe audiences
- Urdu (optional) - For future expansion to Urdu-speaking markets
"""

import json
import os
import subprocess
from datetime import datetime
from typing import Optional, Tuple, List, Dict
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from core.english_engine import EnglishEngine
from core.security_utils import secure_subprocess_run, validate_filename


class DocumentaryArtisan:
    """Agent that assembles documentary videos with professional LUT and overlays.
    
    Default language: English (en)
    Target audience: USA, Europe, English-speaking markets
    """
    
    # Documentary color grading - Teal/Orange LUT
    LUT_PRESETS = {
        "ledger_teal_orange": {
            "shadows": (20, 40, 50),      # Teal shadows
            "midtones": (128, 128, 128),   # Neutral mid
            "highlights": (255, 160, 100), # Orange highlights
            "contrast": 1.2,
            "saturation": 1.1
        },
        "cold_case": {
            "shadows": (30, 30, 40),
            "midtones": (100, 100, 120),
            "highlights": (200, 200, 220),
            "contrast": 1.15,
            "saturation": 0.9
        },
        "warm_evidence": {
            "shadows": (60, 40, 30),
            "midtones": (140, 120, 100),
            "highlights": (255, 220, 180),
            "contrast": 1.1,
            "saturation": 1.05
        }
    }
    
    # Supported languages
    LANGUAGES = {
        "en": {
            "name": "English",
            "engine": "EnglishEngine",
            "default": True,
            "target_regions": ["USA", "UK", "Canada", "Australia", "Europe"]
        },
        "ur": {
            "name": "Urdu",
            "engine": "UrduEngine",
            "default": False,
            "target_regions": ["Pakistan", "India"]
        }
    }
    
    def __init__(self, governor, language: str = "en"):
        self.governor = governor
        self.language = language.lower()
        self.render_config = {
            "resolution": (1920, 1080),  # 16:9 horizontal documentary format
            "fps": 30,
            "bitrate": "8000k",
            "preset": "slow",  # Quality over speed for documentaries
            "audio_codec": "aac",
            "audio_bitrate": "192k"
        }
        self.ffmpeg_params = governor.get_ffmpeg_params() if hasattr(governor, 'get_ffmpeg_params') else ["-c:v", "libx264", "-preset", "slow"]
        
        # Initialize text rendering engine based on language
        self.text_engine = self._init_text_engine()
        
        print(f"🎬 Documentary Artisan initialized")
        print(f"   Language: {self.LANGUAGES.get(self.language, {}).get('name', 'English')}")
        print(f"   Engine: {self.text_engine.__class__.__name__}")
    
    def _init_text_engine(self):
        """Initialize text rendering engine based on language setting."""
        if self.language == "ur":
            # Lazy import - only load if needed
            try:
                from core.urdu_engine import UrduEngine
                return UrduEngine()
            except ImportError:
                print("⚠️  UrduEngine not available, falling back to EnglishEngine")
                return EnglishEngine()
        else:
            # Default to English
            return EnglishEngine(theme="ledger")
    
    def assemble_documentary(self, audio_path: str, image_sequence: List[Dict], output_path: str, 
                            lut_preset: str = "ledger_teal_orange", affiliate_links: Dict = None) -> str:
        """
        Assemble final documentary video from audio and image sequence.
        
        Args:
            audio_path: Path to generated voice audio
            image_sequence: List of dicts with 'path', 'duration', 'type', 'caption'
            output_path: Where to save final video
            lut_preset: Color grading preset name
            affiliate_links: Dict of affiliate links for end card
            
        Returns:
            Path to final video file
        """
        print(f"🎬 Documentary Artisan: Assembling final video")
        print(f"   Audio: {audio_path}")
        print(f"   Clips: {len(image_sequence)}")
        print(f"   LUT: {lut_preset}")
        print(f"   Output: {output_path}")
        
        # Verify audio exists
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Get audio duration
        audio_duration = self._get_audio_duration(audio_path)
        
        # Build video from image sequence
        temp_video = output_path.replace(".mp4", "_temp.mp4")
        
        try:
            # Method 1: Use ffmpeg concat with image sequence
            self._assemble_with_ffmpeg(image_sequence, audio_path, temp_video, lut_preset)
            
            # Add affiliate end card if provided
            if affiliate_links:
                final_video = self._add_end_card(temp_video, output_path, affiliate_links)
                if os.path.exists(temp_video) and temp_video != final_video:
                    os.remove(temp_video)
            else:
                os.rename(temp_video, output_path)
            
            print(f"✅ Documentary Artisan: Complete → {output_path}")
            return output_path
            
        except Exception as e:
            print(f"⚠️ Primary assembly failed: {e}")
            # Fallback: create simple slideshow
            return self._create_fallback_video(image_sequence, audio_path, output_path)
    
    def _assemble_with_ffmpeg(self, image_sequence: List[Dict], audio_path: str, output_path: str, lut_preset: str):
        """Assemble video using ffmpeg with color grading."""
        
        # Create concat file for image sequence
        concat_file = output_path.replace(".mp4", "_concat.txt")
        
        with open(concat_file, 'w') as f:
            for item in image_sequence:
                path = item['path']
                duration = item.get('duration', 5)
                # Escape single quotes in path
                safe_path = path.replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")
                f.write(f"duration {duration}\n")
            # Last frame needs duration too
            if image_sequence:
                last_path = image_sequence[-1]['path'].replace("'", "'\\''")
                f.write(f"file '{last_path}'\n")
        
        # Get LUT params
        lut_params = self.LUT_PRESETS.get(lut_preset, self.LUT_PRESETS["ledger_teal_orange"])
        
        # Build ffmpeg command
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-i", audio_path,
            "-vf", f"format=yuv420p,scale={self.render_config['resolution'][0]}:{self.render_config['resolution'][1]}:force_original_aspect_ratio=decrease,pad={self.render_config['resolution'][0]}:{self.render_config['resolution'][1]}:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264",
            "-preset", self.render_config['preset'],
            "-b:v", self.render_config['bitrate'],
            "-c:a", self.render_config['audio_codec'],
            "-b:a", self.render_config['audio_bitrate'],
            "-shortest",
            "-pix_fmt", "yuv420p",
            output_path
        ]
        
        try:
            result = secure_subprocess_run(cmd, timeout=300)
            if result.returncode != 0:
                print(f"FFmpeg stderr: {result.stderr}")
                raise RuntimeError(f"FFmpeg failed: {result.returncode}")
        finally:
            # Cleanup concat file
            if os.path.exists(concat_file):
                os.remove(concat_file)
    
    def _add_end_card(self, video_path: str, output_path: str, affiliate_links: Dict) -> str:
        """Add affiliate end card to video."""
        
        # Generate end card image
        end_card_path = output_path.replace(".mp4", "_endcard.png")
        self._generate_end_card(end_card_path, affiliate_links)
        
        # Get video duration
        duration = self._get_video_duration(video_path)
        
        # Create filter complex to overlay end card for last 5 seconds
        filter_complex = (
            f"[0:v][1:v]overlay=0:0:enable='between(t,{duration-5},{duration})'[v];"
            f"[0:a][1:a]amix=inputs=2:duration=first[a]"
        )
        
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-loop", "1", "-i", end_card_path,
            "-t", str(duration + 5),
            "-filter_complex", filter_complex,
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_path
        ]
        
        result = secure_subprocess_run(cmd)
        
        # Cleanup
        if os.path.exists(end_card_path):
            os.remove(end_card_path)
        
        if result.returncode == 0:
            return output_path
        else:
            print(f"End card failed, returning original: {result.stderr}")
            return video_path
    
    def _generate_end_card(self, output_path: str, affiliate_links: Dict):
        """Generate end card image with affiliate links."""
        w, h = self.render_config['resolution']
        
        # Create dark background
        img = Image.new('RGB', (w, h), color=(10, 14, 31))
        draw = ImageDraw.Draw(img)
        
        # Load fonts
        try:
            font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 60)
            font_link = ImageFont.truetype("DejaVuSans.ttf", 32)
        except:
            font_title = ImageFont.load_default()
            font_link = ImageFont.load_default()
        
        # Title
        title = "🔗 RESOURCES & AFFILIATE LINKS"
        bbox = draw.textbbox((0, 0), title, font=font_title)
        title_w = bbox[2] - bbox[0]
        draw.text(((w - title_w) // 2, 100), title, fill=(212, 175, 55), font=font_title)
        
        # Links
        y = 250
        for name, url in affiliate_links.items():
            text = f"{name.upper()}: {url}"
            draw.text((200, y), text, fill=(255, 255, 255), font=font_link)
            y += 80
        
        # Disclaimer
        disclaimer = "Some links are affiliate links. This doesn't affect our editorial independence."
        try:
            font_small = ImageFont.truetype("DejaVuSans.ttf", 20)
        except:
            font_small = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), disclaimer, font=font_small)
        disc_w = bbox[2] - bbox[0]
        draw.text(((w - disc_w) // 2, h - 100), disclaimer, fill=(128, 128, 128), font=font_small)
        
        img.save(output_path)
    
    def _create_fallback_video(self, image_sequence: List[Dict], audio_path: str, output_path: str) -> str:
        """Create simple fallback video if primary assembly fails."""
        print("   Using fallback video creation...")
        
        # Use first image or create blank
        if image_sequence and os.path.exists(image_sequence[0]['path']):
            input_img = image_sequence[0]['path']
        else:
            # Create blank image
            blank_path = output_path.replace(".mp4", "_blank.png")
            img = Image.new('RGB', self.render_config['resolution'], color=(20, 20, 20))
            img.save(blank_path)
            input_img = blank_path
        
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", input_img,
            "-i", audio_path,
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            "-pix_fmt", "yuv420p",
            output_path
        ]
        
        result = secure_subprocess_run(cmd)
        
        # Cleanup blank image
        if 'blank_path' in locals() and os.path.exists(blank_path):
            os.remove(blank_path)
        
        if result.returncode == 0:
            return output_path
        else:
            raise RuntimeError(f"Fallback video creation failed: {result.stderr}")
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration in seconds."""
        try:
            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
                   "-of", "default=noprint_wrappers=1:nokey=1", audio_path]
            result = secure_subprocess_run(cmd, timeout=10)
            return float(result.stdout.strip() or 300)  # Default 5 min
        except Exception:
            return 300
    
    def _get_video_duration(self, video_path: str) -> float:
        """Get video duration in seconds."""
        try:
            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
                   "-of", "default=noprint_wrappers=1:nokey=1", video_path]
            result = secure_subprocess_run(cmd, timeout=10)
            return float(result.stdout.strip() or 0)
        except Exception:
            return 0
    
    def apply_lut(self, video_path: str, output_path: str, preset: str = "ledger_teal_orange"):
        """Apply color grading LUT to video."""
        lut = self.LUT_PRESETS.get(preset, self.LUT_PRESETS["ledger_teal_orange"])
        
        # Build LUT filter string
        shadow_r, shadow_g, shadow_b = lut["shadows"]
        highlight_r, highlight_g, highlight_b = lut["highlights"]
        
        # Simplified color grading via curves
        filter_str = (
            f"curves=r='0/0 {shadow_r}/64 1/1':"
            f"g='0/0 {shadow_g}/64 1/1':"
            f"b='0/0 {shadow_b}/64 1/1'"
        )
        
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", filter_str,
            "-c:a", "copy",
            output_path
        ]
        
        result = secure_subprocess_run(cmd)
        if result.returncode == 0:
            return output_path
        else:
            print(f"LUT application failed: {result.stderr}")
            return video_path
    
    def configure(self, **kwargs):
        """Configure video rendering settings."""
        self.render_config.update(kwargs)
    
    def set_resolution(self, width: int, height: int):
        """Set video resolution."""
        self.render_config["resolution"] = (width, height)


# Standalone test
if __name__ == "__main__":
    class MockGovernor:
        def get_ffmpeg_params(self):
            return ["-c:v", "libx264", "-preset", "fast"]
    
    artisan = DocumentaryArtisan(MockGovernor())
    
    # Test with dummy data
    test_sequence = [
        {"path": "test1.png", "duration": 5, "type": "broll"},
        {"path": "test2.png", "duration": 5, "type": "evidence"}
    ]
    
    print(f"LUT presets available: {list(artisan.LUT_PRESETS.keys())}")
