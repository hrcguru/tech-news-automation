"""
Simple scheduler to run tech news emailer daily
"""

import schedule
import time
import subprocess
from datetime import datetime

def job():
    """Run the news collection"""
    print(f"\n{'='*60}")
    print(f"🕐 Running scheduled job at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('='*60)
    
    try:
        # Run the news automation script
        result = subprocess.run(
            ['python', 'tech_news_automation.py'],
            capture_output=True,
            text=True
        )
        
        # Print output
        if result.stdout:
            print("📋 Output:", result.stdout)
        
        if result.stderr:
            print("⚠️  Errors:", result.stderr)
        
        print(f"✅ Job completed at {datetime.now().strftime('%H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ Job failed: {e}")

def main():
    """Setup and run scheduler"""
    
    print("\n" + "🚀 TECH NEWS EMAIL SCHEDULER")
    print("="*40)
    
    # Schedule the job
    schedule.every().day.at("08:00").do(job)   # Morning digest
    schedule.every().day.at("18:00").do(job)   # Evening digest
    
    print("📅 Scheduled times:")
    print("   - 08:00 AM (Morning news)")
    print("   - 06:00 PM (Evening news)")
    print("\n💡 Press Ctrl+C to stop")
    print("="*40)
    
    # Run once immediately for testing (comment this out later)
    print("\n▶️  Running initial test...")
    job()
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()