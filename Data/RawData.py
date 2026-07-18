import requests 
from bs4 import BeautifulSoup
from config import KWS_URL, pages, headers

#function to scrap data from kenya wildlife service website
def kws_scrape(KWS_URL, pages, headers):
        
    html_response = requests.get(f"{KWS_URL}", headers=headers, verify=False)
    
    #convert the response from raw html into python objects
    soup = BeautifulSoup(html_response.text, "html.parser")
    
    #store scraped expriences groups in a list
    experiences = []
    
    for card in soup.select("a.fusion-column-anchor"):
        
        b = card.find_next("b") #b is the html tag containing each experience name
        
        #if not b tag found proceed, do not break 
        if not b:
            continue
        
        experiences.append(
            {
                "title": b.get_text(" ", strip=True),
                "experience_link": card["href"]
            }
        )
    
    all_data=[]
    
    for experience in experiences:
        
        title = experience["title"]
        url = experience["experience_link"]
        
        response = requests.get(url, headers=headers, verify=False)
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        parks = []
        
        for heading in soup.select("h4 a"):
            
            parks.append({
                "park_name": heading.get_text(strip=True),
                "park_link": heading["href"]
            })
            
            all_data.append({
                "experience": title,
                "parks": parks
            })
    

