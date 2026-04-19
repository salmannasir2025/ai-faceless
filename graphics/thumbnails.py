from PIL import Image, ImageDraw, ImageFont
import os

class ThumbnailFactory:
    """Generates two thumbnail variants per topic following The Ledger brand."""
    
    PALETTE = {
        "deep_navy": (10, 14, 31),
        "gold": (212, 175, 55),
        "crimson": (196, 30, 58),
        "white": (255, 255, 255),
        "black": (0, 0, 0)
    }
    
    def __init__(self, output_dir="./output/thumbnails"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self._load_fonts()
    
    def _load_fonts(self):
        try:
            self.font_big = ImageFont.truetype("DejaVuSans-Bold.ttf", 120)
            self.font_action = ImageFont.truetype("DejaVuSans-Bold.ttf", 90)
            self.font_small = ImageFont.truetype("DejaVuSans.ttf", 40)
        except:
            self.font_big = ImageFont.load_default()
            self.font_action = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
    
    def generate(self, slug: str, big_number: str, object_path: str, host_path: str) -> list:
        variants = []
        for color_name in ["gold", "white"]:
            img = Image.new('RGB', (1280, 720), color=self.PALETTE["deep_navy"])
            draw = ImageDraw.Draw(img)
            
            # Vignette
            for i in range(100):
                draw.rectangle([i, i, 1280-i, 720-i], outline=(0,0,0))
            
            # Object
            if os.path.exists(object_path):
                obj = Image.open(object_path).convert("RGBA").resize((350, 350))
                img.paste(obj, (100, 200), obj)
            
            # Host silhouette
            if os.path.exists(host_path):
                host = Image.open(host_path).convert("RGBA").resize((300, 450))
                img.paste(host, (900, 150), host)
            
            # Number
            num_color = self.PALETTE["gold"] if color_name == "gold" else self.PALETTE["white"]
            draw.text((80, 40), big_number, fill=num_color, font=self.font_big, stroke_width=3, stroke_fill="black")
            
            # Action word
            draw.text((80, 580), "EXPOSED", fill=self.PALETTE["crimson"], font=self.font_action, stroke_width=3, stroke_fill="black")
            
            # Channel watermark
            draw.text((1000, 680), "THE LEDGER", fill=self.PALETTE["gold"], font=self.font_small)
            
            out = f"{self.output_dir}/thumb_{slug}_{color_name}.png"
            img.save(out)
            variants.append(out)
        
        return variants

3. voice/clone_manager.py (NEW)
Wraps ElevenLabs voice clone + free Edge-TTS fallback.