from flask import Flask, request, jsonify
from playwright.async_api import async_playwright
import asyncio
import re

app = Flask(__name__)

# Async scraping logic
def run_scraper(search_url, max_pages):
    return asyncio.run(scrape_zillow(search_url, max_pages))

async def scrape_zillow(search_url, max_pages=1):
    listings = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for page_num in range(1, max_pages + 1):
            url = f"{search_url}&p={page_num}"
            await page.goto(url, timeout=60000)
            await page.wait_for_selector("article")

            props = await page.query_selector_all("article")
            for prop in props:
                try:
                    addr_elem = await prop.query_selector("address")
                    address = await addr_elem.inner_text() if addr_elem else "N/A"

                    zip_code_match = re.search(r"\\b\\d{5}\\b", address)
                    zip_code = zip_code_match.group(0) if zip_code_match else None

                    price_elem = await prop.query_selector("span[data-test='property-card-price']")
                    price = int(re.sub(r"[^\\d]", "", await price_elem.inner_text())) if price_elem else 0

                    bed_elem = await prop.query_selector("ul > li")
                    bed_txt = await bed_elem.inner_text() if bed_elem else ""
                    bed_match = re.search(r"(\\d+)\\s*bd", bed_txt.lower())
                    bedrooms = int(bed_match.group(1)) if bed_match else 0

                    listings.append({
                        'address': address,
                        'zip': zip_code,
                        'price': price,
                        'bedrooms': min(bedrooms, 4)
                    })
                except:
                    continue

        await browser.close()
    return listings

# Flask route
@app.route('/scrape', methods=['GET'])
def scrape():
    search_url = request.args.get('url')
    max_pages = int(request.args.get('pages', 1))

    if not search_url:
        return jsonify({'error': 'Missing URL'}), 400

    try:
        results = run_scraper(search_url, max_pages)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
