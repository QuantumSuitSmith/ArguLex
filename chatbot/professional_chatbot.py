import os
import re
import tempfile
import fitz
import pandas as pd
import numpy as np
import nltk
import faiss
import logging
from datetime import datetime
from nltk.tokenize import sent_tokenize
from sentence_transformers import SentenceTransformer
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from typing import Tuple, List, Dict, Optional
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('professional_chatbot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Download required NLTK data
nltk.download("punkt")
nltk.download("punkt_tab")

class ProfessionalChatbot:
    def __init__(self):
        logger.info("Initializing ProfessionalChatbot")
        try:
            # Initialize OpenAI client for general chat
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            # Initialize models for PDF analysis
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
            
            # Initialize QA chain with enhanced prompt
            self.qa_prompt = PromptTemplate(
                input_variables=["context", "question", "chat_history"],
                template="""You are a legal expert. Given the legal text below, chat history, and the user's question, provide a precise and accurate legal answer:

Chat History:
{chat_history}

Legal Text:
{context}

Question:
{question}

Instructions:
1. Be direct and concise
2. Focus on the key points
3. Use clear legal terminology
4. Cite relevant sections if applicable
5. Keep the answer brief (2-3 sentences)
6. Consider the chat history for context
7. If the question is unclear, ask for clarification

Answer:"""
            )
            self.qa_chain = LLMChain(llm=self.llm, prompt=self.qa_prompt)
            
            # Initialize chat history and document context
            self.chat_history = []
            self.document_context = None
            self.document_embeddings = None
            self.document_chunks = None
            
            logger.info("ProfessionalChatbot initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing ProfessionalChatbot: {str(e)}")
            raise

    def split_into_sentences(self, text):
        """Split text into readable sentences."""
        return re.split(r'(?<=[.!?])\s+', text.strip())

    def chunk_text(self, text, max_chars=3000):
        """Break full PDF into manageable chunks."""
        lines = text.splitlines()
        chunks, current_chunk = [], ""
        for line in lines:
            if len(current_chunk) + len(line) < max_chars:
                current_chunk += line + "\n"
            else:
                chunks.append(current_chunk)
                current_chunk = line + "\n"
        if current_chunk:
            chunks.append(current_chunk)
        return chunks

    def handle_upload(self, file) -> Tuple[str, Optional[str], Optional[str]]:
        """Handle document upload and analysis with enhanced error handling and logging."""
        logger.info(f"Handling file upload: {file.filename if file else 'No file'}")
        try:
            if not file or not file.filename:
                logger.warning("No file uploaded")
                return "❌ No file uploaded", None, None

            if not file.filename.lower().endswith('.pdf'):
                logger.warning(f"Invalid file type: {file.filename}")
                return "❌ Only PDF files are supported", None, None

            # Save the file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                file.save(tmp.name)
                tmp_path = tmp.name
                logger.info(f"File saved temporarily at: {tmp_path}")

            try:
                # Validate PDF
                doc = fitz.open(tmp_path)
                if doc.page_count == 0:
                    logger.error("PDF file is empty")
                    return "❌ The PDF file appears to be empty", None, None
                
                # Check for text content
                has_text = False
                full_text = ""
                for page in doc:
                    text = page.get_text()
                    if text.strip():
                        has_text = True
                        full_text += text + "\n"
                
                if not has_text:
                    logger.error("PDF contains no text")
                    return "❌ The PDF file appears to be empty or contains no text", None, None
                
                doc.close()

                # Generate report using analyze_pdf with filename
                logger.info("Generating report")
                report = self.analyze_pdf(full_text, file.filename)
                
                if report.startswith("❌ Error"):
                    logger.error(f"Error generating report: {report}")
                    return report, None, None
                
                if not full_text or not full_text.strip():
                    logger.error("No text extracted from PDF")
                    return "❌ Could not extract text from the PDF", None, None

                logger.info("Report generated successfully")
                return report, "success", full_text

            except fitz.fitz.EmptyFileError:
                logger.error("PDF file is empty or corrupted")
                return "❌ The PDF file appears to be empty or corrupted", None, None
            except fitz.fitz.FileDataError:
                logger.error("PDF file is corrupted")
                return "❌ The PDF file appears to be corrupted", None, None
            except Exception as e:
                logger.error(f"Error processing PDF: {str(e)}")
                return f"❌ Error processing PDF: {str(e)}", None, None

            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                        logger.info(f"Temporary file deleted: {tmp_path}")
                    except Exception as e:
                        logger.error(f"Error deleting temporary file: {str(e)}")

        except Exception as e:
            logger.error(f"Error handling upload: {str(e)}")
            return f"❌ Error handling upload: {str(e)}", None, None

    def extract_date_from_pdf(self, doc, case_name):
        """Extract the date of judgment using multiple strategies."""
        try:
            # Try LLM extraction from first 3 pages
            date_text = "\n".join(page.get_text() for page in doc[:3])
            date_prompt = (
                f"Extract the date of judgment from the following case text:\n\n{date_text}\n\n"
                "The date is in the format 'DD Month YYYY'. Return only the date, without any additional text."
            )
            date_response = self.llm.predict(date_prompt)
            date = date_response.strip()
            if date and re.match(r"\d{1,2} \w+ \d{4}", date):
                return date
        except Exception as e:
            logger.warning(f"LLM date extraction failed: {str(e)}")
        # Try regex in first 3 pages
        try:
            date_text = "\n".join(page.get_text() for page in doc[:3])
            date_pattern = r"(\d{1,2}\s+\w+\s+\d{4})"
            date_match = re.search(date_pattern, date_text)
            if date_match:
                return date_match.group(1)
        except Exception as e:
            logger.warning(f"Regex date extraction failed: {str(e)}")
        # Try regex in filename
        try:
            date_pattern = r"(\d{1,2}\s+\w+\s+\d{4})"
            date_match = re.search(date_pattern, case_name)
            if date_match:
                return date_match.group(1)
        except Exception as e:
            logger.warning(f"Filename date extraction failed: {str(e)}")
        return "Unknown"

    def extract_conclusion_from_pdf(self, full_text):
        """Extract the conclusion section from the PDF text."""
        try:
            # Look for common conclusion headers
            conclusion_headers = [
                r"conclusion", r"final decision", r"held", r"ordered", r"therefore", r"order"
            ]
            sentences = self.split_into_sentences(full_text)
            for i, sentence in enumerate(sentences):
                if any(re.search(header, sentence, re.I) for header in conclusion_headers):
                    # Return the found sentence and the next one for context
                    return " ".join(sentences[i:i+2])
            # Fallback: Use LLM to extract conclusion
            conclusion_prompt = (
                f"Extract the conclusion or final order from the following legal case text. "
                f"If not found, say 'Conclusion not available'.\n\nText:\n{full_text[:3000]}"
            )
            conclusion = self.llm.predict(conclusion_prompt).strip()
            return conclusion if conclusion else "Conclusion not available"
        except Exception as e:
            logger.warning(f"Conclusion extraction failed: {str(e)}")
            return "Conclusion not available"

    def generate_report(self, file_path: str) -> Tuple[str, Optional[str], Optional[str]]:
        """Generate a comprehensive report from the PDF with robust metadata extraction."""
        logger.info(f"Generating report for file: {file_path}")
        doc = None
        try:
            filename = os.path.basename(file_path)
            case_name = filename.replace(".pdf", "").replace("*", " ").title()
            clean_filename = filename.replace(".pdf", "").replace(" ", "*").title()
            logger.info(f"Processing case: {case_name}")

            # Load PDF with error checking
            try:
                doc = fitz.open(file_path)
                if doc.page_count == 0:
                    logger.error("PDF file is empty")
                    return "❌ Error: PDF file is empty", None, None
                logger.info(f"PDF loaded successfully with {doc.page_count} pages")
            except Exception as e:
                logger.error(f"Error opening PDF: {str(e)}")
                return f"❌ Error opening PDF: {str(e)}", None, None

            # Extract full text with error handling
            try:
                full_text = "\n".join(page.get_text() for page in doc)
                if not full_text.strip():
                    logger.error("No text extracted from PDF")
                    return "❌ Error: Could not extract text from PDF", None, None
                logger.info(f"Extracted {len(full_text)} characters of text")
            except Exception as e:
                logger.error(f"Error extracting text: {str(e)}")
                return f"❌ Error extracting text: {str(e)}", None, None

            # Extract metadata using modularized methods
            date = self.extract_date_from_pdf(doc, case_name)
            try:
                judge_names = self.extract_judge_from_pdf(doc)
                judges = ", ".join(judge_names) if judge_names else "Unknown"
                logger.info(f"Extracted judges: {judges}")
            except Exception as e:
                logger.warning(f"Error extracting judges: {str(e)}")
                judges = "Unknown"
            try:
                conclusion = self.extract_conclusion_from_pdf(full_text)
            except Exception as e:
                logger.warning(f"Error extracting conclusion: {str(e)}")
                conclusion = "Conclusion not available"

            # Summarize with error handling
            try:
                chunks = self.chunk_text(full_text, max_chars=3000)
                summaries = []
                for i, chunk in enumerate(chunks[:5]):
                    chunk_prompt = f"""Summarize the following legal case text:\n\n{chunk}\n\nReturn 1-2 key sentences only."""
                    chunk_summary = self.llm.predict(chunk_prompt).strip()
                    summaries.append(chunk_summary)
                    logger.info(f"Generated summary for chunk {i+1}")
                summary = "\n".join(summaries)
            except Exception as e:
                logger.warning(f"Error generating summary: {str(e)}")
                summary = "Summary not available"

            # Final report
            report = f"""🧾 Generated Case Report\n\n🏛️ Case Name: {case_name}\n📅 Date: {date}\n👨‍⚖️ Judges: {judges}\n\n🧠 Summary:\n{summary}\n\n✅ Conclusion:\n{conclusion}"""

            # Save report with error handling
            try:
                temp_dir = tempfile.gettempdir()
                report_path = os.path.join(temp_dir, f"{clean_filename}.txt")
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(report)
                logger.info(f"Report saved to: {report_path}")
            except Exception as e:
                logger.error(f"Error saving report: {str(e)}")
                report_path = None

            return report, report_path, full_text

        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            return f"❌ Error: {str(e)}", None, None
        finally:
            if doc:
                try:
                    doc.close()
                    logger.info("PDF document closed")
                except Exception as e:
                    logger.error(f"Error closing PDF document: {str(e)}")

    def extract_judge_from_pdf(self, doc):
        """Extract judge information from the PDF document."""
        judge_patterns = [
            r'Judge\s+([A-Za-z\s\.]+)',
            r'Presiding Judge\s+([A-Za-z\s\.]+)',
            r'Honorable\s+([A-Za-z\s\.]+)',
            r'HON\'?BLE\s+JUSTICE\s+([A-Za-z\s\.]+)',
            r'JUSTICE\s+([A-Za-z\s\.]+)',
            r'HON\'?BLE\s+([A-Za-z\s\.]+)',
            r'THE HON\'?BLE\s+([A-Za-z\s\.]+)',
            r'THE HON\'?BLE\s+JUSTICE\s+([A-Za-z\s\.]+)'
        ]
        
        judge_names = set()
        full_text = ""
        
        # First collect all text
        for page in doc:
            text = page.get_text()
            full_text += text + "\n"
        
        # Search for judge names using patterns
        for pattern in judge_patterns:
            matches = re.finditer(pattern, full_text, re.IGNORECASE)
            for match in matches:
                name = match.group(1).strip()
                # Clean up the name
                name = re.sub(r'\s+', ' ', name)  # Remove extra spaces
                name = re.sub(r'\.+', '.', name)  # Clean up dots
                if len(name.split()) <= 5:  # Avoid long matches
                    judge_names.add(name)
        
        # If no judges found, try looking in first few pages more carefully
        if not judge_names:
            first_pages_text = "\n".join(page.get_text() for page in doc[:3])
            for pattern in judge_patterns:
                matches = re.finditer(pattern, first_pages_text, re.IGNORECASE)
                for match in matches:
                    name = match.group(1).strip()
                    name = re.sub(r'\s+', ' ', name)
                    name = re.sub(r'\.+', '.', name)
                    if len(name.split()) <= 5:
                        judge_names.add(name)
        
        return list(judge_names)

    def query_pdf_after_report(self, question, pdf_text):
        """Query the PDF document after the initial report."""
        try:
            if not pdf_text:
                return "❌ No document context available. Please upload a document first."

            # Check if the question is about judges
            if any(word in question.lower() for word in ['judge', 'judges', 'justice', 'presiding']):
                # Use a specialized prompt for judge-related questions
                judge_prompt = f"""You are a legal expert. Given the legal text below, answer the question about the judge(s) in the case. Be specific and precise:

Legal Text:
{pdf_text}

Question:
{question}

Instructions:
1. If the judge(s) are mentioned, provide their names and titles
2. If no judge is found, say "The judge(s) could not be identified in the document"
3. Be direct and concise
4. Only use information from the document

Answer:"""
                
                response = self.llm.predict(judge_prompt)
                return f"✅ Answer: {response}"
            
            # For other questions, use the standard QA chain
            response = self.qa_chain.run({"context": pdf_text, "question": question})
            return f"✅ Answer: {response}"
            
        except Exception as e:
            print(f"Error in query_pdf_after_report: {str(e)}")
            return f"❌ Error: {str(e)}"

    def get_response(self, message: str, chat_history: List[Dict] = None) -> str:
        """Get a response from the chatbot with enhanced context handling."""
        logger.info(f"Getting response for message: {message[:50]}...")
        try:
            # Add user message to chat history
            if chat_history is None:
                chat_history = []
            chat_history.append({"role": "user", "content": message})
        
            # Check if the question is legal-related
            legal_check_prompt = f"""Analyze if this question is related to legal matters, Indian law, or legal documents:

Question: {message}

Instructions:
1. Return 'LEGAL' if the question is about:
   - Indian law, constitution, or legal system
   - Legal documents, cases, or judgments
   - Legal procedures or rights
   - Legal terminology or concepts
2. Return 'NON_LEGAL' if the question is about:
   - General knowledge
   - Personal matters
   - Non-legal topics
   - Entertainment, sports, or other non-legal subjects

Return only 'LEGAL' or 'NON_LEGAL':"""

            is_legal = self.llm.predict(legal_check_prompt).strip().upper()
            
            if is_legal != 'LEGAL':
                return "I apologize, but I can only answer questions related to legal matters, Indian law, and legal documents. Please ask a legal question."
        
            # Create a comprehensive prompt for legal queries
            prompt = f"""You are a legal expert. The user has asked: {message}

Previous Chat History:
{self._format_chat_history(chat_history)}

Please provide a detailed and accurate response that:
1. Directly addresses the legal question
2. Is informative and well-structured
3. Uses clear and professional legal language
4. Includes relevant legal examples or explanations when helpful
5. Maintains a professional legal tone
6. Considers the chat history for context

Remember to:
- Focus only on legal matters
- Stay professional and respectful
- Admit when you're not sure about something
- Suggest consulting legal professionals for specific advice
- Keep responses clear and well-organized"""

            # Get response from OpenAI
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful and knowledgeable legal assistant. Provide clear, accurate, and well-structured responses about legal matters only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            # Extract and format the response
            bot_response = response.choices[0].message.content
            
            # Add bot response to chat history
            chat_history.append({"role": "assistant", "content": bot_response})
            
            return bot_response
            
        except Exception as e:
            logger.error(f"Error in get_response: {str(e)}")
            return f"❌ Error: {str(e)}"

    def _format_chat_history(self, chat_history: List[Dict]) -> str:
        """Format chat history for inclusion in prompts."""
        if not chat_history:
            return "No previous conversation."
        
        formatted_history = []
        for msg in chat_history[-5:]:  # Only include last 5 messages for context
            role = "User" if msg["role"] == "user" else "Assistant"
            formatted_history.append(f"{role}: {msg['content']}")
        
        return "\n".join(formatted_history)

    def _split_text_into_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks with improved handling."""
        try:
            words = text.split()
            chunks = []
            
            for i in range(0, len(words), chunk_size - overlap):
                chunk = ' '.join(words[i:i + chunk_size])
                chunks.append(chunk)
            
            logger.info(f"Text split into {len(chunks)} chunks")
            return chunks
        except Exception as e:
            logger.error(f"Error splitting text into chunks: {str(e)}")
            return [text]  # Return full text as single chunk if splitting fails

    def is_legal_question(self, question: str) -> bool:
        """Check if the question is legal-related with enhanced keyword matching."""
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
        """Find the best matching text and its source using FAISS."""
        # First check for specific article references
        article_match = re.search(r'article\s*(\d+[a-zA-Z]*)', question.lower())
        if article_match:
            article_num = article_match.group(1)
            # Look for exact article match in constitutional dataset
            exact_matches = []
            for text, source in zip(self.texts, self.sources):
                if f"Article {article_num}" in text:
                    exact_matches.append((text, source))
            if exact_matches:
                # Combine all exact matches
                combined_text = "\n\n".join([f"Source: {source}\n{text}" for text, source in exact_matches])
                return combined_text, [source for _, source in exact_matches]

        # Check for specific section references
        section_match = re.search(r'section\s*(\d+[a-zA-Z]*)', question.lower())
        if section_match:
            section_num = section_match.group(1)
            # Look for exact section match in IPC dataset
            exact_matches = []
            for text, source in zip(self.texts, self.sources):
                if f"Section {section_num}" in text:
                    exact_matches.append((text, source))
            if exact_matches:
                # Combine all exact matches
                combined_text = "\n\n".join([f"Source: {source}\n{text}" for text, source in exact_matches])
                return combined_text, [source for _, source in exact_matches]

        # If no exact match found, perform similarity search
        question_embedding = self.embeddings.embed_query(question)
        scores, indices = self.index.search(np.array([question_embedding]), k=5)
        
        # Filter out low similarity matches
        threshold = 0.8
        high_similarity_matches = [(scores[0][i], indices[0][i]) for i in range(len(scores[0])) if scores[0][i] >= threshold]
        
        if not high_similarity_matches:
            # If no high similarity matches, take top 3 matches
            high_similarity_matches = [(scores[0][i], indices[0][i]) for i in range(min(3, len(scores[0])))]
        
        # Get the texts and sources for the matches
        matched_texts = []
        matched_sources = []
        for _, idx in high_similarity_matches:
            if idx < len(self.texts):  # Ensure index is valid
                matched_texts.append(self.texts[idx])
                matched_sources.append(self.sources[idx])
        
        # Combine the matched texts with their sources
        combined_text = "\n\n".join([f"Source: {source}\n{text}" for text, source in zip(matched_texts, matched_sources)])
        
        return combined_text, matched_sources

    def handle_question(self, question, file_path=None):
        """Handle both general questions and PDF-specific questions."""
        try:
            if not question or not question.strip():
                return """
                <div class="message-content">
                    <p>Please provide a valid question.</p>
                </div>
                """

            # If a file is provided, use PDF-specific handling
            if file_path and os.path.exists(file_path):
                try:
                    # Extract text from PDF
                    doc = fitz.open(file_path)
                    context = ""
                    for page in doc:
                        try:
                            context += page.get_text()
                        except Exception as e:
                            print(f"Warning: Could not read page {page.number + 1}: {str(e)}")
                            continue
                    doc.close()
                    
                    if not context.strip():
                        return """
                        <div class="message-content">
                            <p>I apologize, but I couldn't extract any text from the document. Please make sure the document is not empty or corrupted.</p>
                        </div>
                        """

                    # Use the PDF-specific QA chain
                    response = self.qa_chain.run({"context": context, "question": question})
                    
                    return f"""
                    <div class="pdf-response">
                        <div class="response-content">
                            <h3>Document Analysis Response:</h3>
                            <p>{response}</p>
                        </div>
                    </div>
                    """

                except Exception as e:
                    print(f"Error reading PDF: {str(e)}")
                    return """
                    <div class="message-content">
                        <p>I apologize, but I encountered an error while reading the document. Please try uploading the document again.</p>
                    </div>
                    """
            else:
                # Use general chatbot for non-PDF questions
                return self.get_response(question)

        except Exception as e:
            print(f"Error handling question: {str(e)}")
            return """
            <div class="message-content">
                <p>I apologize, but I encountered an unexpected error. Please try again or rephrase your question.</p>
            </div>
            """

    def analyze_pdf(self, pdf_text: str, filename: str = None) -> str:
        """Analyze the PDF content and generate a summary using OpenAI directly."""
        try:
            if not pdf_text or len(pdf_text.strip()) == 0:
                return "The document appears to be empty or could not be read properly."

            # Create a prompt for OpenAI to generate the complete report
            report_prompt = f"""You are a legal expert. Analyze this legal document and generate a comprehensive report in the following format:

Text to analyze:
{pdf_text}

Filename (if available): {filename}

Generate a report with the following structure:

📋 LEGAL DOCUMENT ANALYSIS REPORT

1️⃣ CASE INFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏛️ Case Name: [Extract the complete case name and number from the document text. If not found in text, use the filename without extension]
📅 Date: [Extract the exact date of judgment/order in DD Month YYYY format]
👨‍⚖️ Judges: [List all judges who presided over the case]

2️⃣ DOCUMENT SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Provide a clear, concise summary of the case in 2-3 sentences]

3️⃣ KEY CONCLUSION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Provide the key conclusion or outcome in 1-2 sentences]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Note: This analysis is for informational purposes only. For specific legal advice, please consult a qualified legal practitioner.

Instructions:
1. For case name:
   - First try to find the complete case name and number in the document text
   - If not found, use the filename (without extension) as the case name
   - Format the case name properly with proper spacing and capitalization
2. For date:
   - Look for date patterns like "DD Month YYYY" or "DD/MM/YYYY"
   - Convert any numeric dates to the proper format (e.g., "15/05/2023" to "15 May 2023")
   - If multiple dates found, use the most recent one
3. For judges:
   - List all judges who presided over the case
   - Include their full names and titles
4. For summary and conclusion:
   - Be precise and concise
   - Focus on the key legal points
   - Use clear legal terminology
5. Maintain the exact formatting with emojis and dividers"""

            # Get response from OpenAI
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a legal expert specializing in document analysis. Provide clear, accurate, and well-structured legal reports."},
                    {"role": "user", "content": report_prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent output
                max_tokens=1000
            )
            
            # Extract and return the formatted report
            report = response.choices[0].message.content.strip()
            return report

        except Exception as e:
            logger.error(f"Error in analyze_pdf: {str(e)}")
            return "I apologize, but I encountered an error while analyzing the document. Please try uploading the document again."

    def _split_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """Split text into smaller chunks for processing."""
        try:
            # Split by sentences first
            sentences = text.split('. ')
            chunks = []
            current_chunk = []
            current_size = 0

            for sentence in sentences:
                sentence = sentence.strip() + '. '
                sentence_size = len(sentence)
                
                if current_size + sentence_size > chunk_size and current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = [sentence]
                    current_size = sentence_size
                else:
                    current_chunk.append(sentence)
                    current_size += sentence_size

            if current_chunk:
                chunks.append(' '.join(current_chunk))

            return chunks
        except Exception as e:
            logger.error(f"Error in _split_text: {str(e)}")
            return [text]  # Return original text as single chunk if splitting fails

    def query_pdf_after_report(self, question: str, pdf_text: str) -> str:
        """Answer questions about the PDF content."""
        try:
            if not pdf_text or len(pdf_text.strip()) == 0:
                return "I don't have any document content to analyze. Please upload a document first."

            # Split text into chunks
            chunks = self._split_text(pdf_text)
            
            # Find most relevant chunks for the question
            relevant_chunks = []
            for chunk in chunks:
                if len(chunk.strip()) > 0:
                    relevance = self.llm.predict(
                        f"""Rate the relevance of this text to the question (0-1):
                        
                        Question: {question}
                        Text: {chunk}
                        
                        Provide only a number between 0 and 1:"""
                    )
                    try:
                        score = float(relevance.strip())
                        if score > 0.5:  # Only include chunks with relevance > 0.5
                            relevant_chunks.append(chunk)
                    except ValueError:
                        continue

            if not relevant_chunks:
                return "I couldn't find any relevant information in the document to answer your question."

            # Combine relevant chunks
            context = " ".join(relevant_chunks)
            
            # Generate answer
            answer = self.llm.predict(
                f"""Based on this legal document text, answer the following question:
                
                Document Text: {context}
                
                Question: {question}
                
                Provide a clear, concise answer focusing on the specific information from the document:"""
            )

            return answer

        except Exception as e:
            logger.error(f"Error in query_pdf_after_report: {str(e)}")
            return "I apologize, but I encountered an error while processing your question. Please try again."

    def _extract_case_name(self, text: str, filename: str = None) -> str:
        """Extract the case name from the document filename."""
        try:
            if filename:
                # Remove file extension and clean up the name
                case_name = os.path.splitext(filename)[0]
                # Replace underscores and hyphens with spaces
                case_name = case_name.replace('_', ' ').replace('-', ' ')
                # Clean up extra spaces
                case_name = re.sub(r'\s+', ' ', case_name).strip()
                return case_name
            return "Case name not found"
        except Exception as e:
            logger.error(f"Error extracting case name: {str(e)}")
            return "Case name not found"

    def _extract_date(self, text: str) -> str:
        """Extract the date from the document text."""
        try:
            # Look for date patterns in the entire text
            date_patterns = [
                r'(?:Dated|Date|Ordered|Order)\s+on\s+(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4})',
                r'(?:Dated|Date|Ordered|Order)\s+(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4})',
                r'(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4})',
                r'(\d{1,2}/\d{1,2}/\d{4})',
                r'(\d{1,2}-\d{1,2}-\d{4})'
            ]
            
            for pattern in date_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    date = match.group(1).strip()
                    # Clean up the date
                    date = re.sub(r'\s+', ' ', date)  # Remove extra spaces
                    # If it's a numeric date, convert to proper format
                    if '/' in date or '-' in date:
                        try:
                            if '/' in date:
                                day, month, year = date.split('/')
                            else:
                                day, month, year = date.split('-')
                            # Convert month number to month name
                            month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                                         'July', 'August', 'September', 'October', 'November', 'December']
                            month_name = month_names[int(month) - 1]
                            date = f"{int(day)} {month_name} {year}"
                        except:
                            pass
                    return date
            
            return "Date not found"
            
        except Exception as e:
            logger.error(f"Error extracting date: {str(e)}")
            return "Date not found"

    def _extract_judges(self, text: str) -> List[str]:
        """Extract judge names from the document text."""
        try:
            # Try to find judges in first few sentences
            sentences = self.split_into_sentences(text)
            first_page = " ".join(sentences[:10])  # Look in first 10 sentences
            
            # Common patterns for judge names
            patterns = [
                r'(?:HON\'?BLE|HONORABLE)\s+(?:JUSTICE|MR\.|MRS\.|MS\.)\s+([A-Za-z\s\.]+)',
                r'(?:JUSTICE|J\.)\s+([A-Za-z\s\.]+)',
                r'(?:PRESIDING|BENCH)\s+(?:JUSTICE|JUDGE)\s+([A-Za-z\s\.]+)'
            ]
            
            judge_names = set()
            for pattern in patterns:
                matches = re.finditer(pattern, first_page, re.IGNORECASE)
                for match in matches:
                    name = match.group(1).strip()
                    # Clean up the name
                    name = re.sub(r'\s+', ' ', name)  # Remove extra spaces
                    name = re.sub(r'\.+', '.', name)  # Clean up dots
                    if len(name.split()) <= 5:  # Avoid long matches
                        judge_names.add(name)
            
            if judge_names:
                return list(judge_names)
            
            # If no pattern matches, use LLM to extract judge names
            judges_prompt = f"""Extract the names of the judges from this legal document text. Return only the names, separated by commas:

Text: {first_page}

Judges:"""
            
            judges = self.llm.predict(judges_prompt).strip()
            if judges:
                return [name.strip() for name in judges.split(',')]
            
            return ["Judge(s) not found"]
            
        except Exception as e:
            logger.error(f"Error extracting judges: {str(e)}")
            return ["Judge(s) not found"] 