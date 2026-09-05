import requests 
from bs4 import BeautifulSoup
from config import MAGICAL_KENYA_URL, headers

url = MAGICAL_KENYA_URL

def extract_data(url):
    
    response = requests.get(url, headers = headers, timeout = 30)
    
    response.raise_for_status()
    
    #parse the raw html into python objects
    soup = BeautifulSoup(response.text, "html.parser")

    #Remove dynamic/unwanted elements
    for tag in soup(["script", "style", "noscript", "svg", "footer"]):
        tag.decompose()
    
    #Title
    title = soup.find("h1")
    
    #paragraphs
    paragraphs = [p.get_text(" ", strip = True) for p in soup.find_all("p") if p.get_text(strip=True)]
 
    #Headings
    headings = [h.get_text(" ", strip=True) for h in soup.find_all(["h1","h2","h3","h4"]) if h.get_text(strip=True)]
    
    return {
        "url": url,
        "title": title.get_text(" ", strip = True) if title else None,
        "paragraphs": paragraphs,
        "headings": headings
    }
    
data = extract_data(url)

print(data["title"])
print(data["headings"])
print(data["paragraphs"])
