#!/usr/bin/env python3
"""
BRAND ASSETS
Centralized brand identity management for The Ledger documentary channel.
"""

from typing import Dict, Tuple


class BrandAssets:
    """Manages brand colors, fonts, and visual identity."""
    
    # The Ledger Color Palette
    COLORS = {
        "deep_navy": (10, 14, 31),           # #0A0E1F - Primary background
        "gold": (212, 175, 55),              # #D4AF37 - Accent
        "crimson": (196, 30, 58),            # #C41E3A - Alert/CTA
        "white": (255, 255, 255),            # #FFFFFF - Text
        "parchment": (250, 240, 230),        # #FAF0E6 - Evidence cards
        "highlight": (255, 255, 204),        # #FFFFCC - Evidence highlight
        "black": (0, 0, 0),                  # #000000
        "source_gray": (51, 51, 51),         # #333333 - Attribution
        "red_stamp": (196, 30, 58),          # #C41E3A - Watermark
    }
    
    # Typography
    FONTS = {
        "primary": "DejaVuSans",
        "primary_bold": "DejaVuSans-Bold",
        "monospace": "DejaVuSansMono",
        "fallback": "Arial"
    }
    
    # Documentary LUTs
    LUTS = {
        "ledger_teal_orange": {
            "name": "Ledger Teal/Orange",
            "description": "Cinematic financial documentary look",
            "shadows": (20, 40, 50),
            "midtones": (128, 128, 128),
            "highlights": (255, 160, 100),
            "contrast": 1.2,
            "saturation": 1.1
        },
        "cold_case": {
            "name": "Cold Case",
            "description": "Mysterious, desaturated look",
            "shadows": (30, 30, 40),
            "midtones": (100, 100, 120),
            "highlights": (200, 200, 220),
            "contrast": 1.15,
            "saturation": 0.9
        },
        "warm_evidence": {
            "name": "Warm Evidence",
            "description": "Warm, archival feel",
            "shadows": (60, 40, 30),
            "midtones": (140, 120, 100),
            "highlights": (255, 220, 180),
            "contrast": 1.1,
            "saturation": 1.05
        }
    }
    
    # Video Specs
    VIDEO = {
        "resolution": (1920, 1080),    # 1080p
        "fps": 30,
        "bitrate": "8000k",
        "audio_bitrate": "192k",
        "preset": "slow"               # Quality over speed
    }
    
    # Thumbnail Specs
    THUMBNAIL = {
        "resolution": (1280, 720),
        "safe_zone": (154, 0, 1126, 720),  # Text safe area (no face overlap)
        "text_max_width": 900
    }
    
    def __init__(self):
        self.active_lut = "ledger_teal_orange"
    
    def get_color(self, name: str) -> Tuple[int, int, int]:
        """Get RGB color by name."""
        return self.COLORS.get(name, self.COLORS["white"])
    
    def get_hex(self, name: str) -> str:
        """Get hex color by name."""
        r, g, b = self.get_color(name)
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def get_font_path(self, style: str = "primary") -> str:
        """Get font path for style."""
        font_name = self.FONTS.get(style, self.FONTS["primary"])
        return f"{font_name}.ttf"
    
    def get_lut(self, name: str = None) -> Dict:
        """Get LUT preset."""
        lut_name = name or self.active_lut
        return self.LUTS.get(lut_name, self.LUTS["ledger_teal_orange"])
    
    def set_active_lut(self, name: str):
        """Set active LUT preset."""
        if name in self.LUTS:
            self.active_lut = name
    
    def get_video_specs(self) -> Dict:
        """Get video specifications."""
        return self.VIDEO.copy()
    
    def get_thumbnail_specs(self) -> Dict:
        """Get thumbnail specifications."""
        return self.THUMBNAIL.copy()


# Default instance
brand = BrandAssets()

if __name__ == "__main__":
    print("Available colors:", list(BrandAssets.COLORS.keys()))
    print("Available LUTs:", list(BrandAssets.LUTS.keys()))
    print("Gold hex:", brand.get_hex("gold"))
