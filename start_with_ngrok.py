import os
import subprocess
import re
import time
from dotenv import set_key, dotenv_values

def find_flask_entrypoint():
    """Detects your Flask app entry point file (e.g., app.py or main.py)"""
    possible_files = ["app.py", "main.py", "wsgi.py", "run.py"]
    for file in possible_files:
        if os.path.exists(file):
            return file
    # If not found, prompt user
    return input("⚠️ Could not find Flask entry point automatically.\nPlease enter your Flask file (e.g., app.py): ").strip()

def start_ngrok_and_update_env(port=5000):
    """Start ngrok and update .env callback URL"""
    # Start ngrok tunnel
    subprocess.Popen(["ngrok", "http", str(port)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("🚀 Starting ngrok tunnel...")
    time.sleep(5)

    # Get ngrok public URL
    result = subprocess.run(["curl", "-s", "http://127.0.0.1:4040/api/tunnels"], capture_output=True, text=True)
    match = re.search(r'https://[0-9a-zA-Z\-]+\.ngrok-free\.app', result.stdout)

    if not match:
        print("❌ Could not find ngrok public URL. Check if ngrok started successfully.")
        return None

    ngrok_url = match.group(0)
    print(f"✅ Ngrok tunnel running at: {ngrok_url}")

    # Update .env
    env_path = ".env"
    if not os.path.exists(env_path):
        open(env_path, "w").close()

    set_key(env_path, "MPESA_CALLBACK_URL", f"{ngrok_url}/api/mpesa/callbacks")
    print(f"🔄 Updated MPESA_CALLBACK_URL in {env_path}")
    return ngrok_url

if __name__ == "__main__":
    flask_file = find_flask_entrypoint()
    ngrok_url = start_ngrok_and_update_env()

    if ngrok_url:
        print("🌍 Your callback URL is:", f"{ngrok_url}/api/mpesa/callbacks")
        print("💡 Flask app starting...")
        subprocess.run(["flask", "run"])
