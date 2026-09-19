import time
from pathlib import Path
import requests
from app.config import HEADERS, DESTINATIONS

#define the base directory (where the program is executing from)
BASE_DIR = Path(__file__).resolve().parents[2]

#define where the downloaded raw html files will be stored
RAW_HTML_DIR = BASE_DIR / "TravelAfricaRAGProject" / "Data" / "raw"

#make the request and download the html page
def download_page(url: str):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()
    
    #response contains the HTML python string
    return response.text

#save the raw html to the directory
def save_html(slug: str, html: str):
    #create the Data / raw dir if it does not exist, create the parents too if need be 
    RAW_HTML_DIR.mkdir(parents=True, exist_ok=True)
    
    #create the file name
    output_path = RAW_HTML_DIR / f"{slug}.html"
    
    #write the downloaded html into the file
    output_path.write_text(
        html,
        encoding="utf-8",
    )
    
    #return the location of the saved file
    return output_path

#download and scrape all destination pages
def scrape_destinations():
    
    #counting the total number of destinations to scrape
    print(f"Destinations to scrape: {len(DESTINATIONS)}")
    
    for destination in DESTINATIONS:
        name = destination["name"]
        slug = destination["slug"]
        url = destination["url"]
        
        print(f"Scraping: {name}")
        print(f"URL: {url}")
        
        try:
            raw_html_page = download_page(url)
            output_path = save_html(slug, raw_html_page)

            print(f"Saved: {output_path}")
            print(f"HTML size: {len(raw_html_page):,} characters") #to check if you actually downloaed something
            print()
            
        except requests.RequestException as error:
            print(f"ERROR: Could not scrape {name}")
            print(error)
            print()

        # Pauses the program for 1 second before scrapping the next page. Be polite to the server.
        time.sleep(1)


if __name__ == "__main__":
    scrape_destinations()