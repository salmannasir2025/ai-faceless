"""
English Text Rendering Engine
Default engine for English text overlay in documentary videos.
Optimized for USA/Europe English-speaking audiences.
"""

from moviepy.editor import TextClip, AudioFileClip, CompositeVideoClip
from moviepy.video.fx.all import fadein, fadeout
import os


class EnglishEngine:
    """
    Renders English text overlays for documentary videos.
    Designed for professional financial documentary content.
    """
    
    # Professional documentary fonts (system defaults)
    DEFAULT_FONTS = {
        "title": "DejaVuSans-Bold",
        "body": "DejaVuSans",
        "caption": "DejaVuSans-Oblique",
        "quote": "DejaVuSerif"
    }
    
    # Documentary color schemes
    THEMES = {
        "ledger": {
            "primary": "#FFFFFF",      # White
            "secondary": "#C0C0C0",    # Silver
            "accent": "#FFD700",       # Gold
            "shadow": "#000000"        # Black
        },
        "cold": {
            "primary": "#F0F0F0",      # Off-white
            "secondary": "#A0A0A0",    # Gray
            "accent": "#4A90E2",       # Blue
            "shadow": "#1A1A2E"        # Dark blue-black
        },
        "warm": {
            "primary": "#FFF8E7",      # Cream
            "secondary": "#D4A574",    # Tan
            "accent": "#E8B84A",       # Gold
            "shadow": "#2C1810"        # Dark brown
        }
    }
    
    def __init__(self, font_config=None, theme="ledger"):
        """
        Initialize English rendering engine.
        
        Args:
            font_config: Dict with font names or None for defaults
            theme: Color theme name ("ledger", "cold", "warm")
        """
        self.fonts = {**self.DEFAULT_FONTS, **(font_config or {})}
        self.theme = self.THEMES.get(theme, self.THEMES["ledger"])
        
    def create_title_card(self, text: str, duration: float, output_path: str = None,
                         subtitle: str = None) -> TextClip:
        """
        Create a documentary title card.
        
        Args:
            text: Main title text
            duration: Duration in seconds
            subtitle: Optional subtitle text
            output_path: Optional path to save frame
            
        Returns:
            MoviePy TextClip
        """
        # Main title
        title = TextClip(
            text.upper(),
            fontsize=72,
            color=self.theme["primary"],
            font=self.fonts["title"],
            stroke_color=self.theme["shadow"],
            stroke_width=2,
            method="caption",
            size=(1920, 200),
            align="center"
        ).set_duration(duration)
        
        # Subtitle if provided
        if subtitle:
            sub = TextClip(
                subtitle,
                fontsize=36,
                color=self.theme["secondary"],
                font=self.fonts["caption"],
                method="caption",
                size=(1920, 100),
                align="center"
            ).set_duration(duration).set_position(("center", 600))
            
            title = title.set_position(("center", 400))
            composite = CompositeVideoClip([title, sub], size=(1920, 1080))
            
            # Add fade effects
            composite = fadein(composite, 1).fx(fadeout, 1)
            
            if output_path:
                composite.save_frame(output_path, t=0)
            
            return composite
        
        title = title.set_position("center")
        title = fadein(title, 1).fx(fadeout, 1)
        
        if output_path:
            title.save_frame(output_path, t=0)
        
        return title
    
    def create_caption(self, text: str, duration: float, 
                      position=("center", 900)) -> TextClip:
        """
        Create a caption/lower third for documentary.
        
        Args:
            text: Caption text
            duration: Duration in seconds
            position: Tuple (horizontal, vertical) position
            
        Returns:
            MoviePy TextClip
        """
        # Background bar
        caption = TextClip(
            text,
            fontsize=32,
            color=self.theme["primary"],
            font=self.fonts["caption"],
            bg_color=self.theme["shadow"] + "80",  # 50% opacity
            method="caption",
            size=(1800, 80),
            align="center"
        ).set_duration(duration).set_position(position)
        
        return fadein(caption, 0.5)
    
    def create_quote_overlay(self, quote: str, attribution: str, 
                           duration: float) -> CompositeVideoClip:
        """
        Create a styled quote overlay for evidence/citations.
        
        Args:
            quote: The quote text
            attribution: Source attribution (e.g., "SEC Filing, 2023")
            duration: Display duration
            
        Returns:
            CompositeVideoClip with styled quote
        """
        # Quote text
        quote_clip = TextClip(
            f'"{quote}"',
            fontsize=48,
            color=self.theme["primary"],
            font=self.fonts["quote"],
            method="caption",
            size=(1600, 400),
            align="center"
        ).set_duration(duration).set_position(("center", 300))
        
        # Attribution
        attr_clip = TextClip(
            f"— {attribution}",
            fontsize=28,
            color=self.theme["accent"],
            font=self.fonts["caption"],
            method="caption",
            size=(1600, 60),
            align="center"
        ).set_duration(duration).set_position(("center", 720))
        
        # Decorative line
        line = TextClip(
            "_" * 50,
            fontsize=20,
            color=self.theme["accent"],
            font=self.fonts["body"]
        ).set_duration(duration).set_position(("center", 700))
        
        composite = CompositeVideoClip(
            [quote_clip, line, attr_clip], 
            size=(1920, 1080),
            bg_color=self.theme["shadow"] + "40"  # Semi-transparent background
        )
        
        return fadein(composite, 0.8).fx(fadeout, 0.8)
    
    def create_end_credits(self, credits_data: list, duration: float = 10.0,
                          scroll_speed: float = 50) -> TextClip:
        """
        Create scrolling end credits.
        
        Args:
            credits_data: List of tuples (role, name) or section headers
            duration: Total duration of credits
            scroll_speed: Pixels per second
            
        Returns:
            Scrolling TextClip
        """
        # Build credits text
        lines = []
        for item in credits_data:
            if isinstance(item, tuple):
                role, name = item
                lines.append(f"{role:<20} {name}")
            else:
                lines.append("")
                lines.append(item.upper())
                lines.append("")
        
        credits_text = "\n".join(lines)
        
        # Create scrolling text
        txt_clip = TextClip(
            credits_text,
            fontsize=32,
            color=self.theme["primary"],
            font=self.fonts["body"],
            method="caption",
            size=(1200, 2000),  # Tall for scrolling
            align="center",
            interline=-10
        )
        
        # Animate scrolling
        txt_clip = txt_clip.set_duration(duration)
        # Position starts below screen and moves up
        # Note: MoviePy positioning - would need custom animation for true scroll
        
        return txt_clip
    
    def create_watermark(self, text: str = "THE LEDGER") -> TextClip:
        """
        Create channel watermark for corner placement.
        
        Args:
            text: Watermark text
            
        Returns:
            TextClip positioned for watermark
        """
        return TextClip(
            text,
            fontsize=24,
            color=self.theme["secondary"],
            font=self.fonts["body"],
            stroke_color=self.theme["shadow"],
            stroke_width=1
        ).set_duration(9999)  # Long duration for full video


if __name__ == "__main__":
    # Test the engine
    print("EnglishEngine loaded successfully")
    print("Available themes:", list(EnglishEngine.THEMES.keys()))
    print("Default fonts:", EnglishEngine.DEFAULT_FONTS)
