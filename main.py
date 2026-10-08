from app.config import KWS_URL, HEADERS
from src.KWS.KWS import kws_scrape
from src.KWS.Cleaned_kws_Data import kws_clean_data
import pandas as pd
from pathlib import Path
import json
from src.MagicalKenya.Parser import parse_html


BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "Data" / "raw"
PARSED_DIR = BASE_DIR / "Data" /"processed" / "json"

#make dir if not exist
BASE_DIR.mkdir(parents = True, exist_ok = True)
RAW_DIR.mkdir(parents = True, exist_ok = True)
PARSED_DIR.mkdir(parents = True, exist_ok = True)

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