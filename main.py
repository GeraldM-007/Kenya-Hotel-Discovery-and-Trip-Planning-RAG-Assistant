from config import KWS_URL, headers, pages
from Data.RawData import kws_scrape
from Data.CleanedData import kws_clean_data
import pandas as pd

def main():
    
    kws_all_data = kws_scrape(KWS_URL, pages, headers)
    
    df1 = kws_clean_data(kws_all_data)
    
    
    
    
if __name__ == "__main__":
    main()