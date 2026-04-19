import os
import edge_tts
import asyncio
import subprocess
from pathlib import Path
from core.security_utils import secure_subprocess_run

class VoiceCloneManager:
    """Manages cloned voice generation and fallback TTS."""
    
    def __init__(self, elevenlabs_key=None, clone_voice_id=None):
        self.elevenlabs_key = elevenlabs_key
        self.clone_voice_id = clone_voice_id
        self.edge_voice = "en-US-GuyNeural"  # Documentary male tone
    
    async def generate_edge(self, script: str, output_path: str, pitch_shift: float = 0.95):
        """Free fallback using Microsoft Edge-TTS with post-processing."""
        raw = output_path.replace(".wav", "_raw.wav")
        communicate = edge_tts.Communicate(script, self.edge_voice)
        await communicate.save(raw)
        
        # Pitch shift for authority
        cmd = [
            "ffmpeg", "-y", "-i", raw,
            "-af", f"asetrate=44100*{pitch_shift},aresample=44100",
            "-ar", "44100", "-ac", "2",
            output_path
        ]
        secure_subprocess_run(cmd)
        os.remove(raw)
        
        # Add reverb
        reverb = output_path.replace(".wav", "_final.wav")
        secure_subprocess_run([
            "ffmpeg", "-y", "-i", output_path,
            "-af", "aecho=0.8:0.9:1000:0.3",
            reverb
        ])
        
        return reverb
    
    def generate_elevenlabs(self, script: str, output_path: str):
        """Use if API key and clone_voice_id are present."""
        if not self.elevenlabs_key or not self.clone_voice_id:
            return None
        
        import requests
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.clone_voice_id}"
        headers = {
            "xi-api-key": self.elevenlabs_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": script,
            "voice_settings": {
                "stability": 0.75,
                "similarity_boost": 0.85,
                "style": 0.20
            }
        }
        
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        if resp.status_code == 200:
            # SECURITY: Validate response size to prevent DoS (max 50MB for audio)
            max_size = 50 * 1024 * 1024  # 50MB
            content_size = len(resp.content)
            if content_size > max_size:
                raise RuntimeError(f"Response too large: {content_size} bytes (max {max_size})")
            
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return output_path
        return None
    
    async def generate(self, script: str, output_path: str, prefer_clone: bool = True):
        """Primary entry: tries clone, falls back to Edge-TTS."""
        if prefer_clone and self.elevenlabs_key:
            result = self.generate_elevenlabs(script, output_path)
            if result:
                return result
        
        return await self.generate_edge(script, output_path)


if __name__ == "__main__":
    print("VoiceCloneManager module loaded successfully")