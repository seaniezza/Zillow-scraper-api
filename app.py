from flask import Flask, request, jsonify
import asyncio
from playwright.async_api import async_playwright
import re

app = Flask(__name__)

async def scrape_zillow(search_url, pages):
    listings = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for i in range(1, pages + 1):
            url = f"{search_url}&p={i}"
            await page.goto(url)
            await page.wait_for_selector("article")

            properties = await page.query_selector_all("article")
            for prop in properties:
                try:
                    addr = await (await prop.query_selector("address")).inner_text()
                    price_elem = await prop.query_selector("span[data-test='property-card-price']")
                    price = int(re.sub(r"[^\d]", "", await price_elem.inner_text())) if price_elem else 0

                    bed_elem = await prop.query_selector("ul > li")
                    bed_text = await bed_elem.inner_text() if bed_elem else ""
                    bedrooms = int(re.search(r"(\\d+)", bed_text).group(1)) if re.search(r"(\\d+)", bed_text) else 0

                    zip_match = re.search(r"\\b(\\d{5})\\b", addr)
                    zip_code = zip_match.group(0) if zip_match else None

                    listings.append({
                        "address": addr,
                        "price": price,
                        "bedrooms": min(bedrooms, 4),
                        "zip": zip_code
                    })
                except:
                    continue
        await browser.close()
    return listings

@app.route('/scrape', methods=['GET'])
def scrape():
    url = request.args.get("url")
    pages = int(request.args.get("pages", 1))
    data = asyncio.run(scrape_zillow(url, pages))
    return jsonify(data)

if __name__ == '__main__':
    app.run()
