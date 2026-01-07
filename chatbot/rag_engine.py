"""
RAG (Retrieval Augmented Generation) Engine for ArguLex
This module provides a comprehensive RAG system with vector storage,
document processing, and semantic search capabilities.
"""

import os
import json
import logging
import pickle
import numpy as np
import faiss
from typing import List, Dict, Tuple, Optional
from sentence_transformers import SentenceTransformer
from datetime import datetime
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGEngine:
    """
    A comprehensive RAG engine that handles:
    - Document chunking with overlap
    - Vector embeddings generation
    - FAISS indexing for fast retrieval
    - Semantic search
    - Persistent storage
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        storage_path: str = "vector_store"
    ):
        """
        Initialize the RAG engine.
        
        Args:
            model_name: Name of the sentence transformer model
            chunk_size: Size of text chunks in characters
            chunk_overlap: Overlap between chunks in characters
            storage_path: Path to store vector indices and metadata
        """
        logger.info(f"Initializing RAG Engine with model: {model_name}")
        
        self.model = SentenceTransformer(model_name)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.storage_path = storage_path
        
        # Create storage directory if it doesn't exist
        os.makedirs(storage_path, exist_ok=True)
        
        # Initialize empty data structures
        self.index: Optional[faiss.Index] = None
        self.documents: List[Dict] = []
        self.embeddings: Optional[np.ndarray] = None
        
        logger.info("RAG Engine initialized successfully")
    
    def chunk_text(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None
    ) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Text to chunk
            chunk_size: Override default chunk size
            overlap: Override default overlap
            
        Returns:
            List of text chunks
        """
        chunk_size = chunk_size or self.chunk_size
        overlap = overlap or self.chunk_overlap
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            # Get chunk
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundary
            if end < text_length:
                # Look for sentence endings
                last_period = chunk.rfind('. ')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > chunk_size * 0.5:  # Only break if past halfway
                    chunk = chunk[:break_point + 1]
                    end = start + break_point + 1
            
            chunks.append(chunk.strip())
            start = end - overlap if end < text_length else end
        
        logger.info(f"Split text into {len(chunks)} chunks")
        return chunks
    
    def add_documents(
        self,
        documents: List[Dict],
        source_type: str = "general"
    ) -> None:
        """
        Add documents to the RAG system.
        
        Args:
            documents: List of documents with 'text' and 'metadata' fields
            source_type: Type of source (e.g., 'ipc', 'constitution', 'pdf')
        """
        logger.info(f"Adding {len(documents)} documents of type: {source_type}")
        
        # Process each document
        processed_docs = []
        texts_to_embed = []
        
        for doc in documents:
            text = doc.get('text', '')
            metadata = doc.get('metadata', {})
            
            # Chunk the document
            chunks = self.chunk_text(text)
            
            for i, chunk in enumerate(chunks):
                processed_doc = {
                    'text': chunk,
                    'source_type': source_type,
                    'chunk_id': i,
                    'metadata': metadata,
                    'timestamp': datetime.now().isoformat()
                }
                processed_docs.append(processed_doc)
                texts_to_embed.append(chunk)
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(texts_to_embed)} chunks")
        new_embeddings = self.model.encode(
            texts_to_embed,
            convert_to_tensor=False,
            show_progress_bar=True
        )
        new_embeddings = np.array(new_embeddings).astype('float32')
        
        # Update or create index
        if self.index is None:
            # Create new index
            dimension = new_embeddings.shape[1]
            self.index = faiss.IndexFlatL2(dimension)
            self.embeddings = new_embeddings
            self.documents = processed_docs
        else:
            # Add to existing index
            self.embeddings = np.vstack([self.embeddings, new_embeddings])
            self.documents.extend(processed_docs)
        
        # Add embeddings to index
        self.index.add(new_embeddings)
        
        logger.info(f"Successfully added {len(processed_docs)} document chunks")
        logger.info(f"Total documents in index: {len(self.documents)}")
    
    def search(
        self,
        query: str,
        k: int = 5,
        filter_by: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for relevant documents using semantic similarity.
        
        Args:
            query: Search query
            k: Number of results to return
            filter_by: Optional filters (e.g., {'source_type': 'ipc'})
            
        Returns:
            List of relevant documents with scores
        """
        if self.index is None or len(self.documents) == 0:
            logger.warning("No documents in index")
            return []
        
        # Generate query embedding
        query_embedding = self.model.encode([query], convert_to_tensor=False)
        query_embedding = np.array(query_embedding).astype('float32')
        
        # Search
        distances, indices = self.index.search(query_embedding, min(k * 2, len(self.documents)))
        
        # Get results
        results = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx < len(self.documents):
                doc = self.documents[idx].copy()
                doc['score'] = float(1 / (1 + distance))  # Convert distance to similarity score
                
                # Apply filters
                if filter_by:
                    match = all(doc.get(key) == value for key, value in filter_by.items())
                    if not match:
                        continue
                
                results.append(doc)
                
                if len(results) >= k:
                    break
        
        logger.info(f"Found {len(results)} relevant documents")
        return results
    
    def get_context(
        self,
        query: str,
        k: int = 3,
        filter_by: Optional[Dict] = None
    ) -> Tuple[str, List[Dict]]:
        """
        Get context for a query by retrieving and combining relevant documents.
        
        Args:
            query: Search query
            k: Number of documents to retrieve
            filter_by: Optional filters
            
        Returns:
            Tuple of (combined context string, list of source documents)
        """
        results = self.search(query, k=k, filter_by=filter_by)
        
        if not results:
            return "No relevant information found.", []
        
        # Combine contexts
        context_parts = []
        sources = []
        
        for i, result in enumerate(results):
            text = result['text']
            metadata = result.get('metadata', {})
            source = metadata.get('source', 'Unknown')
            
            context_parts.append(f"[Source {i+1}: {source}]\n{text}")
            sources.append(result)
        
        context = "\n\n".join(context_parts)
        return context, sources
    
    def save_index(self, name: str = "default") -> None:
        """
        Save the FAISS index and metadata to disk.
        
        Args:
            name: Name for the saved index
        """
        if self.index is None:
            logger.warning("No index to save")
            return
        
        index_path = os.path.join(self.storage_path, f"{name}_index.faiss")
        docs_path = os.path.join(self.storage_path, f"{name}_docs.pkl")
        embeddings_path = os.path.join(self.storage_path, f"{name}_embeddings.npy")
        
        # Save FAISS index
        faiss.write_index(self.index, index_path)
        
        # Save documents
        with open(docs_path, 'wb') as f:
            pickle.dump(self.documents, f)
        
        # Save embeddings
        np.save(embeddings_path, self.embeddings)
        
        logger.info(f"Saved index '{name}' to {self.storage_path}")
    
    def load_index(self, name: str = "default") -> bool:
        """
        Load a FAISS index and metadata from disk.
        
        Args:
            name: Name of the saved index
            
        Returns:
            True if successful, False otherwise
        """
        index_path = os.path.join(self.storage_path, f"{name}_index.faiss")
        docs_path = os.path.join(self.storage_path, f"{name}_docs.pkl")
        embeddings_path = os.path.join(self.storage_path, f"{name}_embeddings.npy")
        
        if not all(os.path.exists(p) for p in [index_path, docs_path, embeddings_path]):
            logger.warning(f"Index '{name}' not found")
            return False
        
        try:
            # Load FAISS index
            self.index = faiss.read_index(index_path)
            
            # Load documents
            with open(docs_path, 'rb') as f:
                self.documents = pickle.load(f)
            
            # Load embeddings
            self.embeddings = np.load(embeddings_path)
            
            logger.info(f"Loaded index '{name}' with {len(self.documents)} documents")
            return True
        except Exception as e:
            logger.error(f"Error loading index: {str(e)}")
            return False
    
    def clear_index(self) -> None:
        """Clear the current index and all documents."""
        self.index = None
        self.documents = []
        self.embeddings = None
        logger.info("Cleared index")
    
    def get_stats(self) -> Dict:
        """
        Get statistics about the RAG system.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'total_documents': len(self.documents),
            'index_size': self.index.ntotal if self.index else 0,
            'model_name': self.model.get_sentence_embedding_dimension(),
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap
        }


class PDFRAGEngine(RAGEngine):
    """
    Specialized RAG engine for PDF documents with enhanced features.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_pdf = None
        self.pdf_metadata = {}
    
    def process_pdf(
        self,
        pdf_text: str,
        filename: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Process a PDF document and add it to the RAG system.
        
        Args:
            pdf_text: Extracted PDF text
            filename: Name of the PDF file
            metadata: Additional metadata
            
        Returns:
            Session ID for the processed PDF
        """
        session_id = f"pdf_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        pdf_metadata = {
            'filename': filename,
            'session_id': session_id,
            'processed_at': datetime.now().isoformat()
        }
        
        if metadata:
            pdf_metadata.update(metadata)
        
        # Add document to RAG system
        self.add_documents(
            documents=[{
                'text': pdf_text,
                'metadata': pdf_metadata
            }],
            source_type='pdf'
        )
        
        self.current_pdf = session_id
        self.pdf_metadata[session_id] = pdf_metadata
        
        logger.info(f"Processed PDF: {filename} (Session: {session_id})")
        return session_id
    
    def query_pdf(
        self,
        query: str,
        session_id: Optional[str] = None,
        k: int = 3
    ) -> Tuple[str, List[Dict]]:
        """
        Query a specific PDF document.
        
        Args:
            query: Search query
            session_id: PDF session ID (uses current if not specified)
            k: Number of results
            
        Returns:
            Tuple of (context, sources)
        """
        session_id = session_id or self.current_pdf
        
        if not session_id:
            return "No PDF document loaded.", []
        
        # Search with session filter
        filter_by = {
            'source_type': 'pdf',
            'metadata': {'session_id': session_id}
        }
        
        return self.get_context(query, k=k)
