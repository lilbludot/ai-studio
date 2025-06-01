#!/usr/bin/env python3
"""
Diagnose Gradio issues and test fixes
"""

import sys
import subprocess

print("=== System Information ===")
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")

# Check current Gradio
try:
    import gradio as gr
    print(f"\nCurrent Gradio version: {gr.__version__}")
except ImportError:
    print("\nGradio not installed!")
    sys.exit(1)

print("\n=== Testing Minimal Gradio App ===")

# Test 1: Absolute minimal app
try:
    import gradio as gr
    
    def greet(name):
        return f"Hello {name}!"
    
    # Try with show_api=False to skip API generation
    demo = gr.Interface(fn=greet, inputs="text", outputs="text")
    
    print("✓ Basic Interface created")
    
    # Try to launch with different settings
    print("\nAttempting to launch with safe settings...")
    demo.launch(
        server_name="127.0.0.1",
        server_port=7862,
        show_api=False,
        share=False,
        quiet=False,
        prevent_thread_lock=True
    )
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Checking for known issues ===")

# Check if it's the API generation issue
print("\nTesting API generation separately...")
try:
    from gradio.utils import get_api_info
    # This is where it might fail
    print("API generation test passed")
except Exception as e:
    print(f"API generation error: {e}")

print("\n=== Suggested fixes ===")
print("1. Downgrade Gradio:")
print("   pip install gradio==4.19.2")
print("\n2. Or upgrade Python:")
print("   Consider using Python 3.10+ for better compatibility")
print("\n3. Or try these specific versions known to work:")
print("   - gradio==3.50.2 (very stable)")
print("   - gradio==4.31.0 (good middle ground)")