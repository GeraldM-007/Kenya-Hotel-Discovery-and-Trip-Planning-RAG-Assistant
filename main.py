from app.config import KWS_URL, HEADERS
from src.KWS.KWS import kws_scrape
from src.KWS.Cleaned_kws_Data import kws_clean_data
import pandas as pd
from pathlib import Path
import json
from src.MagicalKenya.Parser import parse_html
from src.rag.chunking import load_documents, create_document_chunks, save_chunks
from src.rag.vector_store import load_chunks, SentenceTransformer, create_collection, store_vectors

#Base DIR for all files
BASE_DIR = Path(__file__).resolve().parent

#Directories used in parsing
RAW_DIR = BASE_DIR / "Data" / "raw"
PARSED_DIR = BASE_DIR / "Data" /"processed" / "json"
#make dir if not exist
BASE_DIR.mkdir(parents = True, exist_ok = True)
RAW_DIR.mkdir(parents = True, exist_ok = True)
PARSED_DIR.mkdir(parents = True, exist_ok = True)

#Directories used in chunking
JSON_DIR = BASE_DIR / "Data" / "processed" / "json"
OUTPUT_PATH = BASE_DIR / "Data" / "processed" / "chunks" / "chunks.jsonl"

#Directories and variables used on vectore_store
CHUNKS_PATH = BASE_DIR/ "Data" / "processed" / "chunks" / "chunks.jsonl" 
VECTOR_DB_DIR = BASE_DIR / "Data" / "vector-store"

COLLECTION_NAME = "travel_africa_kenya_destinations"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def main():
    
    #Parsing downloaded html files into json
    for file_path in RAW_DIR.glob("*.html"):
        
        print(f"Parsing: {file_path}")
        
        document = parse_html(file_path)
        
        output_file = (PARSED_DIR / f"{file_path.stem}.json")
        
        with output_file.open("w", encoding = "utf-8") as f:
            json.dump(document, f, ensure_ascii = False, indent = 2)
            
        print(f"Saved: {output_file}")  
        
    #Chunking parsed json files into word and semantic based searching 
    documents = load_documents(JSON_DIR)
    
    all_chunks = []
    
    for document in documents:
        chunks = create_document_chunks(document, chunk_size=300, overlap=50)
        
        all_chunks.extend(chunks)
    
    save_chunks(all_chunks, OUTPUT_PATH)
    
    print(f"Documents processed: {len(documents)}")
    print(f"Chunks created: {len(all_chunks)}")
    print(f"saved to: {OUTPUT_PATH}")
    
    #STORING CREATED CHUNKS INTO A VECTORDB AND DEFINING HOW TO SEARCH THE DATABASE
    chunks = load_chunks(CHUNKS_PATH)
    if not chunks:
        print(f"No chunks found in {CHUNKS_PATH}: Nothing to store")
        return
    
    model = SentenceTransformer(EMBEDDING_MODEL)
    collection = create_collection(VECTOR_DB_DIR, COLLECTION_NAME)
    count = store_vectors(chunks, collection, model)
    
    print(f"chunks processed: {count}")
    print(f"Vectors in collection: {collection.count()}")
    print(f"ChromaDB location {VECTOR_DB_DIR}")
    
if __name__ == "__main__":
    main()