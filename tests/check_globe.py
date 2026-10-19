"""Open globe.html in headless Edge/Chrome and check what a visitor would see.

    pip install playwright pillow && python -m playwright install chromium   # or use your installed Edge
    python tests/check_globe.py            # prints PASS/FAIL per check, exit code 1 on any FAIL

Needs internet (map tiles and the country outlines come from CDNs). Screenshots and the
share image land in tests/out/ (git-ignored).
"""
import functools, http.server, io, json, pathlib, sys, threading

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "out"
OUT.mkdir(exist_ok=True)
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""), flush=True)


def serve():
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{s.server_port}/globe.html"


BAD = """window.TRIPS = {title: "bad", homes: {A: "home"}, country: {A: "GB", B: "FR"},
  places: {A: ["Aville", 51.5, -0.1], B: ["Bville", 48.8, 2.3]},
  trips: [["2020-01-02", "2020-01-05", "A", ["B"], "ok", "o"],
          ["2020-02-02", "2020-02-05", "A", ["XXX"], "unknown place", "o"],
          ["2020-13-40", "", "A", ["B"], "bad date", "d"],
          ["2020-03-02", "2020-03-01", "A", ["B"], "ends before start", "o"]]};"""


def wait_ready(page):
    page.wait_for_function("typeof map !== 'undefined' && !!map.getSource('cities')", timeout=60000)


def main():
    url = serve()
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="msedge", args=["--enable-unsafe-swiftshader"])
        except Exception:
            browser = p.chromium.launch(args=["--enable-unsafe-swiftshader"])
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)

        # 1. demo data loads cleanly
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url)
        wait_ready(page)
        n = page.evaluate("T.length")
        shown = page.inner_text("#stats .stat b")
        check("demo loads without script errors", not errors, "; ".join(errors)[:200])
        check("trip count shown = trips in data", shown == str(n), f"{shown} vs {n}")

        # 6. visited countries are shaded and the share of the world is shown
        try:
            page.wait_for_function("map.getLayer('visited') && map.getSource('countries') && map.isSourceLoaded('countries')", timeout=60000)
            want = sorted(page.evaluate("[...new Set(T.flatMap(t=>t.places).map(k=>iso(k)).filter(Boolean))]"))
            got = sorted(page.evaluate("map.getFilter('visited')[2][1]"))
            check("visited-country fill covers every visited country", got == want, f"{len(got)} vs {len(want)}")
            stats = page.inner_text("#stats")
            check("countries stat shows share of the world", "% of 195" in stats, stats.replace("\n", " ")[:120])
            page.wait_for_timeout(2500)
            page.screenshot(path=str(OUT / "globe.png"))
        except Exception as e:
            check("6. country shading", False, type(e).__name__)
        try:

            # 7. deep link, keyboard, timeline
            tid = page.evaluate("tripId(T[3])")
            page.goto(url + "#trip=" + tid)
            wait_ready(page)
            page.wait_for_timeout(500)
            check("#trip= link opens that trip", page.evaluate("st.sel") == 3, f"sel={page.evaluate('st.sel')} for {tid}")
            page.keyboard.press("ArrowRight")
            page.wait_for_timeout(300)
            sel = page.evaluate("st.sel")
            check("→ moves to another trip and updates the link", sel not in (None, 3) and page.evaluate("location.hash") == "#trip=" + page.evaluate(f"tripId(T[{sel}])"), f"sel={sel} hash={page.evaluate('location.hash')}")
            page.keyboard.press("p")
            page.wait_for_timeout(300)
            check("P starts playback", "Stop" in page.inner_text("#play"))
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
            check("Esc stops playback and clears the selection", "Play" in page.inner_text("#play") and page.evaluate("st.sel") is None)
            page.keyboard.press("g")
            page.wait_for_timeout(300)
            check("G switches globe/flat", "Flat" in page.inner_text("#proj"))
            bars = page.locator("#tl .bar")
            check("timeline has one bar per trip", bars.count() == n, f"{bars.count()} vs {n}")
            if bars.count():
                bars.nth(5).click()
                page.wait_for_timeout(300)
                check("clicking a timeline bar selects its trip", page.evaluate("st.sel") == int(bars.nth(5).get_attribute("data-i")))
            page.screenshot(path=str(OUT / "selected.png"))
        except Exception as e:
            check("7. deep link / keys / timeline", False, type(e).__name__ + " " + str(e).splitlines()[0][:80])

        # 5. share image
        try:
            with page.expect_download(timeout=20000) as dl:
                page.keyboard.press("Escape")
                page.click("#share")
            path = OUT / "share.png"
            dl.value.save_as(str(path))
            from PIL import Image, ImageStat
            im = Image.open(path).convert("RGB")
            spread = max(ImageStat.Stat(im.crop((0, 300, 1080, 1000))).stddev)
            check("share image is a 1080x1350 PNG with the map in it", im.size == (1080, 1350) and spread > 12, f"size={im.size} stddev={spread:.1f}")
        except Exception as e:
            check("share image is a 1080x1350 PNG with the map in it", False, type(e).__name__)

        # 8. broken data shows what is wrong and still renders the good trips
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.route("**/data/trips.js", lambda r: r.fulfill(status=200, content_type="text/javascript", body=BAD))
        page.goto(url)
        try:
            page.wait_for_selector("#err", state="visible", timeout=15000)
            msg = page.inner_text("#err")
        except Exception:
            msg = ""
        check("bad data: banner names each problem", all(s in msg for s in ("XXX", "2020-13-40", "ends before")), msg.replace("\n", " ")[:160])
        try:
            wait_ready(page)
            good = page.inner_text("#stats .stat b")
        except Exception:
            good = "?"
        check("bad data: page still renders the valid trip", not errors and good == "1", f"trips={good} errors={'; '.join(errors)[:120]}")
        page.screenshot(path=str(OUT / "bad_data.png"))
        browser.close()
    print(f"{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
