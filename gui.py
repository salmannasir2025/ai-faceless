#!/usr/bin/env python3
"""
THE LEDGER - API Configuration GUI
Simple GUI for managing API keys locally (never committed to GitHub)
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
from pathlib import Path


class LedgerConfigGUI:
    """GUI for configuring The Ledger API keys and settings."""
    
    # API Fields configuration: (label, env_var, show_char_count, required)
    API_FIELDS = [
        ("Google Gemini API Key", "GEMINI_API_KEY", 10, True),
        ("xAI Grok API Key", "GROK_API_KEY", 10, False),
        ("Moonshot Kimi API Key", "KIMI_API_KEY", 10, False),
        ("DeepSeek API Key", "DEEPSEEK_API_KEY", 10, False),
        ("Alibaba Qwen API Key", "QIANWEN_API_KEY", 10, False),
        ("Puter Auth Token (Free Kimi K2.5)", "PUTER_AUTH_TOKEN", 10, False),
        ("", "", 0, False),  # Spacer
        ("ElevenLabs API Key", "ELEVENLABS_API_KEY", 10, False),
        ("ElevenLabs Voice ID", "ELEVENLABS_VOICE_ID", 10, False),
        ("", "", 0, False),  # Spacer
        ("Brave Search API Key", "BRAVE_API_KEY", 10, False),
        ("YouTube API Key", "YOUTUBE_API_KEY", 10, False),
        ("Notion Integration Token", "NOTION_TOKEN", 10, False),
        ("Pexels API Key", "PEXELS_API_KEY", 10, False),
        ("Unsplash Access Key", "UNSPLASH_ACCESS_KEY", 10, False),
    ]
    
    # Affiliate links
    AFFILIATE_FIELDS = [
        ("Ledger Affiliate Link", "AFFILIATE_LEDGER"),
        ("Bybit Affiliate Link", "AFFILIATE_BYBIT"),
        ("Trezor Affiliate Link", "AFFILIATE_TREZOR"),
        ("NordVPN Affiliate Link", "AFFILIATE_NORDVPN"),
    ]
    
    def __init__(self, root):
        self.root = root
        self.root.title("The Ledger - API Configuration")
        self.root.geometry("700x800")
        self.root.minsize(600, 600)
        
        # Entry widgets storage
        self.entries = {}
        
        self._create_ui()
        self._load_existing_values()
    
    def _create_ui(self):
        """Create the user interface."""
        # Main container with scrollbar
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Canvas for scrolling
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=650)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Mouse wheel scrolling
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        # === HEADER ===
        header = ttk.Label(
            self.scrollable_frame, 
            text="🔐 The Ledger - API Configuration",
            font=("Helvetica", 16, "bold")
        )
        header.pack(pady=(0, 5))
        
        subheader = ttk.Label(
            self.scrollable_frame,
            text="API keys are stored locally in .env (never committed to GitHub)",
            font=("Helvetica", 10),
            foreground="gray"
        )
        subheader.pack(pady=(0, 20))
        
        # === LLM APIs SECTION ===
        self._create_section_header("🧠 LLM APIs (At least one required)")
        
        for label, env_var, show_count, required in self.API_FIELDS[:6]:
            if not label:  # Spacer
                continue
            self._create_api_field(label, env_var, show_count, required)
        
        # === VOICE APIs SECTION ===
        self._create_section_header("🔊 Voice Synthesis (Optional)")
        
        for label, env_var, show_count, required in self.API_FIELDS[6:9]:
            if not label:
                continue
            self._create_api_field(label, env_var, show_count, required)
        
        # === INTEGRATION APIs SECTION ===
        self._create_section_header("🔌 Integration APIs (Optional)")
        
        for label, env_var, show_count, required in self.API_FIELDS[9:]:
            if not label:
                continue
            self._create_api_field(label, env_var, show_count, required)
        
        # === AFFILIATE LINKS SECTION ===
        self._create_section_header("💰 Affiliate Links (Optional)")
        
        for label, env_var in self.AFFILIATE_FIELDS:
            self._create_api_field(label, env_var, 0, False, is_url=True)
        
        # === BUTTONS ===
        button_frame = ttk.Frame(self.scrollable_frame)
        button_frame.pack(fill=tk.X, pady=20)
        
        save_btn = ttk.Button(button_frame, text="💾 Save Configuration", command=self._save_config)
        save_btn.pack(side=tk.LEFT, padx=5)
        
        test_btn = ttk.Button(button_frame, text="🧪 Test APIs", command=self._test_apis)
        test_btn.pack(side=tk.LEFT, padx=5)
        
        clear_btn = ttk.Button(button_frame, text="🗑️ Clear All", command=self._clear_all)
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # === STATUS BAR ===
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            self.scrollable_frame, 
            textvariable=self.status_var,
            font=("Helvetica", 9),
            foreground="blue"
        )
        status_bar.pack(pady=(10, 0))
        
        # === HELP TEXT ===
        help_text = """
📖 Quick Help:
• At least one LLM API key is required (Gemini OR Puter recommended - both free)
• Puter Auth Token = Free access to Kimi K2.5 (1T parameter model)
  Get it at: https://puter.com/dashboard → Copy auth token
• ElevenLabs voice cloning is optional (falls back to Edge-TTS)
• YouTube upload requires client_secrets.json from Google Cloud Console
• Affiliate links are injected into video end cards
• All keys are stored in .env file (excluded from Git via .gitignore)

🔒 Security: This file saves API keys locally only. Never share .env files.

🚀 Pro Tip: Puter provides FREE unlimited access to Kimi K2.5!
   No credit card required. Just sign up at puter.com
        """
        help_label = ttk.Label(
            self.scrollable_frame,
            text=help_text,
            font=("Helvetica", 9),
            foreground="gray",
            justify=tk.LEFT
        )
        help_label.pack(pady=(20, 0), anchor="w")
    
    def _create_section_header(self, text):
        """Create a section header."""
        header = ttk.Label(
            self.scrollable_frame,
            text=text,
            font=("Helvetica", 12, "bold")
        )
        header.pack(anchor="w", pady=(20, 10))
        
        separator = ttk.Separator(self.scrollable_frame, orient="horizontal")
        separator.pack(fill=tk.X, pady=(0, 10))
    
    def _create_api_field(self, label, env_var, show_count, required, is_url=False):
        """Create a labeled entry field for API key."""
        frame = ttk.Frame(self.scrollable_frame)
        frame.pack(fill=tk.X, pady=5)
        
        # Label
        label_text = label
        if required:
            label_text += " *"
        
        lbl = ttk.Label(frame, text=label_text, font=("Helvetica", 10))
        lbl.pack(anchor="w")
        
        # Entry field
        entry = ttk.Entry(frame, width=60, show="" if is_url else "•")
        entry.pack(fill=tk.X, pady=(2, 0))
        
        # Show/Hide button for non-URL fields
        if not is_url and show_count > 0:
            btn_frame = ttk.Frame(frame)
            btn_frame.pack(anchor="w", pady=(2, 0))
            
            show_btn = ttk.Button(
                btn_frame, 
                text="👁 Show",
                width=8,
                command=lambda e=entry, b=show_btn: self._toggle_visibility(e, b)
            )
            show_btn.pack(side=tk.LEFT)
        
        # Store reference
        self.entries[env_var] = entry
    
    def _toggle_visibility(self, entry, button):
        """Toggle password visibility."""
        if entry.cget("show") == "•":
            entry.config(show="")
            button.config(text="🙈 Hide")
        else:
            entry.config(show="•")
            button.config(text="👁 Show")
    
    def _load_existing_values(self):
        """Load existing values from .env file."""
        env_path = Path(__file__).parent / ".env"
        
        if not env_path.exists():
            return
        
        try:
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        
                        if key in self.entries:
                            self.entries[key].insert(0, value)
            
            self.status_var.set(f"Loaded existing configuration from {env_path}")
        except Exception as e:
            self.status_var.set(f"Warning: Could not load .env: {e}")
    
    def _save_config(self):
        """Save configuration to .env file."""
        env_path = Path(__file__).parent / ".env"
        
        try:
            lines = ["# The Ledger - API Configuration", "# Generated by gui.py", ""]
            
            # LLM APIs section
            lines.extend([
                "# ===================",
                "# LLM APIs (Free Options - at least one required)",
                "# ===================",
                ""
            ])
            
            for label, env_var, _, _ in self.API_FIELDS[:6]:
                if env_var:
                    value = self.entries[env_var].get().strip()
                    if value:
                        lines.append(f"{env_var}={value}")
                    else:
                        lines.append(f"# {env_var}=")
            
            # Voice section
            lines.extend([
                "",
                "# ===================",
                "# Voice Synthesis (Optional)",
                "# ===================",
                ""
            ])
            
            for label, env_var, _, _ in self.API_FIELDS[6:9]:
                if env_var:
                    value = self.entries[env_var].get().strip()
                    if value:
                        lines.append(f"{env_var}={value}")
                    else:
                        lines.append(f"# {env_var}=")
            
            # Integrations section
            lines.extend([
                "",
                "# ===================",
                "# Integration APIs (Optional)",
                "# ===================",
                ""
            ])
            
            for label, env_var, _, _ in self.API_FIELDS[9:]:
                if env_var:
                    value = self.entries[env_var].get().strip()
                    if value:
                        lines.append(f"{env_var}={value}")
                    else:
                        lines.append(f"# {env_var}=")
            
            # Affiliate links section
            lines.extend([
                "",
                "# ===================",
                "# Affiliate Links (Optional)",
                "# ===================",
                ""
            ])
            
            for label, env_var in self.AFFILIATE_FIELDS:
                value = self.entries[env_var].get().strip()
                if value:
                    lines.append(f"{env_var}={value}")
                else:
                    lines.append(f"# {env_var}=")
            
            # Write file
            with open(env_path, "w") as f:
                f.write("\n".join(lines))
            
            self.status_var.set(f"✅ Configuration saved to {env_path}")
            messagebox.showinfo("Success", f"Configuration saved to:\n{env_path}")
            
        except Exception as e:
            self.status_var.set(f"❌ Error saving: {e}")
            messagebox.showerror("Error", f"Failed to save configuration:\n{e}")
    
    def _test_apis(self):
        """Test API connectivity."""
        self.status_var.set("Testing APIs...")
        
        # Simple validation - check if at least one LLM key is present
        has_llm = any(
            self.entries[env_var].get().strip()
            for label, env_var, _, _ in self.API_FIELDS[:6]
            if env_var
        )
        
        if not has_llm:
            messagebox.showwarning(
                "Validation Warning",
                "No LLM API key configured.\n\nAt least one LLM API is required to run the pipeline."
            )
            self.status_var.set("⚠️ No LLM API key found")
        else:
            messagebox.showinfo(
                "Validation OK",
                "✅ At least one LLM API key is configured.\n\nFull API testing will happen when you run the pipeline."
            )
            self.status_var.set("✅ Basic validation passed")
    
    def _clear_all(self):
        """Clear all fields."""
        if messagebox.askyesno("Confirm", "Clear all API keys? This cannot be undone."):
            for entry in self.entries.values():
                entry.delete(0, tk.END)
            self.status_var.set("All fields cleared")


def main():
    """Run the GUI."""
    root = tk.Tk()
    app = LedgerConfigGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
