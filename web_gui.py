#!/usr/bin/env python3
"""
THE LEDGER - Web-Based GUI
Alternative to tkinter GUI that runs in browser.
Uses Gradio for modern web interface.
"""

import os
import sys
import json
import time
import threading
import queue
from datetime import datetime
from pathlib import Path

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Check if gradio is available
try:
    import gradio as gr
except ImportError:
    print("❌ Gradio not installed. Installing...")
    os.system(f"{sys.executable} -m pip install gradio -q")
    import gradio as gr

from core.api_manager import APIManager
from core.governor import Governor
from agents.orchestrator import LedgerOrchestrator


class WebOrchestratorWrapper:
    """Wrapper to run orchestrator in background with queue updates."""
    
    def __init__(self):
        self.api = APIManager()
        self.gov = Governor()
        self.progress_queue = queue.Queue()
        self.prompt_queue = queue.Queue()
        self.pipeline_thread = None
        self.is_running = False
        self.final_result = None
        self._lock = threading.Lock()  # Thread safety for shared state
        self._pending_prompt = None   # Store pending prompt for GUI
        
    def start_pipeline(self, topic, style, language, use_failover=True):
        """Start the pipeline in background thread."""
        self.is_running = True
        self.final_result = None
        
        # Create simplified failover manager
        class SimpleFailover:
            def __init__(self, api):
                self.api = api
                self.failed = {}
                
            def get_next_provider(self):
                for p in ["GEMINI", "PUTER", "GROK", "KIMI", "DEEPSEEK"]:
                    if self.api.get_key(p) and p not in self.failed:
                        return p
                return None
                
            def mark_failed(self, provider, error):
                self.failed[provider] = time.time()
        
        failover = SimpleFailover(self.api) if use_failover else None
        
        def progress_cb(stage, status, msg=""):
            self.progress_queue.put({"type": "progress", "stage": stage, "status": status, "msg": msg})
            
        def prompt_cb(question, options):
            response_event = threading.Event()
            container = {"value": None}
            self.prompt_queue.put({"question": question, "options": options, "event": response_event, "container": container})
            response_event.wait()
            return container.get("value", options[0] if options else "yes")
        
        def run():
            try:
                orch = LedgerOrchestrator(
                    api_manager=self.api,
                    governor=self.gov,
                    progress_callback=progress_cb,
                    prompt_callback=prompt_cb,
                    failover_manager=failover
                )
                
                result = orch.run_pipeline(topic=topic, style=style, publish=False)
                self.final_result = result
                self.progress_queue.put({"type": "complete", "result": result})
            except Exception as e:
                self.progress_queue.put({"type": "error", "error": str(e)})
            finally:
                self.is_running = False
        
        self.pipeline_thread = threading.Thread(target=run, daemon=True)
        self.pipeline_thread.start()
        return "Pipeline started"
    
    def get_updates(self):
        """Get all pending updates."""
        updates = []
        try:
            while True:
                updates.append(self.progress_queue.get_nowait())
        except queue.Empty:
            pass
        return updates
    
    def check_prompts(self):
        """Check if there's a pending prompt."""
        with self._lock:
            if self._pending_prompt is not None:
                return self._pending_prompt
        
        try:
            item = self.prompt_queue.get_nowait()
            with self._lock:
                self._pending_prompt = item
            return item
        except queue.Empty:
            return None
    
    def answer_prompt(self, answer):
        """Answer a pending prompt."""
        with self._lock:
            if self._pending_prompt is not None:
                self._pending_prompt["container"]["value"] = answer
                self._pending_prompt["event"].set()
                self._pending_prompt = None
                return True
            return False
    
    def reset(self):
        """Reset wrapper state for new run."""
        with self._lock:
            self.is_running = False
            self.final_result = None
            self._pending_prompt = None
            # Clear queues
            while not self.progress_queue.empty():
                try:
                    self.progress_queue.get_nowait()
                except queue.Empty:
                    break
            while not self.prompt_queue.empty():
                try:
                    self.prompt_queue.get_nowait()
                except queue.Empty:
                    break


# Global wrapper instance with lazy initialization
_wrapper_instance = None
_wrapper_lock = threading.Lock()

def get_wrapper():
    """Get thread-safe singleton wrapper instance."""
    global _wrapper_instance
    if _wrapper_instance is None:
        with _wrapper_lock:
            if _wrapper_instance is None:
                _wrapper_instance = WebOrchestratorWrapper()
    return _wrapper_instance


def create_interface():
    """Create Gradio interface."""
    
    # Custom CSS for Kinetic Terminal theme
    custom_css = """
    .main-container {
        background: #0b0e14 !important;
        color: #ecedf6 !important;
    }
    .input-field {
        background: #10131a !important;
        border: 1px solid #161a21 !important;
        color: #ecedf6 !important;
    }
    .btn-primary {
        background: linear-gradient(135deg, #a1faff 0%, #6bff8f 100%) !important;
        color: #006165 !important;
        border: none !important;
        font-weight: bold !important;
    }
    .progress-bar {
        background: #161a21 !important;
    }
    .progress-fill {
        background: linear-gradient(90deg, #00e5ee 0%, #6bff8f 100%) !important;
    }
    h1, h2, h3 {
        color: #a1faff !important;
        font-family: 'Space Grotesk', sans-serif !important;
    }
    .gr-box {
        background: #161a21 !important;
        border: 1px solid #282c36 !important;
    }
    """
    
    with gr.Blocks(css=custom_css, title="The Ledger - Documentary Studio") as demo:
        
        gr.Markdown("""
        # 🎬 THE LEDGER
        ## AI Documentary Studio
        """)
        
        with gr.Row():
            with gr.Column(scale=2):
                # Input Section
                gr.Markdown("### Documentary Settings")
                
                topic_input = gr.Textbox(
                    label="Topic",
                    placeholder="Enter documentary topic (e.g., 'Wirecard scandal')",
                    elem_classes=["input-field"]
                )
                
                with gr.Row():
                    style_dropdown = gr.Dropdown(
                        label="Style",
                        choices=["documentary", "investigation", "breaking"],
                        value="documentary"
                    )
                    
                    language_dropdown = gr.Dropdown(
                        label="Language",
                        choices=["en (English)", "ur (Urdu - Future)"],
                        value="en (English)"
                    )
                
                # API Status
                gr.Markdown("### AI Providers")
                api_status = gr.JSON(label="Provider Status", value={})
                
                # Action Buttons
                with gr.Row():
                    start_btn = gr.Button("🎬 START DOCUMENTARY", variant="primary", elem_classes=["btn-primary"])
                    stop_btn = gr.Button("⏹ STOP", variant="secondary")
                
            with gr.Column(scale=3):
                # Progress Section
                gr.Markdown("### Progress")
                
                # Progress bars for each stage
                stages = ["scout", "scribe", "verifier", "legal", "voice", "artisan", "complete"]
                stage_labels = ["🔍 Scout", "✍️ Scribe", "🔍 Verifier", "⚖️ Legal", "🎙️ Voice", "🎬 Artisan", "✅ Complete"]
                
                progress_bars = {}
                for stage, label in zip(stages, stage_labels):
                    progress_bars[stage] = gr.Slider(
                        minimum=0, maximum=100, value=0,
                        label=label, interactive=False
                    )
                
                # Log Output
                gr.Markdown("### Activity Log")
                log_output = gr.Textbox(
                    label="",
                    lines=10,
                    interactive=False,
                    elem_classes=["input-field"]
                )
                
                # Status
                status_text = gr.Textbox(label="Status", value="Ready", interactive=False)
        
        # Hidden components for prompt dialog
        with gr.Row(visible=False) as prompt_row:
            prompt_text = gr.Textbox(label="User Input Required")
            prompt_yes = gr.Button("Yes")
            prompt_no = gr.Button("No")
        
        # Result display
        result_box = gr.JSON(label="Result", visible=False)
        
        # Timer for updates
        timer = gr.Timer(value=1.0, active=False)
        
        # State storage
        state = gr.State({"running": False, "logs": []})
        
        def start_pipeline(topic, style, language):
            if not topic.strip():
                return gr.update(value="❌ Please enter a topic"), gr.update(active=False)
            
            lang_code = language.split()[0]
            w = get_wrapper()
            w.reset()
            w.start_pipeline(topic, style, lang_code)
            
            return gr.update(value="🚀 Pipeline started..."), gr.update(active=True)
        
        def check_updates(current_state):
            """Check for updates from pipeline."""
            w = get_wrapper()
            updates = w.get_updates()
            logs = current_state.get("logs", [])
            result = current_state
            
            progress_updates = {}
            
            for update in updates:
                if update["type"] == "progress":
                    stage = update["stage"]
                    status = update["status"]
                    msg = update.get("msg", "")
                    
                    if status == "running":
                        progress_updates[stage] = 50
                    elif status == "complete":
                        progress_updates[stage] = 100
                    
                    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
                    
                elif update["type"] == "complete":
                    logs.append(f"✅ Pipeline complete!")
                    result["running"] = False
                    return (
                        gr.update(active=False),
                        "✅ Complete",
                        "\n".join(logs[-20:]),
                        {"logs": logs, "running": False},
                        update["result"]
                    )
                    
                elif update["type"] == "error":
                    logs.append(f"❌ Error: {update['error']}")
                    return (
                        gr.update(active=False),
                        f"❌ Error: {update['error']}",
                        "\n".join(logs[-20:]),
                        {"logs": logs, "running": False},
                        None
                    )
            
            # Build progress updates
            progress_values = []
            for stage in stages:
                progress_values.append(progress_updates.get(stage, 0))
            
            return (
                gr.update(active=True) if w.is_running else gr.update(active=False),
                "Running..." if w.is_running else "Ready",
                "\n".join(logs[-20:]),
                {"logs": logs, "running": w.is_running},
                None
            ) + tuple(progress_values)
        
        def stop_pipeline():
            # Note: Thread stopping is complex, this is a placeholder
            return gr.update(active=False), "Stopped"
        
        # Event handlers
        start_btn.click(
            start_pipeline,
            inputs=[topic_input, style_dropdown, language_dropdown],
            outputs=[status_text, timer]
        )
        
        stop_btn.click(stop_pipeline, outputs=[timer, status_text])
        
        timer.tick(
            check_updates,
            inputs=[state],
            outputs=[timer, status_text, log_output, state, result_box] + 
                    [progress_bars[s] for s in stages]
        )
        
        # Load initial API status
        def load_api_status():
            w = get_wrapper()
            providers = {}
            for name, config in w.api.PROVIDERS.items():
                key_exists = bool(w.api.get_key(name))
                providers[name] = {
                    "name": config["name"],
                    "configured": key_exists,
                    "status": "Ready" if key_exists else "No key"
                }
            return providers
        
        demo.load(load_api_status, outputs=api_status)
    
    return demo


def find_available_port(start_port=7860, max_port=7870):
    """Find an available port in range."""
    import socket
    for port in range(start_port, max_port + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('127.0.0.1', port))
            sock.close()
            return port
        except OSError:
            continue
    return None


def main():
    """Launch web GUI."""
    print("=" * 60)
    print("🎬 THE LEDGER - Web GUI")
    print("=" * 60)
    print()
    print("Launching web interface...")
    
    # Find available port
    port = find_available_port(7860, 7870)
    if port is None:
        print("❌ No available ports found (tried 7860-7870)")
        print("Please close other applications using these ports.")
        sys.exit(1)
    
    print(f"Using port: {port}")
    print("The browser will open automatically.")
    print()
    
    demo = create_interface()
    demo.launch(
        server_name="127.0.0.1",
        server_port=port,
        share=False,
        show_error=True,
        quiet=False
    )


if __name__ == "__main__":
    main()
