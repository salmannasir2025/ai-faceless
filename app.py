#!/usr/bin/env python3
"""
THE LEDGER - GUI Application
Main entry point with tkinter GUI for documentary creation.
Features: topic input, API management, real-time progress, auto-failover.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import threading
import queue
import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.api_manager import APIManager
from core.governor import Governor
from core.project_state import ProjectState
from agents.orchestrator import LedgerOrchestrator


class FailoverManager:
    """Manages AI provider failover with cooldown tracking."""
    
    def __init__(self, api_manager: APIManager, max_retries: int = 3, cooldown_seconds: int = 300):
        self.api = api_manager
        self.max_retries = max_retries
        self.cooldown_seconds = cooldown_seconds
        self.failed_providers: Dict[str, Tuple[int, float]] = {}  # name -> (count, last_fail_time)
        self.current_provider: Optional[str] = None
        
    def get_available_providers(self) -> List[str]:
        """Return list of available providers not in cooldown."""
        available = []
        now = time.time()
        
        for provider in self.api.PROVIDERS.keys():
            if provider in self.failed_providers:
                fail_count, last_fail = self.failed_providers[provider]
                if fail_count >= self.max_retries:
                    # Check if cooldown expired
                    if now - last_fail > self.cooldown_seconds:
                        # Reset and make available
                        del self.failed_providers[provider]
                        available.append(provider)
                else:
                    available.append(provider)
            else:
                # Check if key exists
                if self.api.get_key(provider):
                    available.append(provider)
        
        return available
    
    def get_next_provider(self) -> Optional[str]:
        """Get next available provider for failover."""
        available = self.get_available_providers()
        if not available:
            return None
        
        # Prefer current provider if still available
        if self.current_provider and self.current_provider in available:
            return self.current_provider
        
        # Return first available
        self.current_provider = available[0]
        return self.current_provider
    
    def mark_failed(self, provider: str, error: str = ""):
        """Mark a provider as failed."""
        now = time.time()
        if provider in self.failed_providers:
            count, _ = self.failed_providers[provider]
            self.failed_providers[provider] = (count + 1, now)
        else:
            self.failed_providers[provider] = (1, now)
        
        # Switch to next provider
        self.current_provider = None
    
    def get_cooldown_remaining(self, provider: str) -> int:
        """Get remaining cooldown seconds for a provider."""
        if provider not in self.failed_providers:
            return 0
        
        fail_count, last_fail = self.failed_providers[provider]
        if fail_count < self.max_retries:
            return 0
        
        elapsed = time.time() - last_fail
        remaining = max(0, self.cooldown_seconds - elapsed)
        return int(remaining)


class PipelineThread(threading.Thread):
    """Background thread for running the pipeline."""
    
    def __init__(self, topic: str, style: str, language: str, 
                 progress_queue: queue.Queue, prompt_queue: queue.Queue,
                 api_manager: APIManager, governor: Governor,
                 failover_manager: FailoverManager):
        super().__init__()
        self.topic = topic
        self.style = style
        self.language = language
        self.progress_queue = progress_queue
        self.prompt_queue = prompt_queue
        self.api = api_manager
        self.gov = governor
        self.failover = failover_manager
        self.daemon = True
        self._stop_event = threading.Event()
        
    def stop(self):
        self._stop_event.set()
        
    def send_progress(self, stage: str, status: str, message: str = ""):
        """Send progress update to GUI."""
        if not self._stop_event.is_set():
            self.progress_queue.put(("progress", stage, status, message))
    
    def send_log(self, message: str):
        """Send log message to GUI."""
        if not self._stop_event.is_set():
            self.progress_queue.put(("log", message))
    
    def request_prompt(self, question: str, options: List[str]) -> str:
        """Request user input through GUI."""
        response_event = threading.Event()
        response_container = {"value": None}
        
        self.prompt_queue.put((question, options, response_event, response_container))
        
        # Wait for response (with timeout to check stop event)
        while not response_event.wait(0.1):
            if self._stop_event.is_set():
                return "cancel"
        
        return response_container.get("value", "cancel")
    
    def run(self):
        """Run the pipeline."""
        try:
            self.send_progress("init", "running", "Initializing pipeline...")
            self.send_log(f"🎬 Starting documentary: {self.topic}")
            self.send_log(f"📊 Style: {self.style}, Language: {self.language}")
            
            # Get initial provider
            provider = self.failover.get_next_provider()
            if not provider:
                self.send_progress("error", "failed", "No AI providers available")
                self.send_log("❌ No AI providers available. Check API configuration.")
                return
            
            self.send_log(f"🤖 Using AI provider: {self.api.PROVIDERS[provider]['name']}")
            
            # Initialize orchestrator
            self.send_progress("init", "running", "Loading orchestrator...")
            
            orchestrator = LedgerOrchestrator(
                api_manager=self.api,
                governor=self.gov,
                channel="ledger",
                progress_callback=self.send_progress,
                prompt_callback=self.request_prompt,
                failover_manager=self.failover
            )
            
            # Run pipeline
            result = orchestrator.run_pipeline(
                topic=self.topic,
                style=self.style,
                publish=False  # Always manual publish from GUI
            )
            
            if result.get("status") == "success":
                self.send_progress("complete", "success", "Documentary created!")
                self.send_log(f"✅ Success! Video saved to: {result.get('video_path', 'Unknown')}")
                self.progress_queue.put(("complete", result))
            else:
                error_msg = result.get("error", "Unknown error")
                self.send_progress("error", "failed", error_msg)
                self.send_log(f"❌ Pipeline failed: {error_msg}")
                self.progress_queue.put(("error", result))
                
        except Exception as e:
            error_msg = str(e)
            self.send_progress("error", "failed", error_msg)
            self.send_log(f"❌ Exception: {error_msg}")
            import traceback
            self.send_log(traceback.format_exc())
            self.progress_queue.put(("error", {"error": error_msg}))


class TheLedgerApp:
    """Main GUI application for The Ledger."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("🎬 The Ledger - Documentary Studio")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Initialize managers
        self.api = APIManager()
        self.gov = Governor()
        self.failover = FailoverManager(self.api)
        
        # Queues for thread communication
        self.progress_queue = queue.Queue()
        self.prompt_queue = queue.Queue()
        
        # State
        self.pipeline_thread: Optional[PipelineThread] = None
        self.is_running = False
        
        # Build UI
        self._create_ui()
        
        # Start queue checker
        self._check_queues()
        
        # Load initial provider status
        self._update_provider_status()
    
    def _create_ui(self):
        """Create the user interface."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # === HEADER ===
        header = ttk.Label(
            main_frame, 
            text="🎬 THE LEDGER",
            font=("Helvetica", 24, "bold")
        )
        header.grid(row=0, column=0, columnspan=3, pady=(0, 5))
        
        subtitle = ttk.Label(
            main_frame,
            text="AI Documentary Studio",
            font=("Helvetica", 12),
            foreground="gray"
        )
        subtitle.grid(row=1, column=0, columnspan=3, pady=(0, 20))
        
        # === INPUT SECTION ===
        input_frame = ttk.LabelFrame(main_frame, text="Documentary Settings", padding="10")
        input_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        input_frame.columnconfigure(1, weight=1)
        
        # Topic
        ttk.Label(input_frame, text="Topic:", font=("Helvetica", 11)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.topic_var = tk.StringVar()
        self.topic_entry = ttk.Entry(input_frame, textvariable=self.topic_var, font=("Helvetica", 11))
        self.topic_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Button(input_frame, text="💡 Ideas", command=self._show_topic_ideas).grid(row=0, column=2, padx=5)
        
        # Style
        ttk.Label(input_frame, text="Style:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.style_var = tk.StringVar(value="documentary")
        style_combo = ttk.Combobox(input_frame, textvariable=self.style_var, 
                                   values=["documentary", "investigation", "breaking"],
                                   state="readonly", width=15)
        style_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Language
        ttk.Label(input_frame, text="Language:").grid(row=1, column=2, sticky=tk.W, pady=5)
        self.language_var = tk.StringVar(value="en")
        lang_combo = ttk.Combobox(input_frame, textvariable=self.language_var,
                                  values=["en (English)", "ur (Urdu - Future)"],
                                  state="readonly", width=15)
        lang_combo.grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)
        
        # === API STATUS SECTION ===
        api_frame = ttk.LabelFrame(main_frame, text="AI Providers Status", padding="10")
        api_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.api_status_frame = ttk.Frame(api_frame)
        self.api_status_frame.pack(fill=tk.X, expand=True)
        
        ttk.Button(api_frame, text="⚙️ Manage APIs", 
                  command=self._open_api_manager).pack(anchor=tk.E, pady=(5, 0))
        
        # === ACTION BUTTONS ===
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=20)
        
        self.start_btn = ttk.Button(
            button_frame, 
            text="🎬 START DOCUMENTARY CREATION",
            command=self._start_pipeline,
            width=40
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(
            button_frame,
            text="⏹ STOP",
            command=self._stop_pipeline,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # === PROGRESS SECTION ===
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # Progress bars for each stage
        self.stages = [
            ("scout", "🔍 Scout", "Research"),
            ("scribe", "✍️ Scribe", "Script"),
            ("verifier", "🔍 Verifier", "Verify"),
            ("legal", "⚖️ Legal", "Safety"),
            ("voice", "🎙️ Voice", "Narration"),
            ("artisan", "🎬 Artisan", "Video"),
            ("complete", "✅ Complete", "Done")
        ]
        
        self.stage_vars = {}
        self.stage_bars = {}
        
        for i, (key, emoji, label) in enumerate(self.stages):
            frame = ttk.Frame(progress_frame)
            frame.grid(row=i, column=0, sticky=(tk.W, tk.E), pady=2)
            frame.columnconfigure(1, weight=1)
            
            ttk.Label(frame, text=f"{emoji} {label}:", width=15).grid(row=0, column=0, sticky=tk.W)
            
            var = tk.DoubleVar(value=0)
            self.stage_vars[key] = var
            
            bar = ttk.Progressbar(frame, variable=var, maximum=100, length=300, mode='determinate')
            bar.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
            self.stage_bars[key] = bar
            
            status_label = ttk.Label(frame, text="Waiting...", width=12)
            status_label.grid(row=0, column=2)
            setattr(self, f"{key}_status", status_label)
        
        # === LOG OUTPUT ===
        log_frame = ttk.LabelFrame(main_frame, text="Activity Log", padding="10")
        log_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            height=8, 
            wrap=tk.WORD,
            font=("Courier", 10)
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(log_frame, text="🗑️ Clear", command=self._clear_log).grid(row=1, column=0, sticky=tk.E, pady=(5, 0))
        
        # === STATUS BAR ===
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            main_frame, 
            textvariable=self.status_var,
            font=("Helvetica", 10),
            relief=tk.SUNKEN,
            padding=(5, 2)
        )
        status_bar.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def _update_provider_status(self):
        """Update the AI provider status display."""
        # Clear existing
        for widget in self.api_status_frame.winfo_children():
            widget.destroy()
        
        # Get available providers
        available = self.failover.get_available_providers()
        all_providers = list(self.api.PROVIDERS.keys())
        
        # Create grid
        col = 0
        for provider in all_providers:
            frame = ttk.Frame(self.api_status_frame)
            frame.grid(row=0, column=col, padx=10, pady=5)
            
            config = self.api.PROVIDERS[provider]
            name = config['name'].split()[0]  # First word only
            
            # Check status
            if provider in available:
                status_emoji = "🟢"
                status_text = "Ready"
            else:
                cooldown = self.failover.get_cooldown_remaining(provider)
                if cooldown > 0:
                    mins = cooldown // 60
                    secs = cooldown % 60
                    status_emoji = "🔴"
                    status_text = f"{mins}:{secs:02d}"
                else:
                    status_emoji = "⚪"
                    status_text = "No Key"
            
            ttk.Label(frame, text=f"{status_emoji} {name}", 
                     font=("Helvetica", 9, "bold")).pack()
            ttk.Label(frame, text=status_text, 
                     font=("Helvetica", 8), foreground="gray").pack()
            
            col += 1
        
        # Update every 5 seconds
        self.root.after(5000, self._update_provider_status)
    
    def _check_queues(self):
        """Check for messages from pipeline thread."""
        try:
            # Check progress queue
            while True:
                msg = self.progress_queue.get_nowait()
                msg_type = msg[0]
                
                if msg_type == "progress":
                    _, stage, status, message = msg
                    self._update_stage(stage, status, message)
                    
                elif msg_type == "log":
                    _, log_msg = msg[1], msg[1]
                    self._log(log_msg)
                    
                elif msg_type == "complete":
                    _, result = msg
                    self._pipeline_complete(result)
                    
                elif msg_type == "error":
                    _, error_data = msg
                    self._pipeline_error(error_data)
                    
        except queue.Empty:
            pass
        
        # Check prompt queue
        try:
            while True:
                question, options, event, container = self.prompt_queue.get_nowait()
                self._show_prompt_dialog(question, options, event, container)
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self._check_queues)
    
    def _update_stage(self, stage: str, status: str, message: str = ""):
        """Update progress for a stage."""
        if stage in self.stage_vars:
            if status == "running":
                self.stage_vars[stage].set(50)
                getattr(self, f"{stage}_status").config(text="Running...")
            elif status == "complete":
                self.stage_vars[stage].set(100)
                getattr(self, f"{stage}_status").config(text="✓ Done")
            elif status == "failed":
                self.stage_vars[stage].set(0)
                getattr(self, f"{stage}_status").config(text="✗ Failed")
        
        if message:
            self.status_var.set(message)
            self._log(message)
    
    def _log(self, message: str):
        """Add message to log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def _clear_log(self):
        """Clear the log."""
        self.log_text.delete(1.0, tk.END)
    
    def _start_pipeline(self):
        """Start the documentary creation pipeline."""
        topic = self.topic_var.get().strip()
        if not topic:
            messagebox.showerror("Error", "Please enter a topic for the documentary.")
            return
        
        # Check if any providers available
        available = self.failover.get_available_providers()
        if not available:
            messagebox.showerror("Error", "No AI providers available. Please configure APIs.")
            return
        
        # Reset progress
        for key, var in self.stage_vars.items():
            var.set(0)
            getattr(self, f"{key}_status").config(text="Waiting...")
        
        self._log(f"🎬 Starting: {topic}")
        
        # Update UI
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.is_running = True
        self.status_var.set("Running pipeline...")
        
        # Get language code
        lang = self.language_var.get().split()[0]
        
        # Start pipeline thread
        self.pipeline_thread = PipelineThread(
            topic=topic,
            style=self.style_var.get(),
            language=lang,
            progress_queue=self.progress_queue,
            prompt_queue=self.prompt_queue,
            api_manager=self.api,
            governor=self.gov,
            failover_manager=self.failover
        )
        self.pipeline_thread.start()
    
    def _stop_pipeline(self):
        """Stop the running pipeline."""
        if self.pipeline_thread and self.is_running:
            self.pipeline_thread.stop()
            self._log("⏹ Stop requested...")
            self.status_var.set("Stopping...")
    
    def _pipeline_complete(self, result: dict):
        """Handle pipeline completion."""
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("Complete!")
        
        # Show success dialog
        video_path = result.get('video_path', 'Unknown')
        
        msg = f"Documentary created successfully!\n\n"
        msg += f"Topic: {result.get('topic', 'Unknown')}\n"
        msg += f"Video: {video_path}\n\n"
        msg += "What would you like to do next?"
        
        dialog = tk.Toplevel(self.root)
        dialog.title("✅ Success!")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Documentary Complete!", 
                 font=("Helvetica", 16, "bold")).pack(pady=10)
        
        ttk.Label(dialog, text=msg, justify=tk.LEFT, wraplength=350).pack(pady=10)
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text="📁 Open Folder", 
                  command=lambda: self._open_folder(os.path.dirname(video_path))).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="🎬 New Documentary", 
                  command=lambda: [dialog.destroy(), self._reset_ui()]).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="Close", 
                  command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _pipeline_error(self, error_data: dict):
        """Handle pipeline error."""
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        error_msg = error_data.get('error', 'Unknown error')
        self.status_var.set(f"Error: {error_msg}")
        
        messagebox.showerror("Pipeline Error", 
                           f"Documentary creation failed:\n\n{error_msg}\n\nCheck the log for details.")
    
    def _show_prompt_dialog(self, question: str, options: List[str], 
                           event: threading.Event, container: dict):
        """Show interactive prompt dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("⚠️ User Input Required")
        dialog.geometry("500x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text=question, wraplength=450, 
                 font=("Helvetica", 12)).pack(pady=20)
        
        def respond(value: str):
            container["value"] = value
            event.set()
            dialog.destroy()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=20)
        
        for option in options:
            ttk.Button(btn_frame, text=option, 
                      command=lambda o=option: respond(o)).pack(side=tk.LEFT, padx=10)
    
    def _open_api_manager(self):
        """Open API management dialog."""
        dialog = APIManagerDialog(self.root, self.api, self.failover)
        self.root.wait_window(dialog)
        self._update_provider_status()
    
    def _show_topic_ideas(self):
        """Show topic ideas dialog."""
        ideas = [
            "Wirecard scandal - The billion dollar fraud",
            "FTX collapse - From crypto king to bankruptcy",
            "Theranos deception - Elizabeth Holmes trial",
            "1MDB scandal - The world's biggest financial fraud",
            "Panama Papers - Offshore tax havens exposed",
            "Archegos meltdown - The $20 billion margin call",
            "WeWork rise and fall - SoftBank's biggest mistake",
            "Luna/Terra collapse - The $40 billion crypto crash"
        ]
        
        dialog = tk.Toplevel(self.root)
        dialog.title("💡 Documentary Topic Ideas")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        
        ttk.Label(dialog, text="Select a topic:", font=("Helvetica", 12, "bold")).pack(pady=10)
        
        listbox = tk.Listbox(dialog, font=("Helvetica", 11), height=10)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        for idea in ideas:
            listbox.insert(tk.END, idea)
        
        def select():
            selection = listbox.curselection()
            if selection:
                topic = listbox.get(selection[0])
                # Extract just the topic name before the dash
                if " - " in topic:
                    topic = topic.split(" - ")[0]
                self.topic_var.set(topic)
                dialog.destroy()
        
        ttk.Button(dialog, text="Select", command=select).pack(pady=10)
    
    def _open_folder(self, path: str):
        """Open folder in file manager."""
        import subprocess
        subprocess.Popen(["open", path])
    
    def _reset_ui(self):
        """Reset UI for new documentary."""
        self.topic_var.set("")
        for key, var in self.stage_vars.items():
            var.set(0)
            getattr(self, f"{key}_status").config(text="Waiting...")
        self._clear_log()
        self.status_var.set("Ready")


class APIManagerDialog(tk.Toplevel):
    """Dialog for managing AI provider API keys."""
    
    def __init__(self, parent, api: APIManager, failover: FailoverManager):
        super().__init__(parent)
        self.title("⚙️ Manage AI Providers")
        self.geometry("600x500")
        self.transient(parent)
        self.grab_set()
        
        self.api = api
        self.failover = failover
        
        self._create_ui()
        self._load_current_values()
    
    def _create_ui(self):
        """Create dialog UI."""
        frame = ttk.Frame(self, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="API Configuration", 
                 font=("Helvetica", 16, "bold")).pack(pady=(0, 10))
        
        ttk.Label(frame, text="Enter your API keys below. Keys are stored locally in .env file.",
                 wraplength=550, foreground="gray").pack(pady=(0, 20))
        
        # Provider frame
        provider_frame = ttk.LabelFrame(frame, text="AI Providers", padding="10")
        provider_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.entries = {}
        
        row = 0
        for provider, config in self.api.PROVIDERS.items():
            ttk.Label(provider_frame, text=f"{config['name']}:",
                     font=("Helvetica", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=5)
            
            entry_frame = ttk.Frame(provider_frame)
            entry_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
            
            entry = ttk.Entry(entry_frame, width=40, show="•")
            entry.pack(side=tk.LEFT)
            self.entries[provider] = entry
            
            ttk.Button(entry_frame, text="👁", width=3,
                      command=lambda e=entry: self._toggle_visibility(e)).pack(side=tk.LEFT, padx=2)
            
            self.status_label = ttk.Label(entry_frame, text="", width=12)
            self.status_label.pack(side=tk.LEFT, padx=5)
            setattr(self, f"{provider}_status", self.status_label)
            
            row += 1
        
        # Failover settings
        settings_frame = ttk.LabelFrame(frame, text="Failover Settings", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(settings_frame, text="Max retries per provider:").grid(row=0, column=0, sticky=tk.W)
        self.max_retries_var = tk.IntVar(value=3)
        ttk.Spinbox(settings_frame, from_=1, to=5, textvariable=self.max_retries_var, 
                   width=5).grid(row=0, column=1, padx=5)
        
        ttk.Label(settings_frame, text="Cooldown (seconds):").grid(row=0, column=2, sticky=tk.W, padx=(20, 5))
        self.cooldown_var = tk.IntVar(value=300)
        ttk.Spinbox(settings_frame, from_=60, to=600, textvariable=self.cooldown_var,
                   width=5).grid(row=0, column=3, padx=5)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(btn_frame, text="💾 Save", 
                  command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="🧪 Test All", 
                  command=self._test_all).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", 
                  command=self.destroy).pack(side=tk.RIGHT, padx=5)
    
    def _load_current_values(self):
        """Load current API key values."""
        for provider, entry in self.entries.items():
            key = self.api.get_key(provider)
            if key:
                entry.insert(0, key)
                getattr(self, f"{provider}_status").config(text="✓ Set", foreground="green")
    
    def _toggle_visibility(self, entry):
        """Toggle password visibility."""
        if entry.cget("show") == "•":
            entry.config(show="")
        else:
            entry.config(show="•")
    
    def _save(self):
        """Save API keys to .env file."""
        env_path = Path(__file__).parent / ".env"
        
        lines = ["# The Ledger - API Configuration", ""]
        
        # Save all keys
        for provider, entry in self.entries.items():
            value = entry.get().strip()
            if value:
                lines.append(f"{provider}_API_KEY={value}")
            else:
                lines.append(f"# {provider}_API_KEY=")
        
        # Save failover settings
        lines.append("")
        lines.append("# Failover settings")
        lines.append(f"MAX_RETRIES={self.max_retries_var.get()}")
        lines.append(f"COOLDOWN_SECONDS={self.cooldown_var.get()}")
        
        with open(env_path, "w") as f:
            f.write("\n".join(lines))
        
        # Reload API manager
        self.api.__init__()
        self.failover.max_retries = self.max_retries_var.get()
        self.failover.cooldown_seconds = self.cooldown_var.get()
        
        messagebox.showinfo("Success", "API keys saved successfully!")
        self.destroy()
    
    def _test_all(self):
        """Test all configured APIs."""
        for provider in self.entries.keys():
            getattr(self, f"{provider}_status").config(text="⏳ Testing...", foreground="orange")
        
        self.update()
        
        for provider, entry in self.entries.items():
            key = entry.get().strip()
            if key:
                # Simple test - just check key format (full test would need API call)
                if len(key) > 10:
                    getattr(self, f"{provider}_status").config(text="✓ Valid", foreground="green")
                else:
                    getattr(self, f"{provider}_status").config(text="✗ Invalid", foreground="red")
            else:
                getattr(self, f"{provider}_status").config(text="Not set", foreground="gray")


def main():
    """Main entry point."""
    root = tk.Tk()
    
    # Set icon if available
    try:
        root.iconphoto(False, tk.PhotoImage(file="assets/icon.png"))
    except:
        pass
    
    app = TheLedgerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
