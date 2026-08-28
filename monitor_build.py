import time
import os
import sys
import re

# Define build milestones in order
MILESTONES = [
    ("Preparing build", 10),
    ("Install platform", 20),
    ("Downloading python-for-android", 30),
    ("Building Python", 40),
    ("Building Kivy", 60),
    ("Packaging APK", 80),
    ("Build finished", 100),
    ("APK created", 100)
]

def print_progress(percentage, status):
    width = 40
    filled = int(width * percentage / 100)
    bar = "█" * filled + "-" * (width - filled)
    sys.stdout.write(f"\rProgress: |{bar}| {percentage}% - {status}")
    sys.stdout.flush()

def monitor():
    log_file = "/root/agent/.buildozer/android/platform/build-debug/build.log" # Adjust path dynamically if needed
    # Fallback: look for any build.log in .buildozer
    if not os.path.exists(log_file):
        # Try to find the actual log path
        import glob
        logs = glob.glob("/root/agent/.buildozer/android/platform/build-*/build.log")
        if logs:
            log_file = logs[0]
        else:
            print("Waiting for log file to be created...")
            while not logs:
                time.sleep(2)
                logs = glob.glob("/root/agent/.buildozer/android/platform/build-*/build.log")
            log_file = logs[0]

    print(f"Monitoring log: {log_file}")
    current_milestone_idx = 0
    
    with open(log_file, "r") as f:
        # Go to end of file
        f.seek(0, os.SEEK_END)
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(1)
                continue
            
            for text, percent in MILESTONES:
                if text in line:
                    print_progress(percent, text)
                    break
            
            if "Buildozer failed" in line or "Error" in line.upper():
                print("\n\n[!] Build Error detected in logs!")
                sys.exit(1)
            
            if "APK created" in line or "build finished" in line.lower():
                print_progress(100, "Complete!")
                print("\n\n✅ Build Finished Successfully!")
                sys.exit(0)

if __name__ == "__main__":
    try:
        monitor()
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
