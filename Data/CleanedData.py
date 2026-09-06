import pandas as pd
from Data.KWS import kws_scrape

def kws_clean_data(kws_all_data):
    
    df1 = pd.DataFrame(kws_all_data)
    
    print(df1.head())
    
