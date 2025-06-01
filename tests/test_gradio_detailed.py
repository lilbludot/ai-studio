#!/usr/bin/env python3
"""
Detailed Gradio diagnostic to find the exact issue
"""

import sys
import time
import threading
import requests

print("=== Gradio Detailed Diagnostic ===")
print(f"Python: {sys.version.split()[0]}")

try:
    import gradio as gr
    print(f"Gradio: {gr.__version__}")
except ImportError:
    print("Gradio not installed!")
    sys.exit(1)

print("\n=== Test 1: Simple blocking launch ===")
def greet(name):
    return f"Hello {name}!"

try:
    demo = gr.Interface(fn=greet, inputs="text", outputs="text")
    
    # First, let's try to see what happens with a simple launch
    print("Launching Gradio (press Ctrl+C after testing)...")
    
    # Use a thread to test the server after launch
    def test_server():
        time.sleep(3)  # Wait for server to start
        print("\n=== Testing server accessibility ===")
        
        try:
            response = requests.get("http://127.0.0.1:7860", timeout=5)
            print(f"✓ Server responded with status: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("❌ Connection refused - server not actually running")
        except requests.exceptions.Timeout:
            print("❌ Connection timeout - server not responding")
        except Exception as e:
            print(f"❌ Error accessing server: {e}")
    
    # Start the test in a separate thread
    test_thread = threading.Thread(target=test_server)
    test_thread.daemon = True
    test_thread.start()
    
    # Try launch with explicit settings
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        show_api=False,
        show_error=True,
        quiet=False
    )
    
except KeyboardInterrupt:
    print("\n\nStopped by user")
except Exception as e:
    print(f"\n❌ Launch error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Test 2: Check for port conflicts ===")
import socket

def check_port(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0

for port in [7860, 7861, 7862]:
    if check_port(port):
        print(f"Port {port}: IN USE")
    else:
        print(f"Port {port}: AVAILABLE")

print("\n=== Test 3: Try older Gradio syntax ===")
try:
    import gradio as gr
    
    # Some versions of Gradio have different internal server handling
    iface = gr.Interface(lambda x: f"Test: {x}", "text", "text")
    
    # Get the underlying app
    app = iface.app
    print(f"Underlying app type: {type(app)}")
    
except Exception as e:
    print(f"Could not test app internals: {e}")

print("\n=== RECOMMENDATION ===")
print("Based on the errors, let's downgrade Gradio:")
print("\n1. First, uninstall current version:")
print("   pip uninstall gradio -y")
print("\n2. Install a stable version:")
print("   pip install gradio==4.19.2")
print("\n3. If that doesn't work, try:")
print("   pip install gradio==3.50.2")