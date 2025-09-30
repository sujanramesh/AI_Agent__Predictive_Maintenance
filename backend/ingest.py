# ingest.py
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings

load_dotenv()

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
VECTORSTORE_DIR = os.path.join(BASE_DIR, "..", "vectorstore")

# Load embeddings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

def create_or_update_vectorstore():
    vectorstore = None

    # If vectorstore exists, load it; otherwise create new
    if os.path.exists(VECTORSTORE_DIR):
        print("📂 Loading existing vector store...")
        vectorstore = FAISS.load_local(VECTORSTORE_DIR, embeddings, allow_dangerous_deserialization=True)
    else:
        print("📂 Creating new vector store...")
    
    # Scan all PDFs in DATA_DIR
    for filename in os.listdir(DATA_DIR):
        if filename.lower().endswith(".pdf"):
            filepath = os.path.join(DATA_DIR, filename)
            print(f"📄 Processing {filename}...")
            
            loader = PyPDFLoader(filepath)
            documents = loader.load()
            
            # Split documents into chunks
            splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            chunks = splitter.split_documents(documents)
            
            # Create or update vectorstore
            if vectorstore is None:
                vectorstore = FAISS.from_documents(chunks, embeddings)
            else:
                vectorstore.add_documents(chunks)
    
    if vectorstore:
        vectorstore.save_local(VECTORSTORE_DIR)
        print("✅ Vector store updated successfully!")
    else:
        print("⚠️ No PDFs found to process.")

if __name__ == "__main__":
    create_or_update_vectorstore()
