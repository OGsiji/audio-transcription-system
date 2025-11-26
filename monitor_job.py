#!/usr/bin/env python3
"""
Simple job monitoring script
Usage: python monitor_job.py <job_id>
"""

import requests
import time
import sys

if len(sys.argv) < 2:
    print("Usage: python monitor_job.py <job_id>")
    print("\nExample:")
    print("  python monitor_job.py 25f05151-82ec-4153-9519-b9bde41350af")
    sys.exit(1)

job_id = sys.argv[1]
base_url = "http://localhost:8000"

print(f"🔍 Monitoring job: {job_id}")
print("Press Ctrl+C to stop\n")

last_processed = 0

while True:
    try:
        response = requests.get(f"{base_url}/transcribe/{job_id}")
        data = response.json()

        status = data.get("status", "unknown")
        total = data.get("total_files") or 0
        processed = data.get("processed_files") or 0

        # Show progress
        if total > 0:
            progress = (processed / total) * 100
            bar_length = 30
            filled = int(bar_length * processed / total)
            bar = "█" * filled + "░" * (bar_length - filled)

            # Show new file processed
            if processed > last_processed and processed > 0:
                print(f"\n✓ Completed file {processed}/{total}")
                last_processed = processed

            print(f"\r{bar} {progress:.0f}% | {processed}/{total} files | Status: {status.upper()}", end="", flush=True)
        else:
            print(f"\rStatus: {status.upper()}", end="", flush=True)

        if status == "completed":
            print("\n\n" + "="*50)
            print("✅ JOB COMPLETED SUCCESSFULLY!")
            print("="*50)

            # Get results
            print("\nFetching results...")
            results_response = requests.get(f"{base_url}/transcribe/{job_id}/results")
            results = results_response.json()

            print(f"\n📊 Summary:")
            print(f"   Total files: {results['total_files']}")
            print(f"   Successful: {results['successful']}")
            print(f"   Failed: {results['failed']}")
            print(f"   Output directory: {results['output_dir']}")

            print(f"\n📁 View transcriptions:")
            print(f"   ls -lh {results['output_dir']}/")

            print(f"\n📄 Read formatted transcripts:")
            print(f"   cat {results['output_dir']}/combined_transcript.txt")
            print(f"   cat {results['output_dir']}/*_transcript.txt")

            print(f"\n📊 View JSON data:")
            print(f"   cat {results['output_dir']}/*.json")

            print(f"\n🔗 Get full results:")
            print(f"   curl 'http://localhost:8000/transcribe/{job_id}/results' | python3 -m json.tool")
            break

        elif status == "failed":
            print("\n\n" + "="*50)
            print("❌ JOB FAILED")
            print("="*50)
            print("\nCheck server logs for error details")
            break

        time.sleep(3)

    except KeyboardInterrupt:
        print("\n\n⏸️  Monitoring stopped (job still running)")
        print(f"\nResume monitoring with:")
        print(f"  python monitor_job.py {job_id}")
        break
    except requests.exceptions.ConnectionError:
        print("\n❌ Cannot connect to server. Is it running?")
        break
    except Exception as e:
        print(f"\n❌ Error: {e}")
        break

print()
