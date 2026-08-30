import os
os.environ["HF_HUB_OFFLINE"] = "1"
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

def ingest_documents():
    print("Configuring Embedding Model (HuggingFace/BAAI)...")
    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
    Settings.embed_model = embed_model
    Settings.llm = None 

    print("Loading Documents...")
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    guidelines_file = os.path.join(base_dir, "data", "guidelines", "icmr_guidelines.txt")
    documents = SimpleDirectoryReader(input_files=[guidelines_file]).load_data()

    print("Parsing Nodes...")
    parser = SentenceSplitter(chunk_size=256, chunk_overlap=32)
    nodes = parser.get_nodes_from_documents(documents)

    print("Indexing into SimpleVectorStore...")
    index = VectorStoreIndex(nodes, embed_model=embed_model)
    
    print("Persisting to disk...")
    persist_dir = os.path.join(base_dir, "var", "storage")
    os.makedirs(persist_dir, exist_ok=True)
    index.storage_context.persist(persist_dir=persist_dir)
    print(f"Ingestion Complete! Data saved to {persist_dir}")

if __name__ == "__main__":
    ingest_documents()
