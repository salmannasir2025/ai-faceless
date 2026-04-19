import platform
import psutil
import os

class Governor:
    def __init__(self):
        self.os_type = platform.system()
        self.cpu_count = psutil.cpu_count(logical=False)
        self.ram_gb = psutil.virtual_memory().total / (1024**3)
        self.profile = self._determine_profile()

    def _determine_profile(self):
        if self.cpu_count <= 2:
            return "LEGACY_INTEL"
        return "PERFORMANCE"

    def get_ffmpeg_params(self):
        if self.os_type == "Darwin" and self.profile == "LEGACY_INTEL":
            # Optimized for your MacBook Pro 9,2
            return ["-c:v", "h264_videotoolbox", "-b:v", "2000k", "-preset", "fast"]
        return ["-c:v", "libx264", "-preset", "ultrafast"]

# Usage for your software
governor = Governor()
print(f"Active Profile: {governor.profile}")