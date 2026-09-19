import json
import re #imports python regular expressions module 
from pathlib import Path
from urllib.parse import urljoin
from app.config import HEADERS, DESTINATIONS
from bs4 import BeautifulSoup

# Paths
BASE_DIR = Path(__file__).resolve().parents[2]

RAW_HTML_DIR = BASE_DIR / "TravelAfricaRAGProject" / "Data" / "raw"
PROCESSED_DIR = BASE_DIR / "TravelAfricaRAGProject" / "Data" / "processed"
DESTINATIONS_DIR = PROCESSED_DIR / "destinations"

RAW_HTML_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
DESTINATIONS_DIR.mkdir(parents=True, exist_ok=True)

# Utility functions
def clean_text(value: str | None):
    """Normalize whitespace in extracted text."""

    if not value:
        return ""

    return re.sub(r"\s+", " ", value).strip()


def absolute_url(url: str | None, base_url: str):
    """Convert a relative URL into an absolute URL."""

    if not url:
        return None

    return urljoin(base_url, url.strip())


def extract_background_image(element, base_url: str):
    """
    Extract an image URL from an inline CSS background-image declaration.

    Example:
        background-image:url("https://example.com/image.jpg")
    """

    if not element:
        return None

    style = element.get("style", "")

    match = re.search(
        r"background-image\s*:\s*url\(\s*[\"']?(.*?)[\"']?\s*\)",
        style,
        flags=re.IGNORECASE,
    )

    if match:
        return absolute_url(match.group(1), base_url)

    return None


def extract_image_url(element, base_url: str):
    """
    Extract an image URL from either:

    1. <img src="...">
    2. lazy-loading attributes
    3. CSS background-image
    """

    if not element:
        return None

    # Direct <img> element
    image = element if element.name == "img" else element.find("img")

    if image:
        # Standard image
        for attribute in ("src", "data-src", "data-lazy-src", "data-original",):
            value = image.get(attribute)

            if value:
                return absolute_url(value, base_url)

        # WordPress/Elementor sometimes uses srcset
        srcset = image.get("srcset")

        if srcset:
            first_image = srcset.split(",")[0].strip().split(" ")[0]

            if first_image:
                return absolute_url(first_image, base_url)

    # CSS background image
    background_url = extract_background_image(element, base_url)

    if background_url:
        return background_url

    # Sometimes the background image is on a parent container.
    parent = element.find_parent()

    if parent:
        background_url = extract_background_image(parent, base_url)

        if background_url:
            return background_url

    return None


def extract_image_alt(element):
    """Extract image alt text."""

    if not element:
        return ""

    image = element if element.name == "img" else element.find("img")

    if image:
        return clean_text(image.get("alt"))

    return ""


def find_heading(soup: BeautifulSoup, patterns: list[str]):
    """
    Find a heading whose text contains one of the supplied patterns.
    """

    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        text = clean_text(heading.get_text(" ", strip=True)).lower()

        for pattern in patterns:
            if pattern.lower() in text:
                return heading

    return None


def find_card_container(element):
    """
    Walk upward until we find an Elementor-style loop/card container.

    Elementor commonly uses classes such as:
        e-loop-item
        elementor-element
        elementor-widget
    """

    if not element:
        return None

    current = element

    for _ in range(8):
        classes = current.get("class", [])

        if "e-loop-item" in classes:
            return current

        if current.name in {"article"}:
            return current

        current = current.parent

        if not current:
            break

    return element


def extract_card_text(card):
    """Extract readable text from a card."""

    return clean_text(card.get_text(" ", strip=True))


# Description
def parse_description(soup: BeautifulSoup):
    """
    Extract the destination introduction.

    The page's first meaningful paragraphs are preferred over
    navigation/footer text.
    """

    # Try the main content area first.
    main = soup.find("main")

    if main:
        paragraphs = main.find_all("p")

        for paragraph in paragraphs:
            text = clean_text(paragraph.get_text(" ", strip=True))

            if len(text) >= 80:
                return text

    # Fallback to the complete document.
    for paragraph in soup.find_all("p"):
        text = clean_text(paragraph.get_text(" ", strip=True))

        if len(text) >= 80:
            return text

    return ""


# Places to Stay
def parse_places_to_stay(soup: BeautifulSoup, base_url: str):
    """
    Extract accommodation/place-to-stay cards.

    The parser searches for the "PLACES TO STAY" section and then
    inspects nearby Elementor loop cards.
    """

    results = []

    heading = find_heading(
        soup,
        [
            "PLACES TO STAY",
            "PLACES TO STAY IN",
        ],
    )

    if not heading:
        return results

    # Find nearby cards.
    container = heading.parent

    for _ in range(6):
        if not container:
            break

        cards = container.select(
            ".e-loop-item, article"
        )

        if cards:
            break

        container = container.parent

    if not cards:
        return results

    seen = set()

    for card in cards:
        text = extract_card_text(card)

        if not text or len(text) < 3:
            continue

        link = card.find("a", href=True)

        name = ""

        # Prefer headings inside the card.
        card_heading = card.find(
            ["h2", "h3", "h4", "h5", "h6"]
        )

        if card_heading:
            name = clean_text(
                card_heading.get_text(" ", strip=True)
            )

        if not name and link:
            name = clean_text(link.get_text(" ", strip=True))

        if not name:
            continue

        # Avoid duplicates.
        key = name.lower()

        if key in seen:
            continue

        seen.add(key)

        results.append(
            {
                "name": name,
                "image": extract_image_url(card, base_url),
                "url": (
                    absolute_url(link.get("href"), base_url)
                    if link
                    else None
                ),
                "description": text,
            }
        )

    return results


# Things to Do
def parse_things_to_do(soup: BeautifulSoup, base_url: str):
    """
    Extract the general "Things to do" cards.

    This is separate from the more structured
    "TOP THINGS TO DO IN ..." section.
    """

    results = []

    heading = find_heading(
        soup,
        [
            "Things to do",
        ],
    )

    if not heading:
        return results

    container = heading.parent

    cards = []

    for _ in range(6):
        if not container:
            break

        cards = container.select(
            ".e-loop-item, article"
        )

        if cards:
            break

        container = container.parent

    seen = set()

    for card in cards:
        card_heading = card.find(
            ["h2", "h3", "h4", "h5", "h6"]
        )

        if not card_heading:
            continue

        name = clean_text(
            card_heading.get_text(" ", strip=True)
        )

        if not name:
            continue

        key = name.lower()

        if key in seen:
            continue

        seen.add(key)

        link = card.find("a", href=True)

        results.append(
            {
                "name": name,
                "description": extract_card_text(card),
                "image": extract_image_url(card, base_url),
                "url": (
                    absolute_url(link.get("href"), base_url)
                    if link
                    else None
                ),
            }
        )

    return results


# Top Things To Do
def parse_top_things_to_do(
    soup: BeautifulSoup,
    base_url: str,
) -> dict:
    """
    Extract the structured:

        TOP THINGS TO DO IN <destination>

    section.

    Expected categories include:

        Nature & Wildlife
        Adventure
        Culture & Heritage
    """

    results = {
        "nature_and_wildlife": [],
        "adventure": [],
        "culture_and_heritage": [],
    }

    heading = find_heading(
        soup,
        [
            "TOP THINGS TO DO IN",
        ],
    )

    if not heading:
        return results

    # Start searching after the main heading.
    current = heading

    category_map = {
        "nature & wildlife": "nature_and_wildlife",
        "nature and wildlife": "nature_and_wildlife",
        "adventure": "adventure",
        "culture & heritage": "culture_and_heritage",
        "culture and heritage": "culture_and_heritage",
    }

    current_category = None
    seen = set()

    # Inspect following headings and cards.
    for element in heading.find_all_next(["h2", "h3", "h4", "h5", "h6", "article"]):
        if element.name in {
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        }:
            heading_text = clean_text(
                element.get_text(" ", strip=True)
            ).lower()

            if heading_text in category_map:
                current_category = category_map[heading_text]

            # Stop when the next major section begins.
            if (
                "trip planner" in heading_text
                and current_category is not None
            ):
                break

            continue

        if element.name == "article":
            card = element

        else:
            card = find_card_container(element)

        if not card or not current_category:
            continue

        card_heading = card.find(
            ["h2", "h3", "h4", "h5", "h6"]
        )

        if not card_heading:
            continue

        name = clean_text(
            card_heading.get_text(" ", strip=True)
        )

        if not name:
            continue

        key = f"{current_category}:{name.lower()}"

        if key in seen:
            continue

        seen.add(key)

        # Try to find a paragraph specifically inside the card.
        paragraph = card.find("p")

        description = (
            clean_text(
                paragraph.get_text(" ", strip=True)
            )
            if paragraph
            else ""
        )

        link = card.find("a", href=True)

        results[current_category].append(
            {
                "name": name,
                "description": description,
                "image": extract_image_url(card, base_url),
                "url": (
                    absolute_url(link.get("href"), base_url)
                    if link
                    else None
                ),
            }
        )

    return results


# Trip Planner
def parse_trip_planner(soup: BeautifulSoup, base_url: str,):
    """
    Extract the destination trip planner.

    The Magical Kenya HTML contains day labels such as:

        Day 1
        Day 2
        Day 3

    followed by the corresponding activity text.
    """

    results = []

    heading = find_heading(
        soup,
        [
            "TRIP PLANNER",
        ],
    )

    if not heading:
        return results

    # Find the nearest useful container.
    container = heading.parent

    for _ in range(6):
        if not container:
            break

        text = clean_text(
            container.get_text(" ", strip=True)
        )

        if "Day 1" in text:
            break

        container = container.parent

    if not container:
        return results

    # Extract text while preserving line breaks where possible.
    raw_text = container.get_text(
        "\n",
        strip=True,
    )

    # Match:
    #
    # Day 1
    # activity
    #
    # Day 2
    # activity

    matches = re.findall(
        r"Day\s+(\d+)\s*(.*?)(?=Day\s+\d+|$)",
        raw_text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    for day_number, content in matches:
        content = clean_text(content)

        if not content:
            continue

        # Remove the section heading and introductory text
        # from the first day if it accidentally gets included.
        content = re.sub(
            r"^.*?TRIP PLANNER",
            "",
            content,
            flags=re.IGNORECASE,
        ).strip()

        if not content:
            continue

        results.append(
            {
                "day": int(day_number),
                "title": content,
                "description": "",
                "image": None,
            }
        )

    return results


# General image extraction

def parse_images(soup: BeautifulSoup, base_url: str):
    """
    Extract useful content images.

    Site-wide assets such as logos and weather icons are filtered out.
    """

    results = []
    seen = set()

    excluded_terms = [
        "logo",
        "weather",
        "icon",
        "favicon",
        "avatar",
        "facebook",
        "instagram",
        "twitter",
        "youtube",
    ]

    # Standard <img> elements

    for image in soup.find_all("img"):
        url = extract_image_url(image, base_url)

        if not url:
            continue

        alt = clean_text(image.get("alt"))

        identifier = f"{url}|{alt}".lower()

        if identifier in seen:
            continue

        lowered = f"{url} {alt}".lower()

        if any(term in lowered for term in excluded_terms):
            continue

        seen.add(identifier)

        results.append(
            {
                "url": url,
                "alt": alt,
                "section": None,
            }
        )

    # CSS background images

    for element in soup.find_all(
        style=True,
    ):
        url = extract_background_image(
            element,
            base_url,
        )

        if not url:
            continue

        identifier = url.lower()

        if identifier in seen:
            continue

        lowered = url.lower()

        if any(term in lowered for term in excluded_terms):
            continue

        seen.add(identifier)

        results.append(
            {
                "url": url,
                "alt": "",
                "section": None,
            }
        )

    return results


# Main parser
def parse_destination_page(html: str, name: str, slug: str, url: str):
    """
    Parse one Magical Kenya destination HTML page.
    """

    soup = BeautifulSoup( html, "html.parser")

    data = {
        "name": name,
        "slug": slug,
        "url": url,
        "description": parse_description(soup),
        "images": parse_images(soup, url),
        "places_to_stay": parse_places_to_stay( soup, url),
        "things_to_do": parse_things_to_do(soup, url),
        "top_things_to_do": parse_top_things_to_do( soup, url),
        "trip_planner": parse_trip_planner(soup, url),
    }

    return data


# Parse all destinations

def parse_all_destinations():
    """Parse all downloaded destination HTML files."""

    all_destinations = []

    for destination in DESTINATIONS:
        name = destination["name"]
        slug = destination["slug"]
        url = destination["url"]

        html_path = RAW_HTML_DIR / f"{slug}.html"

        if not html_path.exists():
            print(f"SKIPPED: {html_path} does not exist")
            continue

        print(f"Parsing: {name}")

        html = html_path.read_text(encoding="utf-8")

        data = parse_destination_page(html=html, name=name, slug=slug, url=url)


        # Save individual destination JSON
        destination_path = (DESTINATIONS_DIR / f"{slug}.json")

        destination_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        all_destinations.append(data)

        print(f"places_to_stay: " f"{len(data['places_to_stay'])}")

        print(f"things_to_do: " f"{len(data['things_to_do'])}")

        print(f"top_things_to_do: " f"{sum(len(v) for v in data['top_things_to_do'].values())}")

        print(f"trip_planner: " f"{len(data['trip_planner'])}")

        print(f"images: " f"{len(data['images'])}")

        print()

    # Save consolidated dataset

    output_path = (PROCESSED_DIR / "destinations.json")

    output_path.write_text(json.dumps(all_destinations, indent=2, ensure_ascii=False,), encoding="utf-8")

    print(f"Saved consolidated dataset: {output_path}")

    return all_destinations


if __name__ == "__main__":
    parse_all_destinations()
