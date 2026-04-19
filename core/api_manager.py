import os
import json
from pathlib import Path
from cryptography.fernet import Fernet
from dotenv import load_dotenv


class APIManager:
    """
    Manages API keys for LLM and other services.
    Supports multiple free LLM providers with automatic failover.
    """
    
    # LLM Provider configurations
    PROVIDERS = {
        "GEMINI": {
            "name": "Google Gemini",
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "models": ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-pro"],
            "default_model": "gemini-2.0-flash",
            "free": True
        },
        "GROK": {
            "name": "xAI Grok",
            "base_url": "https://api.x.ai/v1",
            "models": ["grok-2", "grok-beta"],
            "default_model": "grok-2",
            "free": True
        },
        "KIMI": {
            "name": "Moonshot Kimi",
            "base_url": "https://api.moonshot.cn/v1",
            "models": ["kimi-echo", "kimi-k2"],
            "default_model": "kimi-echo",
            "free": True
        },
        "DEEPSEEK": {
            "name": "DeepSeek",
            "base_url": "https://api.deepseek.com/v1",
            "models": ["deepseek-chat"],
            "default_model": "deepseek-chat",
            "free": True
        },
        "QIANWEN": {
            "name": "Alibaba Qwen",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "models": ["qwen-turbo", "qwen-plus", "qwen-max"],
            "default_model": "qwen-plus",
            "free": True
        },
        "PUTER": {
            "name": "Puter AI (Free Kimi K2.5)",
            "base_url": "https://api.puter.com/puterai/openai/v1/",
            "models": ["moonshotai/kimi-k2-5", "moonshotai/kimi-k2", "moonshotai/kimi-dev-72b"],
            "default_model": "moonshotai/kimi-k2-5",
            "free": True,
            "openai_compatible": True,
            "description": "Free access to Kimi K2.5 via Puter. Get auth token at puter.com/dashboard"
        }
    }
    
    def __init__(self, env_file: str = None):
        """
        Initialize APIManager.
        
        Args:
            env_file: Path to .env file (default: .env in project root)
        """
        # Initialize keys for all providers
        self.keys = {provider: None for provider in self.PROVIDERS}
        self.keys.update({
            "BRAVE_SEARCH": None,
            "ELEVENLABS": None,
            "ELEVENLABS_VOICE_ID": None,
            "YOUTUBE": None,
            "NOTION_TOKEN": None,
            "PEXELS": None,
            "UNSPLASH": None
        })
        
        # Default config
        self.config = {
            "brave_count": 10,
            "elevenlabs_voice": "Rachel"
        }
        
        # Set default models from provider configs
        for provider, cfg in self.PROVIDERS.items():
            self.config[f"{provider.lower()}_model"] = cfg["default_model"]
        
        # Load environment
        if env_file is None:
            env_file = Path(__file__).parent.parent / ".env"
        
        if Path(env_file).exists():
            load_dotenv(env_file)
        
        self.load_keys()
    
    def load_keys(self):
        """Load API keys from environment variables."""
        
        # LLM Keys - map various env var names
        self.keys["GEMINI"] = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.keys["GROK"] = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")
        self.keys["KIMI"] = os.getenv("KIMI_API_KEY") or os.getenv("MOONSHOT_API_KEY")
        self.keys["DEEPSEEK"] = os.getenv("DEEPSEEK_API_KEY")
        self.keys["QIANWEN"] = os.getenv("QIANWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        
        # Search
        self.keys["BRAVE_SEARCH"] = os.getenv("BRAVE_API_KEY")
        
        # Audio/TTS
        self.keys["ELEVENLABS"] = os.getenv("ELEVENLABS_API_KEY")
        self.keys["ELEVENLABS_VOICE_ID"] = os.getenv("ELEVENLABS_VOICE_ID")
        
        # YouTube
        self.keys["YOUTUBE"] = os.getenv("YOUTUBE_API_KEY")
        
        # Notion
        self.keys["NOTION_TOKEN"] = os.getenv("NOTION_TOKEN")
        
        # Stock media
        self.keys["PEXELS"] = os.getenv("PEXELS_API_KEY")
        self.keys["UNSPLASH"] = os.getenv("UNSPLASH_ACCESS_KEY")
        
        # Model overrides from environment
        for provider in self.PROVIDERS:
            env_model = os.getenv(f"{provider}_MODEL")
            if env_model:
                self.config[f"{provider.lower()}_model"] = env_model
            
        print("🔑 APIManager: Loaded API keys")
        self._print_available()
    
    def _print_available(self):
        """Print which APIs are available."""
        available = [k for k, v in self.keys.items() if v]
        print(f"   Available: {', '.join(available)}")
    
    def get_key(self, provider: str) -> str:
        """Get API key for a provider (NEW METHOD for Ledger)."""
        return self.keys.get(provider.upper())
    
    def get_active_brain(self) -> str:
        """
        Get the primary LLM API key (free providers preferred).
        
        Returns:
            API key string, or None if no keys available
        """
        # Priority order: Gemini > Grok > Kimi > DeepSeek > Qwen
        for provider in ["GEMINI", "GROK", "KIMI", "DEEPSEEK", "QIANWEN"]:
            if self.keys[provider]:
                return self.keys[provider]
        return None
    
    def get_brain_name(self) -> str:
        """Get name of active brain."""
        for provider in ["GEMINI", "GROK", "KIMI", "DEEPSEEK", "QIANWEN"]:
            if self.keys[provider]:
                return provider
        return "NONE"
    
    def get_provider_config(self, provider: str) -> dict:
        """
        Get configuration for a specific LLM provider.
        
        Args:
            provider: Provider name (GEMINI, GROK, KIMI, DEEPSEEK, QIANWEN)
            
        Returns:
            Dict with base_url, model, api_key
        """
        provider = provider.upper()
        if provider not in self.PROVIDERS:
            return None
            
        cfg = self.PROVIDERS[provider]
        model_key = f"{provider.lower()}_model"
        
        return {
            "provider": provider,
            "name": cfg["name"],
            "api_key": self.keys.get(provider),
            "base_url": cfg["base_url"],
            "model": self.config.get(model_key, cfg["default_model"]),
            "models": cfg["models"]
        }
    
    def get_llm_config(self) -> dict:
        """Get LLM configuration for active provider."""
        brain = self.get_brain_name()
        if brain == "NONE":
            return {"error": "No LLM API key available"}
        return self.get_provider_config(brain)
    
    def call_llm(self, provider: str, prompt: str, system_prompt: str = "") -> str:
        """
        Call an LLM provider and return the response.
        
        Args:
            provider: Provider name (GEMINI, GROK, KIMI, etc.)
            prompt: User prompt
            system_prompt: Optional system instructions
            
        Returns:
            Response text from the LLM
            
        Raises:
            RuntimeError: If API call fails or no response
        """
        import requests
        
        provider = provider.upper()
        cfg = self.get_provider_config(provider)
        
        if not cfg or not cfg.get("api_key"):
            raise RuntimeError(f"No API key configured for {provider}")
        
        api_key = cfg["api_key"]
        model = cfg["model"]
        
        try:
            # Handle different provider APIs
            if provider == "GEMINI":
                url = f"{cfg['base_url']}/models/{model}:generateContent?key={api_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}]
                }
                if system_prompt:
                    payload["system_instruction"] = {"parts": [{"text": system_prompt}]}
                
                resp = requests.post(url, json=payload, timeout=60)
                resp.raise_for_status()
                data = resp.json()
                
                if "candidates" in data and len(data["candidates"]) > 0:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                raise RuntimeError("Empty response from Gemini")
            
            elif provider in ["PUTER", "GROK", "KIMI", "DEEPSEEK", "QIANWEN"]:
                # OpenAI-compatible API
                url = f"{cfg['base_url']}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt or "You are a helpful assistant."},
                        {"role": "user", "content": prompt}
                    ]
                }
                
                resp = requests.post(url, headers=headers, json=payload, timeout=60)
                resp.raise_for_status()
                data = resp.json()
                
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]
                raise RuntimeError(f"Empty response from {provider}")
            
            else:
                raise RuntimeError(f"Unsupported provider: {provider}")
                
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"API call failed for {provider}: {e}")
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Invalid response format from {provider}: {e}")
    
    def get_all_llm_providers(self) -> list:
        """Get list of configured LLM providers."""
        configured = []
        for provider in self.PROVIDERS:
            if self.keys.get(provider):
                cfg = self.get_provider_config(provider)
                configured.append({
                    "provider": provider,
                    "name": cfg["name"],
                    "model": cfg["model"]
                })
        return configured
    
    def get_brave_config(self) -> dict:
        """Get Brave Search configuration."""
        return {
            "api_key": self.keys["BRAVE_SEARCH"],
            "count": self.config["brave_count"]
        }
    
    def get_elevenlabs_config(self) -> dict:
        """Get ElevenLabs configuration."""
        return {
            "api_key": self.keys["ELEVENLABS"],
            "voice_id": self.keys.get("ELEVENLABS_VOICE_ID") or self.config["elevenlabs_voice"]
        }
    
    def get_youtube_config(self) -> dict:
        """Get YouTube API configuration."""
        return {
            "api_key": self.keys["YOUTUBE"]
        }
    
    def has_key(self, provider: str) -> bool:
        """Check if API key exists for provider."""
        return bool(self.keys.get(provider.upper()))
    
    def is_available(self, provider: str) -> bool:
        """Check if provider is available and configured."""
        return self.has_key(provider)
    
    # === Encryption (for storing keys securely) ===
    
    @staticmethod
    def generate_key() -> bytes:
        """Generate a new encryption key."""
        return Fernet.generate_key()
    
    def encrypt_keys(self, key: bytes) -> bytes:
        """Encrypt all keys for storage."""
        f = Fernet(key)
        data = json.dumps(self.keys).encode()
        return f.encrypt(data)
    
    def decrypt_keys(self, encrypted: bytes, key: bytes) -> dict:
        """Decrypt stored keys."""
        f = Fernet(key)
        decrypted = f.decrypt(encrypted)
        return json.loads(decrypted)


# Example .env structure
ENV_EXAMPLE = """
# ===================
# LLM APIs (Free Options)
# ===================

# Google Gemini (recommended - generous free tier)
# Get from: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=

# xAI Grok (free)
# Get from: https://console.x.ai/
GROK_API_KEY=

# Moonshot Kimi (free)
# Get from: https://platform.moonshot.cn/
KIMI_API_KEY=

# DeepSeek (free)
# Get from: https://platform.deepseek.com/
DEEPSEEK_API_KEY=

# Alibaba Qwen (free)
# Get from: https://bailian.console.aliyun.com/
QIANWEN_API_KEY=

# Optional: Override default models
# GEMINI_MODEL=gemini-2.0-flash
# GROK_MODEL=grok-2
# KIMI_MODEL=kimi-echo

# ===================
# Search API (Optional)
# ===================

# Brave Search API (for ResearchAgent)
# Get from: https://brave.com/search/api/
BRAVE_API_KEY=

# ===================
# Audio/TTS APIs (Optional)
# ===================

# ElevenLabs (for voice generation)
# Get from: https://elevenlabs.io/app/settings/api
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=

# ===================
# YouTube API (Optional)
# ===================

# YouTube Data API v3
# Get from: https://console.cloud.google.com/apis/credentials
YOUTUBE_API_KEY=

# ===================
# Notion Integration (Optional)
# ===================
NOTION_TOKEN=

# ===================
# Stock Media APIs (Optional)
# ===================
PEXELS_API_KEY=
UNSPLASH_ACCESS_KEY=
"""


if __name__ == "__main__":
    # Test
    api = APIManager()
    print(f"\nActive Brain: {api.get_brain_name()}")
    print(f"LLM Config: {api.get_llm_config()}")
    print(f"\nAll configured LLMs: {api.get_all_llm_providers()}")
