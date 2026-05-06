# AI Faceless Channel Automation

**The Ledger** - Financial Darkness Documentary Channel Automation v3.0 (Enterprise)

## Overview

An automated content creation pipeline for producing documentary-style YouTube videos about financial crimes, fraud cases, and corruption investigations. The system uses a multi-agent architecture to research, script, verify, produce, and publish videos while maintaining strict legal compliance.

### Target Audience

**Primary**: USA, Europe, and English-speaking audiences  
**Default Language**: English  
**Future Expansion**: Urdu-speaking markets (optional)

## Architecture

The system follows a state-driven pipeline with these stages:

```
SCOUT → SCRIBE → VERIFY → LEGAL_GATE → VOICE → ARTISAN → PUBLISH
```

### Agents

- **Scout** (`agents/scout.py`) - Researches financial crime topics from SEC EDGAR, CourtListener, and news sources
- **Scribe** (`agents/scribe.py`) - Generates original 5-act documentary scripts
- **Verifier** (`agents/verifier.py`) - Cross-references claims against court documents
- **Artisan** (`agents/artisan.py`) - Assembles final video with color grading and overlays
- **Publisher** (`agents/publisher.py`) - Uploads to YouTube with proper metadata
- **Orchestrator** (`agents/orchestrator.py`) - Coordinates the entire pipeline

### Core Infrastructure

- **Governor** (`core/governor.py`) - Hardware optimization for rendering
- **APIManager** (`core/api_manager.py`) - Manages API keys for multiple LLM providers
- **ProjectState** (`core/project_state.py`) - State machine for pipeline tracking
- **EnglishEngine** (`core/english_engine.py`) - Text rendering for English content (default)

### Supporting Modules

- **Graphics** (`graphics/`) - Thumbnails, evidence cards, document overlays
- **Voice** (`voice/`) - TTS with Edge-TTS fallback and ElevenLabs voice cloning
- **Legal** (`legal/`) - Safety checker for policy compliance
- **Integrations** (`integrations/`) - Notion sync for content calendar

## Project Structure

```
ai-faceless-channel-automation/
├── agents/
│   ├── __init__.py
│   ├── scout.py              # FinancialScout - research agent
│   ├── scribe.py             # DocumentaryScribe - script writer
│   ├── verifier.py           # LegalVerifier - fact checker
│   ├── artisan.py            # DocumentaryArtisan - video assembler
│   ├── publisher.py          # AffiliatePublisher - YouTube uploader
│   └── orchestrator.py       # LedgerOrchestrator - pipeline coordinator
├── core/
│   ├── __init__.py
│   ├── governor.py           # Hardware profiler
│   ├── api_manager.py        # API key management
│   ├── project_state.py      # State persistence
│   ├── english_engine.py     # English text renderer (default)
│   └── urdu_engine.py        # Urdu text renderer (optional, future expansion)
├── graphics/
│   ├── __init__.py
│   ├── doc_graphics.py       # Evidence card generator
│   ├── thumbnails.py         # Thumbnail factory
│   └── brand_assets.py       # Color palette, fonts
├── voice/
│   ├── __init__.py
│   └── clone_manager.py      # Voice synthesis manager
├── legal/
│   ├── __init__.py
│   └── safety_checker.py     # Policy compliance checker
├── integrations/
│   ├── __init__.py
│   └── notion_sync.py        # Content calendar sync
├── config/
│   └── documentary_prompts.json  # 5-act prompt templates
├── main.py                   # CLI entry point
├── test_mock.py             # Pipeline validation
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## Installation

```bash
# Clone the repository
git clone https://github.com/salmannasir2025/ai-faceless.git
cd ai-faceless

# Install dependencies
pip install -r requirements.txt

# Set up directories
python main.py --setup
```

## Configuration

Create a `.env` file in the project root:

```env
# LLM APIs (at least one required)
GEMINI_API_KEY=your_gemini_key
GROK_API_KEY=your_grok_key
KIMI_API_KEY=your_kimi_key
DEEPSEEK_API_KEY=your_deepseek_key
QIANWEN_API_KEY=your_qwen_key

# Voice (optional - falls back to Edge-TTS)
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=your_voice_id

# YouTube Upload (optional)
# Requires client_secrets.json from Google Cloud Console

# Affiliate Links (optional)
AFFILIATE_LEDGER=https://shop.ledger.com/?r=YOUR_CODE
AFFILIATE_BYBIT=https://www.bybit.com/invite?ref=YOUR_CODE
```

## Usage

### For Older/Legacy Macs (2012-2015 Models with OpenCore)

The GUI may crash on older systems due to tkinter/macOS compatibility. **Use CLI mode instead**:

```bash
# Easy launcher (recommended)
./run_cli.command "FTX Collapse"

# Or run directly with system Python
/usr/bin/python3 main.py "FTX Collapse" --dry-run --style documentary
```

**Tested **: Working on MacBook Pro running macOS 15.4

### Language Settings

**Default: English (en)** - For USA, Europe, and English-speaking audiences

```bash
# Create English documentary (default)
python main.py --topic "Wirecard scandal" --language en

# Future: Urdu support (for expansion to Urdu-speaking markets)
python main.py --topic "Wirecard scandal" --language ur
```

### Run Full Pipeline

```bash
# Create a documentary about a topic (English default)
python main.py --topic "Wirecard scandal" --style documentary

# With mock/test mode (no API calls)
python main.py --topic "Test case" --mock

# With specific language setting
python main.py --topic "FTX collapse" --language en --style documentary
```

### Individual Stages

```python
from agents.orchestrator import LedgerOrchestrator
from core.api_manager import APIManager
from core.governor import Governor

# Initialize
api = APIManager()
gov = Governor()
orch = LedgerOrchestrator(api, gov)

# Run pipeline
result = orch.run_pipeline(
    topic="FTX collapse",
    style="documentary",
    publish=False  # Set True for actual upload
)
```

## Legal Compliance

This system includes multiple safeguards:

1. **Legal Verifier** - Cross-references all claims against court documents
2. **Safety Checker** - Scans for policy violations before production
3. **Original Scripts** - Never copies verbatim from sources
4. **Synthetic Disclosure** - YouTube metadata labels AI-generated content
5. **Affiliate Disclosure** - End cards clearly label affiliate links

## Hardware Optimization

The Governor automatically detects hardware and optimizes:

- **Legacy Intel** (2-core): Uses VideoToolbox for Mac hardware encoding
- **Performance**: Uses CPU encoding with quality presets

## License

MIT License - See LICENSE file for details

## Disclaimer

This tool is for educational and documentary purposes. Users are responsible for:
- Ensuring content accuracy
- Complying with YouTube's Terms of Service
- Following applicable laws regarding defamation and copyright
- Properly disclosing AI-generated content and affiliate relationships
