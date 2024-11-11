import json
import os
import shutil
import sqlite3
import sys
from typing import Optional
import re
import traceback

import requests
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


class Chrome100Spider(scrapy.Spider):
    name = "chrome100-scraper"
    start_urls = ["https://chrome100.dev/"]

    def parse(self, response):
        table = response.css("table")[0]

        for row in table.css("tbody tr"):
            board_name = row.css("td:nth-child(1)::text").get()
            version_link = row.css("td:nth-child(3) a::attr(href)").get()

            yield scrapy.Request(
                f"https://chrome100.dev/{version_link}",
                callback=self.parse_versions_page,
            )

    def parse_versions_page(self, response):
        board_name = response.css("body > h1 > code::text").get()
        brands = response.css("body > ul:nth-child(13) > li::text").getall()

        table = response.css("table")[0]

        for row in table.css("tbody tr"):
            version = row.css("td:nth-child(2)::text").get()
            download_links = row.css("td:nth-child(4) a::attr(href)").getall()

            yield {
                "board_name": board_name,
                "version": version,
                "download_links": download_links,
                "brands": brands
            }


def fix_mp(mp_str):
    if mp_str == "mp":
        return "mp", 1
    if mp_str.endswith("-mp"):
        return mp_str, 1
    return "-".join(mp_str.split("-")[0:-1]), int(mp_str.split("-")[-1].lstrip("v"))



def main():
    if os.path.exists("temp.json"):
        os.remove("temp.json")
    process = CrawlerProcess(
        {
            "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "FEEDS": {
                "temp.json": {"format": "json"},
            },
        }
    )
    process.crawl(Chrome100Spider)
    process.start()
    if not os.path.exists("temp.json"):
        print("Something goofed!")
        return 1
    print("Scraping complete!")
    with open("temp.json", "r") as f:
        data = json.load(f)
    os.remove("temp.json")
    print("Cleaning old tree...")
    shutil.rmtree("boards")
    os.makedirs("boards")
    unique = list({entry["board_name"] for entry in data})
    print(f"Found {len(unique)} boards.")
    for board in unique:
        images = [entry for entry in data if entry["board_name"] == board]
        new_images = []
        expr = re.compile(f"https:\/\/dl\.google\.com\/dl\/edgedl\/chromeos\/recovery\/chromeos_(.*)_{board}_recovery_(.*)_(.*).bin.zip")
        for image in images:
            matches = expr.finditer(image["download_links"][0])
            for match in matches:
                mp_token, mp_key = fix_mp(match.group(3)) 
                new_images.append({
                    "board": board,
                    "platform": match.group(1),
                    "chrome": image["version"],
                    "mp_token": mp_token,
                    "mp_key": mp_key,
                    "channel": match.group(2),
                    "last_modified": "1970-01-01T00:00:00Z" # this part can't really be extracted, TODO: cross-reference chrome-versions database
                })
        brands = images[0]["brands"]
        images = new_images
        filepath = os.path.join("boards", f"{board}.json")
        with open(filepath, 'w') as f:
            json.dump({
                "pageProps": {
                    "board": board,
                    "images": images,
                    "brands": brands,
                },
                "__N_SSP": True
            }, f, indent=2)

        print(f"Created {filepath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
