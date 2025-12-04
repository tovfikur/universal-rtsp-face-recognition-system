"""
Playwright test to debug snapshot display issue
"""
import asyncio
import time
from playwright.async_api import async_playwright

async def test_snapshot_flow():
    """Test the complete flow: start camera -> click RTSP -> check snapshots"""

    async with async_playwright() as p:
        # Launch browser in headed mode so we can see what's happening
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context()
        page = await context.new_page()

        # Enable console logging to see frontend errors
        page.on("console", lambda msg: print(f"[Browser Console] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"[Browser Error] {err}"))

        print("\n=== Step 1: Navigate to application ===")
        await page.goto("http://localhost:5000")
        await page.wait_for_load_state("networkidle")
        print("✓ Page loaded")

        # Take screenshot
        await page.screenshot(path="screenshots/01_initial_load.png")

        print("\n=== Step 2: Open settings panel and configure webcam ===")
        # Click settings button
        await page.click('button[data-bs-target="#settingsPanel"]')
        await asyncio.sleep(1)

        # Set source to webcam 0
        await page.fill("#cameraSourceInput", "0")
        await asyncio.sleep(0.5)

        # Click Apply & Connect
        await page.click("#applyCameraSourceBtn")
        print("✓ Clicked Apply & Connect for webcam")
        await asyncio.sleep(3)  # Wait for connection

        await page.screenshot(path="screenshots/02_after_connect.png")

        # Close settings panel by clicking outside
        await page.click("body")
        await asyncio.sleep(1)

        print("\n=== Step 3: Check if video stream is showing ===")
        video_visible = await page.is_visible("#liveVideo")
        remote_visible = await page.is_visible("#remoteStream:not(.d-none)")
        print(f"Video element visible: {video_visible}")
        print(f"Remote stream visible: {remote_visible}")

        print("\n=== Step 4: Click RTSP button to start background detection ===")
        # Check if RTSP button exists
        rtsp_btn_exists = await page.is_visible("#startRemoteBtn")
        print(f"RTSP button exists: {rtsp_btn_exists}")

        if rtsp_btn_exists:
            await page.click("#startRemoteBtn")
            print("✓ Clicked RTSP button")
            await asyncio.sleep(2)

        await page.screenshot(path="screenshots/03_after_rtsp_click.png")

        print("\n=== Step 5: Check snapshot tab ===")
        # Switch to Snapshot tab
        snapshot_tab = await page.is_visible("#snapshot-tab")
        print(f"Snapshot tab exists: {snapshot_tab}")

        if snapshot_tab:
            await page.click("#snapshot-tab")
            await asyncio.sleep(1)
            print("✓ Clicked Snapshot tab")

        await page.screenshot(path="screenshots/04_snapshot_tab.png")

        print("\n=== Step 6: Wait for snapshots to appear (10 seconds) ===")
        for i in range(5):
            await asyncio.sleep(2)

            # Check if snapshot image is visible
            snapshot_img_visible = await page.is_visible("#snapshotImage:not(.d-none)")
            placeholder_visible = await page.is_visible("#snapshotPlaceholder:not(.d-none)")

            print(f"[{i*2}s] Snapshot image visible: {snapshot_img_visible}, Placeholder visible: {placeholder_visible}")

            # Check snapshot time
            snapshot_time = await page.text_content("#snapshotTime")
            print(f"[{i*2}s] Snapshot time: {snapshot_time}")

            await page.screenshot(path=f"screenshots/05_snapshot_wait_{i*2}s.png")

        print("\n=== Step 7: Check API endpoints directly ===")
        # Check background status
        bg_status_response = await page.evaluate("""
            async () => {
                const response = await fetch('/api/background/status');
                return await response.json();
            }
        """)
        print(f"Background status: {bg_status_response}")

        # Try to fetch snapshot directly
        snapshot_response = await page.evaluate("""
            async () => {
                try {
                    const response = await fetch('/api/snapshot?t=' + Date.now());
                    return {
                        ok: response.ok,
                        status: response.status,
                        contentType: response.headers.get('content-type')
                    };
                } catch (error) {
                    return { error: error.message };
                }
            }
        """)
        print(f"Snapshot API response: {snapshot_response}")

        # Check snapshot history
        history_response = await page.evaluate("""
            async () => {
                const response = await fetch('/api/snapshot/history');
                return await response.json();
            }
        """)
        print(f"Snapshot history: {history_response}")

        print("\n=== Step 8: Check JavaScript state ===")
        js_state = await page.evaluate("""
            () => {
                return {
                    snapshotRunning: state.snapshotRunning,
                    snapshotInterval: state.snapshotInterval !== null,
                    remoteSource: state.remoteSource,
                    stream: state.stream !== null
                };
            }
        """)
        print(f"JavaScript state: {js_state}")

        await page.screenshot(path="screenshots/06_final_state.png")

        print("\n=== Test Complete ===")
        print("Screenshots saved to screenshots/ directory")
        print("\nPress Enter to close browser...")

        # Keep browser open for manual inspection
        await asyncio.sleep(30)

        await browser.close()

if __name__ == "__main__":
    # Create screenshots directory
    import os
    os.makedirs("screenshots", exist_ok=True)

    print("Starting Playwright test...")
    print("Make sure the backend is running at http://localhost:5000")
    print("")

    asyncio.run(test_snapshot_flow())
