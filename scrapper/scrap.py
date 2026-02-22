import os
import requests
from bs4 import BeautifulSoup
import json
import time
from tqdm import tqdm
import rlcompleter
import re
from multiprocessing import Pool, Manager, Lock
from functools import partial

BASE = "https://www.museunacional.cat"
START = "https://www.museunacional.cat/en/collections/medieval-gothic-art"

IMG_DIR = "images"
META_DIR = "metadata"
COMBINED_JSON = "all_metadata.json"
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(META_DIR, exist_ok=True)

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})


# ---------------------------------------------------------
# URL normalization helpers
# ---------------------------------------------------------


def normalize_url(href):
    """Return a clean absolute URL, or None if invalid."""
    if not href:
        return None
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE + href
    return None


# ---------------------------------------------------------
# Fetchers
# ---------------------------------------------------------


def get_soup(url):
    r = session.get(url)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    soup.base_url = url
    return soup


def get_collection_pages():
    return [
        f"https://www.museunacional.cat/en/collections/medieval-gothic-art?page={i}"
        for i in range(45)
    ]


def collect_item_links(page_url):
    soup = get_soup(page_url)
    links = []

    for a in soup.select(".row-catalog .file .content a"):
        raw = a.get("href")
        if raw and "/colleccio/" in raw:
            full = normalize_url(raw)
            if full:
                links.append(full)

    return list(dict.fromkeys(links))


# ---------------------------------------------------------
# Item extraction
# ---------------------------------------------------------


def is_painting(soup):
    tags = {a.get_text(strip=True).lower() for a in soup.select(".ds-detail-tags")}
    return "painting" in tags


def extract_image_url(soup):
    js_text = soup.select_one(".node-piece script").get_text(strip=True)

    jpg_urls = re.findall(r'https://[^"\s]+?\.jpg', js_text, flags=re.IGNORECASE)

    return jpg_urls[0]


def extract_metadata(soup):
    title = soup.select_one(".title h2")
    title = title.get_text(strip=True) if title else None

    info = soup.select_one(".group_piece_technical")
    info = info.get_text(strip=True, separator=";") if info else None

    author = soup.select_one(".field-name-field-piece-authors-author")
    author = author.get_text(strip=True) if author else None

    return {
        "title": title,
        "info": info,
        "url": soup.base_url,
        "author": author,
    }


def download(url, path):
    r = session.get(url)
    r.raise_for_status()
    with open(path, "wb") as f:
        f.write(r.content)


# ---------------------------------------------------------
# Item processing
# ---------------------------------------------------------


def process_item(item_url, all_metadata_dict, lock):
    """Process a single item and update shared metadata."""
    try:
        soup = get_soup(item_url)

        if not is_painting(soup):
            return None

        meta = extract_metadata(soup)

        img_url = extract_image_url(soup)

        if not img_url:
            return None
        else:
            meta["image_url"] = img_url

        # filename
        filename = img_url.split("/")[-1].split(".")[0]
        filename = filename.replace("/", "-").replace(" ", "_")

        img_path = f"{IMG_DIR}/{filename}.jpg"
        json_path = f"{META_DIR}/{filename}.json"

        # try:
        #     download(img_url, img_path)
        # except Exception:
        #     return None

        # with open(json_path, "w", encoding="utf-8") as f:
        #     json.dump(meta, f, indent=2, ensure_ascii=False)

        # Add to combined metadata (thread-safe)
        with lock:
            all_metadata_dict[filename] = meta

        time.sleep(0.1)  # polite delay
        return filename

    except Exception as e:
        return None


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------


def main():
    pages = get_collection_pages()

    # Load existing combined metadata or start fresh
    if os.path.exists(COMBINED_JSON):
        with open(COMBINED_JSON, "r", encoding="utf-8") as f:
            existing_metadata = json.load(f)
    else:
        existing_metadata = {}

    # Collect all item URLs first
    print("Collecting all item URLs...")
    all_items = []
    for page in tqdm(pages, desc="Catalogue pages"):
        items = collect_item_links(page)
        all_items.extend(items)

    print(f"Found {len(all_items)} items to process")

    # Use Manager for shared state
    with Manager() as manager:
        all_metadata_dict = manager.dict(existing_metadata)
        lock = manager.Lock()

        # Create partial function with shared state
        process_func = partial(
            process_item, all_metadata_dict=all_metadata_dict, lock=lock
        )

        # Process items in parallel
        num_processes = os.cpu_count() or 4
        print(f"Processing with {num_processes} workers...")

        with Pool(processes=num_processes) as pool:
            results = list(
                tqdm(
                    pool.imap_unordered(process_func, all_items),
                    total=len(all_items),
                    desc="Processing items",
                )
            )

        # Convert manager.dict to regular dict and save
        final_metadata = dict(all_metadata_dict)

    # Save combined metadata
    print("Saving combined metadata...")
    with open(COMBINED_JSON, "w", encoding="utf-8") as f:
        json.dump(final_metadata, f, indent=2, ensure_ascii=False)

    successful = sum(1 for r in results if r is not None)
    print(f"Successfully processed {successful}/{len(all_items)} items")


if __name__ == "__main__":
    main()
