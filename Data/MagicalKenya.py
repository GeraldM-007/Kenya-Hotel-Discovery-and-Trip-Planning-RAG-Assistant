import requests 
from bs4 import BeautifulSoup
from app.config import DESTINATIONS, HEADERS

destinations = DESTINATIONS

headers = HEADERS

def extract_data(destinations):
    
    for destination in destinations:
        
        url = destination["url"]
        
        response = requests.get(url, headers = headers, timeout = 30)
        
        response.raise_for_status()
        
        #parse the html into python objects
        soup = BeautifulSoup(response.text, "html.parser")
        
        #remove dynamic/unwanted elements
        for tag in soup(["script", "style", "noscript", "svg", "footer"]):
            
            tag.decompose()
            
        #Get the title of the page
        title = [t.get_text(" ", strip = True) for t in soup.find_all("h1") if t.get_text(strip = True)]
        print(title)

        #Get paragraphs in the page
        paragraphs = [p.get_text(" ", strip = True) for p in soup.find_all("p") if p.get_text(strip = True)]
        print(paragraphs)
        
        #Get all the headings in the page
        headings = [h.get_text(" ", strip = True) for h in soup.find_all(["h1","h2","h3","h4"]) if h.get_text(strip = True)]
        print(headings)
        
    return response.raise_for_status()
    
data = extract_data(destinations)
print("Raise for response was: ", data)
