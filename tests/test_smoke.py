"""Smoke tests for Ottolingo using Streamlit's AppTest framework."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest


def _login_anonymous(at: AppTest) -> AppTest:
    """Click the 'Anoniem' button to log in without saving."""
    for btn in at.button:
        if "Anoniem" in str(btn.label):
            btn.click().run()
            return at
    raise AssertionError("Anoniem button not found")


def test_app_boots_to_login_screen():
    """App starts and shows user selection."""
    at = AppTest.from_file("app.py", default_timeout=10)
    at.run()
    assert not at.exception, f"App crashed: {at.exception}"
    assert any("Wie ben je?" in str(el.label) for el in at.text_input)


def test_anonymous_session_arabic():
    """Anonymous user can start with Arabic and sees exercise UI."""
    at = AppTest.from_file("app.py", default_timeout=10)
    at.run()

    _login_anonymous(at)

    assert not at.exception, f"App crashed after login: {at.exception}"
    # Should now show sidebar with language/category/mode selectors
    # Default language is Arabic
    assert any("Arabisch" in str(el.value) for el in at.selectbox)


def test_anonymous_session_japanese():
    """Anonymous user can switch to Japanese."""
    at = AppTest.from_file("app.py", default_timeout=10)
    at.run()

    _login_anonymous(at)

    assert not at.exception, f"App crashed after login: {at.exception}"

    # Find language selector and switch to Japanese
    lang_select = None
    for sb in at.selectbox:
        if "Japans" in str(sb.options):
            lang_select = sb
            break

    assert lang_select is not None, "Language selector not found"
    lang_select.set_value("🇯🇵 Japans").run()

    assert not at.exception, f"App crashed after language switch: {at.exception}"


def test_arabic_categories_load():
    """Arabic categories are discovered and words load."""
    at = AppTest.from_file("app.py", default_timeout=10)
    at.run()
    _login_anonymous(at)

    # Check categories are present in a selectbox
    category_options_found = False
    for sb in at.selectbox:
        opts = [str(o) for o in sb.options]
        if "Alle woorden" in opts and "Basis" in opts:
            category_options_found = True
            break

    assert category_options_found, "Arabic categories not found in selectbox"


def test_japanese_categories_load():
    """Japanese categories are discovered after language switch."""
    at = AppTest.from_file("app.py", default_timeout=10)
    at.run()
    _login_anonymous(at)

    # Switch to Japanese
    for sb in at.selectbox:
        if "Japans" in str(sb.options):
            sb.set_value("🇯🇵 Japans").run()
            break

    # Check Japanese categories
    category_options_found = False
    for sb in at.selectbox:
        opts = [str(o) for o in sb.options]
        if "Alle woorden" in opts and "Basis" in opts:
            category_options_found = True
            break

    assert category_options_found, "Japanese categories not found in selectbox"


def test_no_crash_on_all_modes_arabic():
    """Cycling through all Arabic modes doesn't crash."""
    at = AppTest.from_file("app.py", default_timeout=10)
    at.run()
    _login_anonymous(at)

    modes = ["Nederlands -> Arabisch", "Arabisch -> Nederlands", "Schrift oefenen"]
    for mode in modes:
        for sb in at.selectbox:
            if mode in [str(o) for o in sb.options]:
                sb.set_value(mode).run()
                assert not at.exception, f"Crashed on mode '{mode}': {at.exception}"
                break


def test_no_crash_on_all_modes_japanese():
    """Cycling through all Japanese modes doesn't crash."""
    at = AppTest.from_file("app.py", default_timeout=10)
    at.run()
    _login_anonymous(at)

    # Switch to Japanese
    for sb in at.selectbox:
        if "Japans" in str(sb.options):
            sb.set_value("🇯🇵 Japans").run()
            break

    modes = ["Nederlands -> Japans", "Japans -> Nederlands", "Hiragana oefenen"]
    for mode in modes:
        for sb in at.selectbox:
            if mode in [str(o) for o in sb.options]:
                sb.set_value(mode).run()
                assert not at.exception, f"Crashed on mode '{mode}': {at.exception}"
                break
