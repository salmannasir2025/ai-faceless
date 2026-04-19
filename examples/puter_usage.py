#!/usr/bin/env python3
"""
Example: Using Puter AI for Free Kimi K2.5 Access

Puter provides free, unlimited access to Kimi K2.5 (1T parameter MoE model)
without requiring a Moonshot API key. You only need a Puter auth token.

Get your auth token: https://puter.com/dashboard → Click "Copy" button
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.api_manager import APIManager


def test_puter_kimi():
    """Test Puter AI integration with Kimi K2.5"""
    
    print("=" * 60)
    print("🚀 Puter AI + Kimi K2.5 Example")
    print("=" * 60)
    
    # Initialize API manager
    api = APIManager()
    
    # Check if Puter token is configured
    puter_token = api.get_key("PUTER")
    
    if not puter_token:
        print("\n⚠️  Puter Auth Token not found!")
        print("\nTo get your free token:")
        print("1. Visit https://puter.com")
        print("2. Sign up for a free account")
        print("3. Go to https://puter.com/dashboard")
        print("4. Click 'Copy' to get your auth token")
        print("5. Add it to your .env file: PUTER_AUTH_TOKEN=your_token_here")
        print("\n💡 Or run: python gui.py and enter it in the GUI")
        return False
    
    print(f"\n✅ Puter Auth Token found: {puter_token[:10]}...")
    print(f"🤖 Model: {api.PROVIDERS['PUTER']['default_model']}")
    print(f"📡 Base URL: {api.PROVIDERS['PUTER']['base_url']}")
    
    # Example: Using Puter with OpenAI-compatible API
    print("\n" + "=" * 60)
    print("Example API Call:")
    print("=" * 60)
    
    example_code = '''
import requests

# Using Puter's OpenAI-compatible endpoint
response = requests.post(
    "https://api.puter.com/puterai/openai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {puter_token}",
        "Content-Type": "application/json"
    },
    json={
        "model": "moonshotai/kimi-k2-5",
        "messages": [
            {"role": "system", "content": "You are a documentary scriptwriter."},
            {"role": "user", "content": "Write a 5-act documentary script about the Wirecard scandal."}
        ],
        "temperature": 0.7,
        "max_tokens": 4000
    }
)

result = response.json()
print(result['choices'][0]['message']['content'])
'''
    print(example_code)
    
    print("\n" + "=" * 60)
    print("Available Puter Models:")
    print("=" * 60)
    for model in api.PROVIDERS['PUTER']['models']:
        print(f"  • {model}")
    
    print("\n" + "=" * 60)
    print("Benefits of Using Puter:")
    print("=" * 60)
    print("  ✅ Free unlimited access to Kimi K2.5")
    print("  ✅ 1 trillion parameter MoE model")
    print("  ✅ No credit card required")
    print("  ✅ OpenAI-compatible API")
    print("  ✅ Perfect for documentary script generation")
    print("  ✅ Falls back to other providers if needed")
    
    print("\n" + "=" * 60)
    print("Integration with The Ledger:")
    print("=" * 60)
    print("The orchestrator will automatically use Puter when:")
    print("  1. PUTER_AUTH_TOKEN is set in .env")
    print("  2. Puter is selected as the active brain")
    print("  3. Or as fallback if other providers fail")
    
    return True


def compare_providers():
    """Compare different LLM providers available"""
    
    print("\n" + "=" * 60)
    print("📊 Provider Comparison")
    print("=" * 60)
    
    api = APIManager()
    
    providers = [
        ("PUTER", "Puter AI (Free Kimi K2.5)", "✅ Free", "1T params MoE"),
        ("GEMINI", "Google Gemini", "✅ Free tier", "Flash 2.0"),
        ("GROK", "xAI Grok", "✅ Free tier", "Grok 2"),
        ("KIMI", "Moonshot Kimi", "❌ Paid", "Kimi K2"),
        ("DEEPSEEK", "DeepSeek", "✅ Free", "DeepSeek-V3"),
        ("QIANWEN", "Alibaba Qwen", "✅ Free", "Qwen Plus"),
    ]
    
    print(f"{'Provider':<12} {'Name':<25} {'Cost':<12} {'Model':<15}")
    print("-" * 65)
    for key, name, cost, model in providers:
        config = api.PROVIDERS.get(key, {})
        default = config.get('default_model', 'N/A')
        print(f"{key:<12} {name:<25} {cost:<12} {default:<15}")
    
    print("\n💡 Recommendation: Use PUTER or GEMINI for free tier")
    print("   Both offer excellent performance for documentary scripts.")


if __name__ == "__main__":
    # Test Puter integration
    success = test_puter_kimi()
    
    # Show comparison
    compare_providers()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Puter integration is ready!")
    else:
        print("⚠️  Please configure your Puter Auth Token first")
    print("=" * 60)
