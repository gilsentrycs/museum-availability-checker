#!/usr/bin/env python3
"""
Railway.app cron service for museum checking
"""
import time
import schedule
from test_both_museums import main as check_both_museums

def job():
    print(f"🕐 Running museum check at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        check_both_museums()
    except Exception as e:
        print(f"❌ Error: {e}")
    print("✅ Check completed\n")

# Schedule every 20 minutes
schedule.every(20).minutes.do(job)

print("🚀 Museum checker started - will run every 20 minutes")
print("Press Ctrl+C to stop")

# Run once immediately
job()

# Keep the service running
while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute for scheduled jobs
