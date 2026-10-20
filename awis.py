import sys
import platform
import subprocess

def run_stack(action):
    is_windows = platform.system() == "Windows"
    
    if action == "start":
        script = "start_awis.ps1" if is_windows else "./start_awis.sh"
    elif action == "stop":
        script = "stop_awis.ps1" if is_windows else "./stop_awis.sh"
    else:
        print(f"Unknown command: '{action}'. Please use 'start' or 'stop'.")
        sys.exit(1)

    # Route execution to the correct terminal environment
    if is_windows:
        cmd = ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", script]
    else:
        cmd = [script]

    print(f"Detected {platform.system()} - Routing to {script}...")
    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        print(f"Execution failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python awis.py [start|stop]")
        sys.exit(1)
        
    run_stack(sys.argv[1].lower())