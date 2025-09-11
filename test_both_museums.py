#!/usr/bin/env python3
"""
Quick test script to check both museums for October 7th availability
"""

import os
import subprocess
import sys

# URLs for both museums
CHICHU_URL = "https://benesse-artsite.eventos.tokyo/web/portal/797/event/8483/module/booth/239565/176695?language=eng"
TESHIMA_URL = "https://benesse-artsite.eventos.tokyo/web/portal/797/event/8483/module/booth/239565/185773?language=eng"

def check_museum(name, url, date):
    """Check availability for one museum"""
    print(f"\n=== Checking {name} ===")
    print(f"URL: {url}")
    print(f"Date: {date}")
    
    # Set environment variable and run the original script
    env = os.environ.copy()
    env["TARGET_URL"] = url
    env["HEADLESS"] = "1"  # Run in headless mode for automation
    
    try:
        result = subprocess.run([
            sys.executable, "chichu_availability_checker.py", 
            "--dates", date
        ], env=env, capture_output=True, text=True, timeout=120)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Timeout - script took too long")
        return False
    except Exception as e:
        print(f"❌ Error running script: {e}")
        return False

def main():
    date = "2025-10-07"
    
    print("🔍 Museum Availability Checker")
    print(f"Checking both museums for {date}")
    
    # Check both museums
    success1 = check_museum("Chichu Art Museum", CHICHU_URL, date)
    success2 = check_museum("Teshima Art Museum", TESHIMA_URL, date)
    
    print(f"\n=== SUMMARY ===")
    print(f"Chichu Art Museum: {'✅ Success' if success1 else '❌ Failed'}")
    print(f"Teshima Art Museum: {'✅ Success' if success2 else '❌ Failed'}")

if __name__ == "__main__":
    main()
