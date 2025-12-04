"""
Simple visual test for snapshot functionality
Run this AFTER starting the backend: python backend/app.py
"""
import asyncio
import time
from playwright.async_api import async_playwright

async def test_snapshots():
    """Visual test - opens browser and tests snapshot display"""

    async with async_playwright() as p:
        print("\n" + "="*60)
        print("VISUAL SNAPSHOT TEST")
        print("="*60)
        print("\nStarting browser (visible mode)...")

        # Launch browser in visible mode
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=1000  # Slow down by 1 second per action so we can see
        )
        context = await browser.new_context()
        page = await context.new_page()

        # Log browser console messages
        page.on("console", lambda msg: print(f"  [Browser] {msg.text}"))

        try:
            print("\n[1] Opening http://localhost:5000 ...")
            await page.goto("http://localhost:5000", timeout=10000)
            await page.wait_for_load_state("networkidle")
            print("    [OK] Page loaded")

            # Take screenshot
            await page.screenshot(path="test_01_loaded.png")
            print("    [OK] Screenshot: test_01_loaded.png")

            print("\n[2] Opening settings panel...")
            await page.click('button[data-bs-toggle="tooltip"][title="Camera Settings"]')
            await asyncio.sleep(1)
            print("    [OK] Settings panel opened")

            print("\n[3] Setting webcam source to '0'...")
            await page.fill("#cameraSourceInput", "0")
            await asyncio.sleep(0.5)
            print("    [OK] Source set to webcam 0")

            print("\n[4] Clicking 'Apply & Connect'...")
            await page.click("#applyCameraSourceBtn")
            await asyncio.sleep(3)  # Wait for connection
            print("    [OK] Connection initiated")

            await page.screenshot(path="test_02_connected.png")
            print("    [OK] Screenshot: test_02_connected.png")

            # Close settings by pressing Escape
            await page.keyboard.press("Escape")
            await asyncio.sleep(1)

            print("\n[5] Checking if RTSP button is visible...")
            rtsp_visible = await page.is_visible("#startRemoteBtn")
            print(f"    RTSP button visible: {rtsp_visible}")

            if rtsp_visible:
                print("\n[6] Clicking RTSP button to start background detection...")
                await page.click("#startRemoteBtn")
                await asyncio.sleep(2)
                print("    [OK] RTSP button clicked")

                await page.screenshot(path="test_03_rtsp_clicked.png")
                print("    [OK] Screenshot: test_03_rtsp_clicked.png")

            print("\n[7] Switching to Snapshot tab...")
            await page.click("#snapshot-tab")
            await asyncio.sleep(1)
            print("    [OK] Snapshot tab active")

            await page.screenshot(path="test_04_snapshot_tab.png")
            print("    [OK] Screenshot: test_04_snapshot_tab.png")

            print("\n[8] Waiting 10 seconds for snapshots to appear...")
            snapshot_appeared = False

            for i in range(5):
                await asyncio.sleep(2)

                # Check if snapshot image is visible (not hidden)
                snapshot_visible = await page.is_visible("#snapshotImage:not(.d-none)")
                placeholder_visible = await page.is_visible("#snapshotPlaceholder:not(.d-none)")
                snapshot_time = await page.text_content("#snapshotTime")

                status = "VISIBLE" if snapshot_visible else "HIDDEN"
                print(f"    [{(i+1)*2}s] Snapshot: {status}, Time: {snapshot_time}")

                if snapshot_visible and not snapshot_appeared:
                    snapshot_appeared = True
                    print("    [SUCCESS] Snapshot appeared!")
                    await page.screenshot(path=f"test_05_snapshot_visible.png")
                    print(f"    [OK] Screenshot: test_05_snapshot_visible.png")

            print("\n[9] Checking JavaScript state...")
            js_state = await page.evaluate("""
                () => {
                    return {
                        snapshotRunning: state.snapshotRunning,
                        hasInterval: state.snapshotInterval !== null,
                        remoteSource: state.remoteSource,
                        hasStream: state.stream !== null
                    };
                }
            """)
            print(f"    snapshotRunning: {js_state['snapshotRunning']}")
            print(f"    hasInterval: {js_state['hasInterval']}")
            print(f"    remoteSource: {js_state['remoteSource']}")
            print(f"    hasStream: {js_state['hasStream']}")

            print("\n[10] Checking backend API...")
            bg_status = await page.evaluate("""
                async () => {
                    const res = await fetch('/api/background/status');
                    return await res.json();
                }
            """)
            print(f"    Background running: {bg_status.get('background_running', False)}")
            print(f"    Stream active: {bg_status.get('stream_active', False)}")

            print("\n" + "="*60)
            print("TEST RESULTS")
            print("="*60)

            if snapshot_appeared:
                print("\n[SUCCESS] Snapshots are working!")
                print("- Snapshot image appeared in the UI")
                print("- Check test_05_snapshot_visible.png to see it")
            else:
                print("\n[FAILED] Snapshots did NOT appear")
                print("- Check screenshots for debugging")
                print("- Snapshot image element stayed hidden")

                if not js_state['snapshotRunning']:
                    print("\n[ISSUE] Frontend snapshot updates not running")
                    print("  -> startSnapshotUpdates() was not called")

                if not bg_status.get('background_running'):
                    print("\n[ISSUE] Backend background processing not running")
                    print("  -> Snapshot analysis thread not started")

            print("\n" + "="*60)
            print("\nBrowser will stay open for 30 seconds for manual inspection...")
            print("Press Ctrl+C to close early, or wait...")

            await asyncio.sleep(30)

        except Exception as e:
            print(f"\n[ERROR] Test failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()
            print("\nBrowser closed. Test complete.")

if __name__ == "__main__":
    print("\nMake sure backend is running: python backend/app.py")
    print("Starting test in 3 seconds...\n")
    time.sleep(3)

    asyncio.run(test_snapshots())
