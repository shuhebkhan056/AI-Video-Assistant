import hashlib
import os 
from langchain_chroma import Chroma 
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

CHROMA_DIR = "vector_db"
COLLECTION_NAME = "meeting_transcript"
EMBEDDING_MODEL  = "all-MiniLM-L6-v2"

def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name = EMBEDDING_MODEL,
        model_kwargs = {"device" : 'cpu'}
    )

def build_vector_store(transcript : str)->Chroma:
    print("Building vector Store")
    if not transcript or not transcript.strip():
        raise ValueError("Cannot build meeting search: the transcript is empty. Run transcription first.")

    # Keep each meeting in its own persistent collection. Reusing one fixed
    # collection causes later meetings to retrieve chunks from earlier ones.
    transcript_id = hashlib.sha256(transcript.encode("utf-8")).hexdigest()[:16]
    collection_name = f"meeting_{transcript_id}"

    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 500,
        chunk_overlap = 50
    )
    chunks = [chunk for chunk in splitter.split_text(transcript) if chunk.strip()]
    if not chunks:
        raise ValueError("Cannot build meeting search: the transcript contains no searchable text.")

    docs = [
        Document(page_content=chunk, metadata = {'chunk_index' : i})
        for i,chunk in enumerate(chunks)
    ]

    embeddings = get_embeddings()
    vector_store = Chroma.from_documents(
        documents= docs,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=CHROMA_DIR
    )

    return vector_store



def load_vector_store() ->Chroma:
    embeddings = get_embeddings()
    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function= embeddings,
        persist_directory=CHROMA_DIR
    )

    return vector_store

def get_retriever(vector_store : Chroma, k :int = 4):
    return vector_store.as_retriever(
        search_type = 'similarity',
        search_kwargs = {"k":k}
    )


