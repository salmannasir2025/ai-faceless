#!/usr/bin/env python3
"""
THE LEDGER — Integrated Entry Point
Financial Darkness Documentary Channel Automation v3.0
"""

import os
import sys
import json  # SECURITY FIX: Added missing json import
import argparse
import asyncio
from datetime import datetime

# Core infrastructure
from core.governor import Governor
from core.api_manager import APIManager
from core.project_state import ProjectState

# Agent pipeline
from agents.orchestrator import LedgerOrchestrator

# Utilities
from legal.safety_checker import LegalSafetyChecker
from core.security_utils import validate_topic, validate_enum, sanitize_path, InputValidationError


def setup_directories():
    """Ensure required folder structure exists."""
    dirs = [
        "output/videos", "output/audio", "output/thumbnails",
        "assets/host", "assets/objects", "assets/broll",
        "states", "logs", "config"
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def validate_environment():
    """Check for required files before starting."""
    required = []
    
    if not os.path.exists("client_secrets.json"):
        print("⚠️  Warning: client_secrets.json not found. YouTube upload will fail.")
        print("   Download from Google Cloud Console → APIs & Services → Credentials")
    
    if not os.path.exists(".env") and not os.path.exists(".env.example"):
        print("⚠️  Warning: No .env file found. API keys may be missing.")
    
    missing_dirs = [d for d in ["assets/host", "config"] if not os.path.exists(d)]
    if missing_dirs:
        print(f"⚠️  Creating missing directories: {missing_dirs}")
        setup_directories()


def parse_arguments():
    """CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="The Ledger — Financial Documentary Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "FTX collapse" --channel ledger --voice clone --publish
  python main.py "Bitcoin Fed reaction" --channel signal --voice edge_tts
  python main.py "Wirecard scandal" --channel ledger --no-affiliate --dry-run
        """
    )
    
    parser.add_argument("topic", help="Documentary topic or news headline")
    
    parser.add_argument(
        "--channel", choices=["ledger", "signal"], default="ledger",
        help="Channel target: ledger (documentary) or signal (shorts)"
    )
    
    parser.add_argument(
        "--voice", choices=["clone", "edge_tts", "pre_recorded"], default="clone",
        help="Voice generation method"
    )
    
    parser.add_argument(
        "--audio-path", default=None,
        help="Path to pre-recorded audio (for pre_recorded voice mode)"
    )
    
    parser.add_argument(
        "--publish", action="store_true",
        help="Upload to YouTube as PRIVATE after production"
    )
    
    parser.add_argument(
        "--no-affiliate", action="store_true",
        help="Disable affiliate link injection"
    )
    
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run pipeline without external API calls (testing mode)"
    )
    
    parser.add_argument(
        "--style", choices=["documentary", "news", "breaking"], default="documentary",
        help="Script style tone"
    )
    
    parser.add_argument(
        "--language", choices=["en", "ur"], default="en",
        help="Video language: en (English, default) or ur (Urdu). Channel targets USA/Europe English speakers by default."
    )
    
    return parser.parse_args()


def print_banner():
    print("=" * 70)
    print("   🎬  THE LEDGER")
    print("   🤖  AI Faceless Channel Automation v3.0")
    print("=" * 70)
    print()


def print_config(args):
    lang_display = f"{args.language.upper()} (English)" if args.language == "en" else f"{args.language.upper()} (Urdu)"
    print("CONFIGURATION:")
    print(f"  Topic:      {args.topic}")
    print(f"  Channel:    {args.channel}")
    print(f"  Style:      {args.style}")
    print(f"  Language:   {lang_display}")
    print(f"  Voice:      {args.voice}")
    print(f"  Affiliate:  {'Disabled' if args.no_affiliate else 'Enabled'}")
    print(f"  Publish:    {'Yes (PRIVATE)' if args.publish else 'No'}")
    print(f"  Dry Run:    {'Yes' if args.dry_run else 'No'}")
    print("-" * 70)


def main():
    print_banner()
    validate_environment()
    
    args = parse_arguments()
    
    # SECURITY: Validate user inputs
    try:
        # Validate topic
        if args.topic:
            args.topic = validate_topic(args.topic)
        
        # Validate enum values
        args.style = validate_enum(args.style, ["documentary", "news", "breaking"])
        args.language = validate_enum(args.language, ["en", "ur"])
        args.channel = validate_enum(args.channel, ["ledger", "signal"])
        args.voice = validate_enum(args.voice, ["edge_tts", "elevenlabs", "pre_recorded"])
        
        # Validate audio path if provided
        if args.audio_path:
            args.audio_path = sanitize_path(args.audio_path)
            
    except InputValidationError as e:
        print(f"❌ Input validation failed: {e}")
        sys.exit(1)
    
    print_config(args)
    
    # Initialize core systems
    print("\n🔧 Initializing systems...")
    try:
        gov = Governor()
        api = APIManager()
        
        # Dry run flag passed to orchestrator
        orchestrator = LedgerOrchestrator(
            api_manager=api,
            governor=gov,
            channel=args.channel,
            dry_run=args.dry_run
        )
        
        # Override settings from CLI
        orchestrator.project_state.set_metadata("voice_source", args.voice)
        orchestrator.project_state.set_metadata("affiliate_inject", not args.no_affiliate)
        orchestrator.project_state.set_metadata("language", args.language)
        
        if args.voice == "pre_recorded" and args.audio_path:
            if not os.path.exists(args.audio_path):
                print(f"❌ Error: Audio file not found: {args.audio_path}")
                sys.exit(1)
            orchestrator.project_state.set_metadata("pre_recorded_audio_path", args.audio_path)
        print("✅ Systems ready\n")
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        sys.exit(1)
    
    # Execute pipeline
    print("🚀 LAUNCHING PIPELINE\n")
    start_time = datetime.now()
    
    try:
        result = orchestrator.run_pipeline(
            topic=args.topic,
            style=args.style,
            publish=args.publish
        )
        
        # Results display
        elapsed = (datetime.now() - start_time).total_seconds()
        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)
        
        if result.get("status") == "success":
            print(f"✅ Status:      SUCCESS")
            print(f"📁 Project:     {result.get('project_id')}")
            print(f"⏱️  Duration:    {elapsed:.1f}s")
            
            if result.get('video_path'):
                print(f"🎥 Video:       {result['video_path']}")
            
            if result.get('youtube_url'):
                print(f"📺 YouTube:     {result['youtube_url']} (PRIVATE)")
                print(f"🔧 Studio:      {result.get('studio_link', 'N/A')}")
                print("\n⚠️  ACTION REQUIRED:")
                print("   1. Review video in YouTube Studio")
                print("   2. Set 'Altered or synthetic content' = Yes")
                print("   3. Verify end-screen and cards")
                print("   4. Change privacy to PUBLIC when ready")
            
            # Show affiliate earnings potential
            if not args.no_affiliate:
                print("\n💰 Affiliate links injected:")
                print("   • Ledger (hardware wallet)")
                print("   • Bybit (exchange)")
                print("   • NordVPN (privacy)")
            
        elif result.get("status") == "failed":
            print(f"❌ Status:      FAILED")
            print(f"💥 Reason:      {result.get('error', 'Unknown error')}")
            print(f"📍 Stage:       {result.get('full_state', {}).get('stage', 'unknown')}")
            
            # Show where it died
            state = result.get('full_state', {})
            for agent_name, agent_data in state.get('agents', {}).items():
                if agent_data.get('status') == 'failed':
                    print(f"   Failed at:   {agent_name}")
        
        # Save final report
        report_path = f"logs/run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs("logs", exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n📝 Full report:  {report_path}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Unhandled exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()