import subprocess
import sys
import time

# Define the full suite of AWIS MCP microservices
SERVERS = [
    {"name": "researcher_server",   "module": "src.mcp_servers.researcher_server",   "port": 8001},
    {"name": "academic_server",     "module": "src.mcp_servers.academic_server",     "port": 8002},
    {"name": "dev_server",          "module": "src.mcp_servers.dev_server",          "port": 8003},
    {"name": "media_social_server", "module": "src.mcp_servers.media_social_server", "port": 8004},
    {"name": "extractor_server",    "module": "src.mcp_servers.extractor_server",    "port": 8005},
]

def main():
    processes = []
    print("=========================================")
    print("Starting AWIS MCP Microservices Suite")
    print("=========================================")
    
    try:
        # Boot each server as a subprocess
        for server in SERVERS:
            print(f"Booting {server['name']} on http://localhost:{server['port']}/sse ...")
            p = subprocess.Popen([sys.executable, "-m", server["module"]])
            processes.append((server["name"], p))
            time.sleep(0.5) # Slight stagger to prevent log overlap
        
        print("\n✅ All 5 MCP servers launched successfully!")
        print("Press Ctrl+C to shut down all servers gracefully.\n")
        
        # Keep the main process alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Received shutdown signal. Terminating MCP servers...")
        for name, p in processes:
            print(f"Terminating {name}...")
            p.terminate()
        
        # Wait for all processes to finish closing ports
        for name, p in processes:
            p.wait()
        
        print("✅ All servers shut down cleanly.")

if __name__ == "__main__":
    main()