#!/bin/bash
# THE LEDGER - macOS Launcher
# One-click startup with dependency checking

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Suppress zsh compinit warnings
export ZSH_DISABLE_COMPFIX=true

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "${BLUE}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    🎬  THE LEDGER                               ║"
echo "║           AI Faceless Channel Automation v3.0                   ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo "${NC}"
echo ""

# Check Python 3 (prefer system Python with tkinter)
printf "${BLUE}🔍 Checking Python 3...${NC} "

# Try system Python first (usually has tkinter)
if [ -x "/usr/bin/python3" ]; then
    PYTHON_CMD="/usr/bin/python3"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "${RED}❌ Not found${NC}"
    echo ""
    echo "${RED}Error: Python 3 is required but not installed.${NC}"
    echo "Please install Python 3 from https://python.org"
    read -p "Press Enter to exit..."
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo "${GREEN}✅ $PYTHON_VERSION${NC}"

# Check tkinter
printf "${BLUE}🔍 Checking tkinter (GUI library)...${NC} "
if ! $PYTHON_CMD -c "import tkinter" 2>/dev/null; then
    echo "${YELLOW}⚠️  tkinter not available${NC}"
    echo ""
    echo "${YELLOW}Installing python-tk...${NC}"
    
    # Try to install tkinter
    if command -v brew &> /dev/null; then
        brew install python-tk@3.11 2>/dev/null || brew install python-tk 2>/dev/null || true
    fi
    
    # Check again
    if ! $PYTHON_CMD -c "import tkinter" 2>/dev/null; then
        echo ""
        echo "${YELLOW}⚠️  tkinter not available${NC}"
        echo ""
        echo "${BLUE}🔄 Using Web GUI instead (no tkinter needed)...${NC}"
        echo ""
        
        # Install gradio if needed
        if ! $PYTHON_CMD -c "import gradio" 2>/dev/null; then
            echo "${BLUE}📦 Installing web GUI dependencies...${NC}"
            
            # Try installing with error handling
            if ! $PYTHON_CMD -m pip install gradio -q 2>/dev/null; then
                echo "${RED}❌ Failed to install gradio${NC}"
                echo ""
                echo "${YELLOW}Trying with --user flag...${NC}"
                
                if ! $PYTHON_CMD -m pip install --user gradio -q 2>/dev/null; then
                    echo "${RED}❌ Gradio installation failed${NC}"
                    echo ""
                    echo "${YELLOW}Please install manually:${NC}"
                    echo "  $PYTHON_CMD -m pip install gradio"
                    read -p "Press Enter to exit..."
                    exit 1
                fi
            fi
            
            # Verify installation
            if ! $PYTHON_CMD -c "import gradio" 2>/dev/null; then
                echo "${RED}❌ Gradio installation verification failed${NC}"
                read -p "Press Enter to exit..."
                exit 1
            fi
            
            echo "${GREEN}✅ Gradio installed${NC}"
        fi
        
        # Launch web GUI
        echo "${GREEN}🚀 Launching Web GUI...${NC}"
        echo ""
        $PYTHON_CMD web_gui.py
        exit 0
    fi
else
    echo "${GREEN}✅ OK${NC}"
fi

# Check pip
printf "${BLUE}🔍 Checking pip...${NC} "
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    echo "${RED}❌ Not found${NC}"
    echo "pip is required. Installing..."
    $PYTHON_CMD -m ensurepip --upgrade 2>/dev/null || {
        echo "${RED}Failed to install pip${NC}"
        read -p "Press Enter to exit..."
        exit 1
    }
fi
echo "${GREEN}✅ Found${NC}"

# Check if virtual environment exists
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    echo ""
    echo "${YELLOW}📦 Creating virtual environment...${NC}"
    $PYTHON_CMD -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "${RED}❌ Failed to create virtual environment${NC}"
        read -p "Press Enter to exit..."
        exit 1
    fi
    echo "${GREEN}✅ Virtual environment created${NC}"
fi

# Activate virtual environment
echo ""
echo "${BLUE}🔄 Activating virtual environment...${NC}"
source "$VENV_DIR/bin/activate"

# Check dependencies
printf "${BLUE}🔍 Checking dependencies...${NC} "
$PYTHON_CMD -c "
import sys
required = ['psutil', 'PIL', 'moviepy', 'requests', 'dotenv', 'cryptography', 'portalocker']
missing = []
for pkg in required:
    try:
        if pkg == 'PIL':
            __import__('PIL')
        else:
            __import__(pkg)
    except ImportError:
        missing.append(pkg)

if missing:
    print('MISSING:' + ','.join(missing))
    sys.exit(1)
else:
    print('OK')
    sys.exit(0)
" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "${YELLOW}⚠️  Some dependencies missing${NC}"
    echo ""
    echo "${YELLOW}📦 Installing dependencies...${NC}"
    echo "This may take a few minutes..."
    echo ""
    
    # Install with progress indication
    $PYTHON_CMD -m pip install --upgrade pip
    $PYTHON_CMD -m pip install -r requirements.txt 2>&1 | while read line; do
        if [[ $line == *"Successfully installed"* ]] || [[ $line == *"Requirement already satisfied"* ]]; then
            echo "${GREEN}✓${NC} $line"
        elif [[ $line == *"Collecting"* ]]; then
            echo "${BLUE}→${NC} $line"
        fi
    done
    
    # Check if installation succeeded
    $PYTHON_CMD -c "
import sys
try:
    import psutil, PIL, moviepy, requests, dotenv, cryptography, portalocker
    sys.exit(0)
except ImportError as e:
    print('Error:', e)
    sys.exit(1)
" 2>/dev/null
    
    if [ $? -ne 0 ]; then
        echo ""
        echo "${RED}❌ Failed to install some dependencies${NC}"
        echo "Please check the error messages above"
        read -p "Press Enter to exit..."
        exit 1
    fi
    
    echo ""
    echo "${GREEN}✅ All dependencies installed successfully${NC}"
else
    echo "${GREEN}✅ All dependencies present${NC}"
fi

# Check for API configuration
echo ""
printf "${BLUE}🔍 Checking API configuration...${NC} "
if [ ! -f ".env" ]; then
    echo "${YELLOW}⚠️  No .env file found${NC}"
    echo ""
    echo "${YELLOW}💡 Tip: You can configure APIs in the GUI${NC}"
else
    echo "${GREEN}✅ .env file found${NC}"
fi

echo ""
echo "${GREEN}🚀 All systems ready!${NC}"
echo ""
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Launch the GUI
echo "${BLUE}🎬 Launching The Ledger GUI...${NC}"
echo ""
$PYTHON_CMD app.py

# If GUI crashes, show error
if [ $? -ne 0 ]; then
    echo ""
    echo "${RED}❌ The Ledger GUI exited with an error${NC}"
    echo ""
    read -p "Press Enter to exit..."
fi

deactivate 2>/dev/null
