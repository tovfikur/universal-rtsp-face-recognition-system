"""
Visual test for RTSP face detection using Playwright.
Tests the full flow: connect to RTSP -> start detection -> verify bounding boxes.
"""

import asyncio
import time
from playwright.async_api import async_playwright
from pathlib import Path
import sys
import io

# Fix Windows console encoding issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

RTSP_URL = "rtsp://admin:123456789m@192.168.50.210:554/cam/realmonitor?channel=1&subtype=0"
WEB_URL = "http://localhost:5000"
OUTPUT_DIR = Path(__file__).parent / "test_screenshots"

async def test_rtsp_detection():
    """Visual test of RTSP face detection system"""

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"[Test] Saving screenshots to: {OUTPUT_DIR}")

    async with async_playwright() as p:
        # Launch browser in headed mode to see what's happening
        print("[Test] Launching browser...")
        browser = await p.chromium.launch(
            headless=False,  # Show browser window
            args=['--start-maximized']
        )

        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            permissions=['camera', 'microphone']
        )
        page = await context.new_page()

        # Enable console logging from browser
        page.on('console', lambda msg: print(f"[Browser] {msg.text}"))
        page.on('pageerror', lambda err: print(f"[Browser Error] {err}"))

        try:
            # Step 1: Navigate to web interface
            print(f"\n[Step 1] Navigating to {WEB_URL}...")
            await page.goto(WEB_URL, wait_until='networkidle')
            await page.wait_for_timeout(2000)
            await page.screenshot(path=OUTPUT_DIR / "01_homepage.png")
            print("[Step 1] OK - Homepage loaded")

            # Step 2: Open settings to configure RTSP
            print("\n[Step 2] Opening settings panel...")
            settings_btn = page.locator('button[data-bs-toggle="offcanvas"][data-bs-target="#settingsPanel"]')
            await settings_btn.click()
            await page.wait_for_timeout(1000)
            await page.screenshot(path=OUTPUT_DIR / "02_settings_open.png")
            print("[Step 2] OK - Settings panel opened")

            # Step 3: Enter RTSP URL
            print(f"\n[Step 3] Entering RTSP URL: {RTSP_URL}")
            rtsp_input = page.locator('#cameraSourceInput')
            await rtsp_input.fill(RTSP_URL)
            await page.wait_for_timeout(500)
            await page.screenshot(path=OUTPUT_DIR / "03_rtsp_entered.png")
            print("[Step 3] OK RTSP URL entered")

            # Step 4: Connect to RTSP stream
            print("\n[Step 4] Connecting to RTSP stream...")
            connect_btn = page.locator('#applyCameraSourceBtn')
            await connect_btn.click()

            # Wait for connection (give it time)
            print("[Step 4] Waiting for stream to connect (10 seconds)...")
            await page.wait_for_timeout(10000)
            await page.screenshot(path=OUTPUT_DIR / "04_stream_connecting.png")

            # Check if stream is visible
            remote_stream = page.locator('#remoteStream')
            is_visible = await remote_stream.is_visible()
            print(f"[Step 4] Remote stream visible: {is_visible}")

            if is_visible:
                print("[Step 4] OK Stream connected and visible")
            else:
                print("[Step 4] WARN Stream element not visible, checking status...")

            await page.screenshot(path=OUTPUT_DIR / "05_stream_loaded.png")

            # Step 5: Close settings panel
            print("\n[Step 5] Closing settings panel...")
            close_btn = page.locator('button.btn-close[data-bs-dismiss="offcanvas"]')
            await close_btn.click()
            await page.wait_for_timeout(1000)
            await page.screenshot(path=OUTPUT_DIR / "06_settings_closed.png")
            print("[Step 5] OK Settings closed")

            # Step 6: Start background detection (click RTSP button)
            print("\n[Step 6] Starting background detection...")
            rtsp_btn = page.locator('#startRemoteBtn')
            rtsp_btn_exists = await rtsp_btn.count() > 0
            print(f"[Step 6] RTSP button exists: {rtsp_btn_exists}")

            if rtsp_btn_exists:
                await rtsp_btn.click()
                await page.wait_for_timeout(2000)
                await page.screenshot(path=OUTPUT_DIR / "07_detection_started.png")
                print("[Step 6] OK Background detection started")
            else:
                print("[Step 6] ERROR RTSP button not found!")

            # Step 7: Monitor snapshot updates over time
            print("\n[Step 7] Monitoring snapshot updates for 30 seconds...")

            for i in range(6):
                await page.wait_for_timeout(5000)  # Wait 5 seconds

                # Take screenshot
                screenshot_path = OUTPUT_DIR / f"08_snapshot_t{i*5}s.png"
                await page.screenshot(path=screenshot_path)

                # Check snapshot element
                snapshot_img = page.locator('#snapshotImage')
                snapshot_visible = await snapshot_img.is_visible()

                # Check snapshot timestamp
                snapshot_time = page.locator('#snapshotTime')
                time_text = await snapshot_time.inner_text()

                # Check recognized counter
                recognized_counter = page.locator('#recognizedCounter')
                counter_text = await recognized_counter.inner_text()

                # Check FPS
                fps_counter = page.locator('#fpsCounter')
                fps_text = await fps_counter.inner_text()

                print(f"[Step 7] T+{i*5}s - Snapshot visible: {snapshot_visible}, Time: {time_text}, Recognized: {counter_text}, FPS: {fps_text}")

            await page.screenshot(path=OUTPUT_DIR / "09_final_state.png")
            print("[Step 7] OK Monitoring complete")

            # Step 8: Check system status via API
            print("\n[Step 8] Checking system status...")

            # Navigate to API endpoint to check status
            health_response = await page.request.get(f"{WEB_URL}/api/health")
            health_data = await health_response.json()
            print(f"[Step 8] Health: {health_data}")

            bg_response = await page.request.get(f"{WEB_URL}/api/background/status")
            bg_data = await bg_response.json()
            print(f"[Step 8] Background: {bg_data}")

            faces_response = await page.request.get(f"{WEB_URL}/api/faces")
            faces_data = await faces_response.json()
            print(f"[Step 8] Faces: {len(faces_data.get('faces', []))} registered")

            # Step 9: Take final full-page screenshot
            print("\n[Step 9] Taking final screenshot...")
            await page.screenshot(path=OUTPUT_DIR / "10_final_fullpage.png", full_page=True)

            # Step 10: Download snapshot image directly
            print("\n[Step 10] Downloading snapshot image...")
            try:
                snapshot_response = await page.request.get(f"{WEB_URL}/api/snapshot?t={int(time.time())}")
                if snapshot_response.ok:
                    snapshot_data = await snapshot_response.body()
                    snapshot_path = OUTPUT_DIR / "11_snapshot_direct.jpg"
                    with open(snapshot_path, 'wb') as f:
                        f.write(snapshot_data)
                    print(f"[Step 10] OK Snapshot saved to {snapshot_path}")
                else:
                    print(f"[Step 10] ERROR Snapshot API returned: {snapshot_response.status}")
            except Exception as e:
                print(f"[Step 10] ERROR Error downloading snapshot: {e}")

            print("\n" + "="*60)
            print("TEST COMPLETE")
            print("="*60)
            print(f"\nScreenshots saved to: {OUTPUT_DIR}")
            print("\nPlease check the screenshots to see:")
            print("1. If the stream is loading")
            print("2. If the snapshot panel is updating")
            print("3. If bounding boxes appear on detected faces")
            print("\nPress Enter to close browser...")

            # Keep browser open for manual inspection
            await page.wait_for_timeout(60000)  # Wait 60 seconds for manual inspection

        except Exception as e:
            print(f"\n[ERROR] Test failed: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path=OUTPUT_DIR / "error_state.png")

        finally:
            await browser.close()

if __name__ == "__main__":
    print("="*60)
    print("RTSP FACE DETECTION - VISUAL TEST")
    print("="*60)
    print("\nThis test will:")
    print("1. Open the web interface in a browser")
    print("2. Connect to the RTSP stream")
    print("3. Start background detection")
    print("4. Monitor for 30 seconds")
    print("5. Take screenshots at each step")
    print("\nStarting test...\n")

    asyncio.run(test_rtsp_detection())
