import os
import pandas as pd
import numpy as np
import faiss
import nltk
import re
import logging
from nltk.tokenize import sent_tokenize
from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv
from typing import Tuple, List
from .rag_engine import RAGEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Download required NLTK data
nltk.download("punkt")
nltk.download("punkt_tab")

class GeneralChatbot:
    def __init__(self):
        logger.info("Initializing GeneralChatbot with enhanced RAG")
        
        # Load and preprocess data
        self.ipc_df = pd.read_csv("data/ipc_sections.csv")
        self.constitution_df = pd.read_csv("data/constitutional_dataset.csv")
        self.ipc_df.dropna(subset=["Description"], inplace=True)
        self.constitution_df.dropna(subset=["article_desc"], inplace=True)
        
        # Initialize RAG engine with persistence
        self.rag_engine = RAGEngine(
            model_name="all-MiniLM-L6-v2",
            chunk_size=500,
            chunk_overlap=50,
            storage_path="vector_store/general"
        )
        
        # Try to load existing index, otherwise create new one
        if not self.rag_engine.load_index("legal_knowledge"):
            logger.info("Creating new vector index from legal data")
            self.texts, self.sources = self._preprocess_data()
            self._build_rag_index()
            self.rag_engine.save_index("legal_knowledge")
        else:
            logger.info("Loaded existing vector index")
            self.texts, self.sources = self._preprocess_data()
        
        # Keep legacy model for compatibility
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.embeddings = None
        self.index = None
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Initialize QA chain with enhanced prompt template
        prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template="""
You are a legal expert specializing in Indian Constitutional Law and the Indian Penal Code. Given the legal text below and the user's question, provide a **concise**, **clear**, and **direct** response.

**Legal Text:**
{context}

**Question:**
{question}

**Instructions:**
1. Provide a response that is **brief** and **to the point**
2. Focus only on the **key points** from the legal text
3. Keep the answer **concise** (2-3 sentences)
4. Use **clear legal terminology**
5. Cite **relevant sections** if applicable
6. Format the response with:
   - Main answer first
   - Supporting details (if needed)
   - Source reference

**Response Format:**
✅ Answer: [Your concise answer here]
📚 Source: [Relevant section/article reference]
            """
        )
        self.qa_chain = LLMChain(llm=self.llm, prompt=prompt_template)

    def _preprocess_data(self):
        # Process constitutional data
        constitution_data = []
        for _, row in self.constitution_df.iterrows():
            if "article_desc" in row and row["article_desc"]:
                # Keep the entire article text together
                constitution_data.append({
                    "source": row["article_id"],
                    "text": str(row["article_desc"]).strip()
                })

        # Process IPC data
        ipc_data = []
        for _, row in self.ipc_df.iterrows():
            if "Description" in row and row["Description"]:
                # Keep the entire section description together
                ipc_data.append({
                    "source": f"Section {row['Section']}",
                    "text": str(row["Description"]).strip()
                })

        # Combine the datasets
        all_data = constitution_data + ipc_data
        texts = [item["text"] for item in all_data]
        sources = [item["source"] for item in all_data]
        
        logger.info(f"Loaded {len(constitution_data)} constitutional articles and {len(ipc_data)} IPC sections")
        return texts, sources

    def _build_rag_index(self):
        """Build RAG index from preprocessed data."""
        logger.info("Building RAG index from legal data")
        
        # Process constitutional data
        constitution_docs = []
        for _, row in self.constitution_df.iterrows():
            if "article_desc" in row and row["article_desc"]:
                constitution_docs.append({
                    'text': str(row["article_desc"]).strip(),
                    'metadata': {
                        'source': row["article_id"],
                        'type': 'constitutional'
                    }
                })
        
        # Add constitutional data to RAG
        if constitution_docs:
            self.rag_engine.add_documents(constitution_docs, source_type="constitution")
        
        # Process IPC data
        ipc_docs = []
        for _, row in self.ipc_df.iterrows():
            if "Description" in row and row["Description"]:
                ipc_docs.append({
                    'text': str(row["Description"]).strip(),
                    'metadata': {
                        'source': f"Section {row['Section']}",
                        'type': 'ipc',
                        'section': row['Section']
                    }
                })
        
        # Add IPC data to RAG
        if ipc_docs:
            self.rag_engine.add_documents(ipc_docs, source_type="ipc")
        
        logger.info("RAG index built successfully")

    def _create_embeddings(self):
        """Legacy method for backward compatibility."""
        if self.embeddings is None:
            embeddings = self.model.encode(
                self.texts,
                convert_to_tensor=False,
                show_progress_bar=True
            )
            self.embeddings = np.array(embeddings).astype("float32")
        return self.embeddings

    def _create_index(self):
        """Legacy method for backward compatibility."""
        if self.index is None and self.embeddings is not None:
            index = faiss.IndexFlatL2(self.embeddings.shape[1])
            index.add(self.embeddings)
            self.index = index
        return self.index

    def is_legal_question(self, question):
        legal_keywords = [
            "section", "act", "law", "legal", "ipc", "article", "constitution", "penal",
            "rights", "duty", "court", "crime", "criminal", "civil", "suit", "offence",
            "offense", "trial", "judge", "judgment", "justice", "bail", "warrant", "arrest",
            "contract", "tort", "property", "liability", "penalty", "clause",
            "code of criminal procedure", "evidence", "procedure", "appeal", "jurisdiction",
            "tribunal", "bar council", "advocate", "litigation", "enactment", "rule",
            "regulation", "verdict", "plaintiff", "defendant", "writ", "habeas corpus",
            "fundamental rights", "directive principles", "preamble", "murder"
        ]
        return any(word.lower() in question.lower() for word in legal_keywords)

    def get_best_match(self, question: str) -> Tuple[str, List[str]]:
        """Find the best matching text and its source using enhanced RAG."""
        # First check for specific article references
        article_match = re.search(r'article\s*(\d+[a-zA-Z]*)', question.lower())
        if article_match:
            article_num = article_match.group(1)
            # Use RAG engine with filter
            results = self.rag_engine.search(
                question,
                k=3,
                filter_by={'source_type': 'constitution'}
            )
            
            # Look for exact article match
            for result in results:
                if f"Article {article_num}" in result.get('metadata', {}).get('source', ''):
                    return result['text'], [result['metadata']['source']]
            
            # Fallback to legacy search
            for text, source in zip(self.texts, self.sources):
                if f"Article {article_num}" in text:
                    return text, [source]

        # Check for specific section references
        section_match = re.search(r'section\s*(\d+[a-zA-Z]*)', question.lower())
        if section_match:
            section_num = section_match.group(1)
            # Use RAG engine with filter
            results = self.rag_engine.search(
                question,
                k=3,
                filter_by={'source_type': 'ipc'}
            )
            
            # Look for exact section match
            for result in results:
                if f"Section {section_num}" in result.get('metadata', {}).get('source', ''):
                    return result['text'], [result['metadata']['source']]
            
            # Fallback to legacy search
            for text, source in zip(self.texts, self.sources):
                if f"Section {section_num}" in text:
                    return text, [source]

        # Use RAG engine for semantic search
        context, sources = self.rag_engine.get_context(question, k=1)
        
        if context and context != "No relevant information found.":
            source_list = [s.get('metadata', {}).get('source', 'Unknown') for s in sources]
            return context, source_list
        
        return "No relevant information found.", ["No source"]

    def get_response(self, message: str) -> str:
        """Get a response from the chatbot."""
        try:
            # Convert message to lowercase for better matching
            message = message.lower().strip()
            
            # Handle greetings
            if any(greeting in message for greeting in ['hey', 'hi', 'hello', 'greetings']):
                return "Hello! How can I help you with legal information today?"
            
            # Handle thank you messages
            if any(thanks in message for thanks in ['thank', 'thanks', 'appreciate']):
                return "You're welcome! Let me know if you need anything else."
            
            # Handle goodbyes
            if any(bye in message for bye in ['bye', 'goodbye', 'see you']):
                return "Goodbye! Feel free to return if you have more questions."
            
            # Check if the question is legal-related
            if not self.is_legal_question(message):
                return "I can only answer questions about Indian Constitutional Law and IPC. Please ask a legal question."
            
            # Get the best matching text and its source
            context, sources = self.get_best_match(message)
            
            # Generate response using the context
            response = self.qa_chain.run({"context": context, "question": message})
            
            # Clean up the response (remove HTML tags and extra whitespace)
            response = re.sub(r'<[^>]+>', '', response)  # Remove HTML tags
            response = re.sub(r'\s+', ' ', response)     # Remove extra whitespace
            response = response.strip()
            
            # If response is too long, summarize it
            if len(response) > 200:
                response = self.summarize_response(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting response: {str(e)}")
            return "I apologize, but I'm having trouble processing your request. Could you please rephrase it?"

    def summarize_response(self, response: str) -> str:
        """Summarize a long response to be more concise."""
        try:
            # Split into sentences
            sentences = response.split('. ')
            
            # Keep first 2-3 sentences if they're informative
            if len(sentences) > 3:
                summary = '. '.join(sentences[:3])
                if not summary.endswith('.'):
                    summary += '.'
                return summary
            
            return response
            
        except Exception as e:
            logger.error(f"Error summarizing response: {str(e)}")
            return response 