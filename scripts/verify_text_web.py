"""Real Edge desktop/mobile smoke check against the running local server."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    report = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        for width in (1440, 390):
            page = browser.new_page(viewport={'width': width, 'height': 1000})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto('http://127.0.0.1:8010/', wait_until='networkidle')
            assert page.locator('[data-mode=music]').is_disabled()
            page.locator('#song-search').fill('Evil dudes demo')
            page.locator('#search-results [data-seed]').first.wait_for(timeout=30000)
            page.locator('#search-results [data-seed]').first.click()
            page.locator('#song-grid .song-card').first.wait_for(timeout=60000)
            assert page.locator('#song-grid .song-card').count() == 10
            chosen = page.locator('[data-compare]').first.get_attribute('data-compare')
            chosen_title = page.locator('[data-detail]').first.inner_text()
            page.locator('[data-compare]').first.click()
            page.wait_for_function("document.querySelector('#lyrics-origin-status').textContent === 'Letra original del corpus' && document.querySelector('#lyrics-selected-status').textContent === 'Letra original del corpus'")
            expected = page.request.get('http://127.0.0.1:8010/api/v1/tracks/'+chosen+'/lyrics').json()
            assert page.locator('#lyrics-selected-text').text_content() == expected['text']
            assert page.locator('#lyrics-selected-title').inner_text() == chosen_title
            assert len(page.locator('#lyrics-origin-text').text_content()) > 0
            panels = page.locator('.lyrics-panel')
            a, b = panels.nth(0).bounding_box(), panels.nth(1).bounding_box()
            assert (b['x'] > a['x']) if width > 650 else (b['y'] > a['y'])
            page.locator('#lyrics-comparison').screenshot(path=f'runtime/text_lyrics_{width}.png')
            page.locator('#close-lyrics').click()
            assert page.locator('#lyrics-comparison').is_hidden()
            page.locator('[data-save]').first.click()
            page.reload(wait_until='networkidle')
            page.locator('[data-page=saved]').first.click()
            assert page.locator('#song-grid .song-card').count() == 1
            page.locator('[data-detail]').first.click()
            assert page.locator('#song-dialog').is_visible()
            page.locator('.dialog-close').click()
            page.locator('[data-page=discover]').first.click()
            page.locator('#text-strategy').select_option('tfidf')
            page.locator('#free-text').fill('Leaving home and missing my family xyzzyunknown')
            page.locator('#free-text-form button').click()
            page.locator('#song-grid .song-card').first.wait_for(timeout=60000)
            assert 'TF-IDF' in page.locator('.song-reason').first.inner_text()
            page.locator('[data-compare]').first.click()
            page.wait_for_function("document.querySelector('#lyrics-selected-status').textContent === 'Letra original del corpus'")
            assert page.locator('#lyrics-origin-text').text_content() == 'Leaving home and missing my family xyzzyunknown'
            assert page.locator('#lyrics-origin-label').inner_text() == 'TEXTO DE PARTIDA'
            page.locator('#close-lyrics').click()
            page.screenshot(path=f'runtime/text_web_{width}.png', full_page=True)
            report.append({'width': width, 'cards': page.locator('#song-grid .song-card').count(), 'errors': errors, 'overflow': page.evaluate('document.documentElement.scrollWidth > innerWidth'), 'version': page.locator('#version-note').inner_text()})
            page.locator('#free-text').fill('xyzzyunknownqwerty')
            page.locator('#free-text-form button').click()
            page.wait_for_function("document.querySelector('#empty-title').textContent === 'No pudimos recomendar'")
            assert 'vocabulario' in page.locator('#empty-copy').inner_text()
            page.route('**/api/v1/recommendations', lambda route: route.fulfill(status=503, content_type='application/json', body='{"detail":"API interrumpida"}'))
            page.locator('#free-text').fill('love')
            page.locator('#free-text-form button').click()
            page.wait_for_function("document.querySelector('#empty-copy').textContent === 'API interrumpida'")
            assert page.locator('#song-grid').is_hidden()
            assert not errors
            assert not report[-1]['overflow']
            page.close()
        page = browser.new_page()
        page.goto('http://127.0.0.1:8010/mobile.html', wait_until='networkidle')
        assert page.frame_locator('iframe').locator('#free-text').count() == 1
        browser.close()
    Path('runtime/text_web_browser.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
