from pathlib import Path
from bs4 import BeautifulSoup
import json
import hashlib

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "TravelAfricaRAGProject" / "Data" / "raw"
PARSED_DIR = BASE_DIR / "TravelAfricaRAGProject" / "tests" / "data" /"processed" / "json"

#make dir if not exist
BASE_DIR.mkdir(parents = True, exist_ok = True)
RAW_DIR.mkdir(parents = True, exist_ok = True)
PARSED_DIR.mkdir(parents = True, exist_ok = True)

#create a deterministic file ID from the filename using sha256 algorithm
def create_document_id(filename: str):
    #turn filename into bytes, calculate hash and convert into hexadecimal string
    return hashlib.sha256(filename.encode()).hexdigest()[:16]

#Read downloaded HTML files
def parse_html(file_path: Path):
    #load the entire file into a python string, decoding in utf-8 while ignoring invalid utf-8 characters
    html = file_path.read_text(encoding = "utf-8", errors = "ignore")
    
    #Beautifulsoup turns the raw html string into a navigatable html tree
    #lxml is the html parser in use
    soup = BeautifulSoup(html, "lxml")
        
    #Extract metadata from the read text
    title = None #safe default incase html doesn't contain a title
    
    if soup.title:
        title = soup.title.get_text(strip = True)
        
        #find a meta element whose 'name' attribute equals to'description'
        description_tag = soup.find("meta", attrs = {"name": "description"})
        
        #Extract the description content
        description = (description_tag.get("content") if description_tag else None)
        
        #canonical tag contains the prefered/original URL of the webpage
        #Find the link element with canonical naming
        canonical_tag = soup.find("link", attrs = {"rel": "canonical"})
        
        #Extract the url
        source_url = (canonical_tag.get("href") if canonical_tag else None)
        
    #Extract content from article/main or the body its self
    content = ( soup.find('div', attrs={"data-elementor-type": "wp-post"}) or soup.find("article") or soup.find("main") or soup.body or soup)
    
    #Remove unwanted content
    for tag in content.find_all(["script", "style", "noscript", "svg", "iframe", "nav", "footer"]):
        tag.decompose()   #decompose completely removes a HTML element and its contents from BeautifulSoup tree

    #Extract useful sections
    sections = []
    
    current_heading = None
    current_text = []
    
    for element in content.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        # Extract text from the current HTML element.
        # " " puts spaces between nested elements.
        text = element.get_text(" ", strip=True)
        
        # Ignore empty elements
        if not text:
            continue
        
        # If we encounter a heading, a new section is starting
        if element.name in ["h1", "h2", "h3", "h4"]:
            # Save the previous section first
            if current_text:
                sections.append({"heading": current_heading, "text": "\n".join(current_text)})
        
            # Start the new section
            current_heading = text
            current_text = []
        
        else:
            # <p> and <li> belong to the current section
            current_text.append(text)
    
    
    #Full cleaned text from the document
    full_text = "\n\n".join(section["text"] for section in sections)
    
    #The final document
    document = {
        "document_id": create_document_id(file_path.name),
        "source_file": file_path.name,
        "source_url": source_url,
        "title": title,
        "description": description,
        "content_type": "html",
        "text": full_text,
        "sections": sections
    }
    
    return document

#Move this to main.py file. It is only here for testing purposes only
def main():
    
    for file_path in RAW_DIR.glob("*.html"):
        
        print(f"Parsing: {file_path}")
        
        document = parse_html(file_path)
        
        output_file = (PARSED_DIR / f"{file_path.stem}.json")
        
        with output_file.open("w", encoding = "utf-8") as f:
            json.dump(document, f, ensure_ascii = False, indent = 2)
            
        print(f"Saved: {output_file}")

if __name__ == "__main__":
    main()
    
