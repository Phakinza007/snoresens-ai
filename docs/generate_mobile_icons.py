"""Render the existing Snoresens/Lucide vector into iOS asset catalog sizes."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
assets=ROOT/'mobile/ios/Runner/Assets.xcassets'
svg=(ROOT/'mobile/app-icon.svg').read_text()
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(device_scale_factor=1)
    page.set_content('<style>html,body{margin:0}svg{display:block;width:100vw;height:100vh}</style>'+svg)
    catalog=assets/'AppIcon.appiconset'
    for entry in json.loads((catalog/'Contents.json').read_text())['images']:
        size=round(float(entry['size'].split('x')[0])*float(entry['scale'].rstrip('x')))
        page.set_viewport_size(dict(width=size,height=size))
        page.screenshot(path=str(catalog/entry['filename']))
    for scale in (1,2,3):
        size=168*scale;page.set_viewport_size(dict(width=size,height=size))
        page.screenshot(path=str(assets/'LaunchImage.imageset'/f'LaunchImage{"" if scale==1 else f"@{scale}x"}.png'))
    browser.close()
