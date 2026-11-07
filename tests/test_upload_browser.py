"""Opt-in browser regression tests using real rendering and controlled API replies.

Start the frontend, then set INFORM_UPLOAD_TEST_URL=http://localhost:3017 and run
pytest tests/test_upload_browser.py. Requires Playwright and its Chromium browser.
These checks do not run OCR.
"""

import base64
import io
import json
import os
from pathlib import Path
from urllib.parse import urlparse

import pytest
from PIL import Image


URL = os.environ.get("INFORM_UPLOAD_TEST_URL")
pytestmark = pytest.mark.skipif(not URL, reason="Set INFORM_UPLOAD_TEST_URL to a running frontend")


@pytest.fixture(scope="module")
def browser():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def upload(browser):
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(30_000)
    state = {"available": True, "posts": [], "sample_reads": 0}
    root = Path(__file__).resolve().parents[1]
    extraction = json.loads((root / "data/samples/extractions.json").read_text())["extractions"]["synthetic_270_clean"]
    sample = {
        "id": "synthetic_270_clean", "name": "Controlled sample",
        "provenance": "synthetic", "source_device": "inbody_270",
        "image_url": "/samples/synthetic_270_clean/image", "description": "Stored sample",
    }
    job = {
        "read_id": "controlled-read", "sample_id": None, "live": True,
        "status": "complete", "progress": 1, "message": "Controlled response",
        "extraction": extraction,
    }

    def api(route):
        path = urlparse(route.request.url).path.removeprefix("/api")
        if path == "/capabilities":
            route.fulfill(json={"live_read_available": state["available"]})
        elif path == "/auth/me":
            route.fulfill(status=401, json={"detail": "Guest"})
        elif path == "/samples":
            route.fulfill(json=[sample])
        elif path == "/samples/synthetic_270_clean":
            state["sample_reads"] += 1
            route.fulfill(json=extraction)
        elif path == "/samples/synthetic_270_clean/image":
            route.fulfill(body=image_bytes("PNG", "white"), content_type="image/png")
        elif path == "/reads" and route.request.method == "POST":
            state["posts"].append(route.request.post_data_json)
            route.fulfill(json=job)
        elif path.startswith("/reads/"):
            route.fulfill(json=job)
        else:
            route.continue_()

    page.route("**/*", api)
    yield page, state
    context.close()


def image_bytes(format, color):
    result = io.BytesIO()
    image = Image.new("RGB", (300, 400), color)
    if format == "PDF":
        image.save(result, format="PDF", save_all=True, append_images=[Image.new("RGB", image.size, "green")])
    else:
        image.save(result, format=format)
    return result.getvalue()


def open_picker(page):
    from playwright.sync_api import expect

    page.goto(f"{URL}/upload")
    button = page.get_by_role("button", name="Upload from device")
    expect(button).to_be_enabled()
    button.click()
    dialog = page.get_by_role("dialog")
    expect(dialog).to_be_visible()
    expect(dialog.get_by_role("button", name="Continue", exact=True)).to_be_disabled()
    expect(page.get_by_role("button", name="Confirm and Analyze")).to_have_count(0)
    dialog.get_by_role("checkbox").check()
    with page.expect_file_chooser() as picker:
        dialog.get_by_role("button", name="Continue", exact=True).click()
    return picker.value


def assert_raster(payload, color):
    assert payload["live"] is True
    data = payload["image_data"]
    assert data.startswith("data:image/jpeg;base64,")
    image = Image.open(io.BytesIO(base64.b64decode(data.split(",", 1)[1])))
    assert max(image.size) <= 1000
    pixel = image.getpixel((image.width // 2, image.height // 2))
    expected = (255, 0, 0) if color == "red" else (0, 0, 255)
    assert all(abs(actual - wanted) < 15 for actual, wanted in zip(pixel, expected)), pixel


def test_pdf_contents_not_filename_reach_reads(upload):
    from playwright.sync_api import expect

    page, state = upload
    picker = open_picker(page)
    for color in ("red", "blue"):
        if color == "blue":
            page.goto(f"{URL}/upload")
            with page.expect_file_chooser() as chosen:
                page.get_by_role("button", name="Upload from device").click()
            picker = chosen.value
        picker.set_files({"name": "same-name.pdf", "mimeType": "application/pdf", "buffer": image_bytes("PDF", color)})
        confirm = page.get_by_role("button", name="Confirm and Analyze")
        expect(confirm).to_be_visible()
        preview = page.get_by_alt_text("The photo you're about to send").get_attribute("src")
        assert_raster({"image_data": preview, "live": True}, color)
        expect(page.get_by_text("Read page 1 of 2", exact=True)).to_be_visible()
        assert len(state["posts"]) == (0 if color == "red" else 1)
        confirm.click()
        page.wait_for_url("**/preview")
        assert_raster(state["posts"][-1], color)
        assert state["posts"][-1]["image_data"] == preview
        assert page.evaluate("JSON.parse(sessionStorage.getItem('inform:sheetSource'))") == "pdf"
        assert page.evaluate("JSON.parse(sessionStorage.getItem('inform:sheetPages'))") == 2
    assert state["posts"][0]["image_data"] != state["posts"][1]["image_data"]


def test_unreadable_pdf_replacement_cannot_send_old_sheet(upload):
    from playwright.sync_api import expect

    page, state = upload
    picker = open_picker(page)
    picker.set_files({"name": "sheet.png", "mimeType": "image/png", "buffer": image_bytes("PNG", "red")})
    with page.expect_file_chooser() as chosen:
        page.get_by_role("button", name="Choose other file").click()
    chosen.value.set_files({"name": "broken.pdf", "mimeType": "application/pdf", "buffer": b"%PDF-1.7\nbroken"})
    error = page.get_by_role("alert").filter(has_text="That PDF could not be opened")
    expect(error).to_be_visible()
    expect(error).to_contain_text("damaged or password-protected")
    expect(page.get_by_role("button", name="Confirm and Analyze")).to_have_count(0)
    assert not state["posts"]
    with page.expect_file_chooser() as chosen:
        page.get_by_role("button", name="Upload from device").click()
    chosen.value.set_files({"name": "recovered.PDF", "mimeType": "", "buffer": image_bytes("PDF", "blue")})
    page.get_by_role("button", name="Confirm and Analyze").click()
    page.wait_for_url("**/preview")
    assert_raster(state["posts"][0], "blue")


@pytest.mark.parametrize(("extension", "mime", "format"), [("jpg", "image/jpeg", "JPEG"), ("png", "image/png", "PNG")])
def test_images_still_upload_after_consent(upload, extension, mime, format):
    page, state = upload
    picker = open_picker(page)
    picker.set_files({"name": f"sheet.{extension}", "mimeType": mime, "buffer": image_bytes(format, "red")})
    assert not state["posts"]
    page.get_by_role("button", name="Confirm and Analyze").click()
    page.wait_for_url("**/preview")
    assert_raster(state["posts"][0], "red")
    assert page.evaluate("JSON.parse(sessionStorage.getItem('inform:sheetSource'))") == "photo"


def test_unavailable_reader_keeps_samples_open_without_consent(upload):
    from playwright.sync_api import expect

    page, state = upload
    state["available"] = False
    page.goto(f"{URL}/upload")
    expect(page.get_by_role("button", name="Upload from device")).to_be_disabled()
    expect(page.get_by_role("button", name="Open Camera and Take Photo")).to_be_disabled()
    expect(page.locator('input[type="file"]')).to_be_disabled()
    page.get_by_role("button", name="Use sample: Controlled sample", exact=True).click()
    page.wait_for_url("**/preview")
    assert state["sample_reads"] == 1
    assert not state["posts"]
    assert page.evaluate("sessionStorage.getItem('inform:privacyAck')") is None
