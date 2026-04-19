# GUI Setup Guide for macOS

## Problem: tkinter Not Found

Your Python installation doesn't include tkinter (the GUI library). Here are 3 solutions:

---

## Solution 1: Install Python with tkinter (Recommended)

```bash
# Install python-tk (Homebrew)
brew install python-tk@3.11

# Or use system Python which has tkinter built-in
/usr/bin/python3 --version
```

Then modify `start.command` to use system Python:
```bash
# Change this line in start.command:
python3 main.py

# To:
/usr/bin/python3 main.py
```

---

## Solution 2: Use Virtual Environment with System Python

```bash
# Use system Python (usually has tkinter)
cd ai-faceless-channel-automation
/usr/bin/python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

---

## Solution 3: Web-Based GUI (No tkinter needed)

If tkinter continues to be problematic, we can build a web-based GUI using Flask or Gradio:

```bash
pip install gradio
```

Then launch web GUI:
```bash
python web_gui.py  # Opens in browser
```

**Advantages:**
- No tkinter dependency
- Runs in any browser
- More modern UI
- Easier to style (follows Kinetic Terminal design perfectly)

---

## Quick Check

Test if tkinter is available:
```bash
python3 -c "import tkinter; print('tkinter OK')"
```

If it fails, use one of the solutions above.

---

## Alternative: Use CLI Instead

While GUI is being fixed, the CLI still works perfectly:

```bash
# Install deps
pip install -r requirements.txt

# Run with CLI
python main.py --topic "Wirecard scandal" --mock
```
