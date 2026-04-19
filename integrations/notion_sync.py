from PIL import Image, ImageDraw, ImageFont
import os

class DocumentGraphicFactory:
    """Generates court-document-style overlays for video evidence."""
    
    COLORS = {
        "parchment": "#FAF0E6",
        "highlight": "#FFFFCC",
        "black": "#000000",
        "red_stamp": "#C41E3A",
        "source_gray": "#333333"
    }
    
    def __init__(self, assets_dir="./assets"):
        self.assets_dir = assets_dir
        os.makedirs(assets_dir, exist_ok=True)
        self._load_fonts()
    
    def _load_fonts(self):
        try:
            self.font_quote = ImageFont.truetype("DejaVuSans-Bold.ttf", 48)
            self.font_source = ImageFont.truetype("DejaVuSans.ttf", 32)
            self.font_stamp = ImageFont.truetype("DejaVuSans-Bold.ttf", 120)
        except:
            self.font_quote = ImageFont.load_default()
            self.font_source = ImageFont.load_default()
            self.font_stamp = ImageFont.load_default()
    
    def create_evidence_card(self, quote: str, source: str, page: str, output_name: str) -> str:
        """Creates a 1920x1080 evidence card."""
        w, h = 1920, 1080
        img = Image.new('RGB', (w, h), color=self.COLORS["parchment"])
        draw = ImageDraw.Draw(img)
        
        # Highlighted text box
        margin = 200
        draw.rectangle(
            [margin, 300, w - margin, 800],
            fill=self.COLORS["highlight"],
            outline=self.COLORS["black"],
            width=4
        )
        
        # Wrap text
        words = quote.split()
        lines, line = [], []
        for word in words:
            test = " ".join(line + [word])
            bbox = draw.textbbox((0,0), test, font=self.font_quote)
            if bbox[2] - bbox[0] < (w - 2*margin - 100):
                line.append(word)
            else:
                lines.append(" ".join(line))
                line = [word]
        if line:
            lines.append(" ".join(line))
        
        # Draw quote
        y = 350
        for line in lines:
            draw.text((margin + 30, y), line, fill="black", font=self.font_quote)
            y += 60
        
        # Attribution
        draw.text(
            (margin + 30, 750),
            f"Source: {source} | Page {page}",
            fill=self.COLORS["source_gray"],
            font=self.font_source
        )
        
        # Watermark
        draw.text((w//2 - 300, h//2 - 60), "EXHIBIT A", fill="#FF000022", font=self.font_stamp)
        
        out = f"{self.assets_dir}/{output_name}.png"
        img.save(out)
        return out


if __name__ == "__main__":
    print("NotionSync module loaded successfully")