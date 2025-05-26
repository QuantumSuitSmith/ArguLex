from .general_chatbot import GeneralChatbot
from .professional_chatbot import ProfessionalChatbot
import os
import tempfile
import fitz
from nltk import sent_tokenize
import re

class ChatbotManager:
    def __init__(self):
        self.general_chatbot = GeneralChatbot()
        self.professional_chatbot = ProfessionalChatbot()
        self.temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp')
        os.makedirs(self.temp_dir, exist_ok=True)

    def get_response(self, message, chatbot_type, document_context=None):
        """Get response from the appropriate chatbot."""
        try:
            if chatbot_type == 'general':
                return self.general_chatbot.get_response(message)
            elif chatbot_type == 'professional':
                if document_context:
                    return self.professional_chatbot.query_pdf_after_report(message, document_context)
                return self.professional_chatbot.get_response(message)
            else:
                raise ValueError(f"Unknown chatbot type: {chatbot_type}")
        except Exception as e:
            print(f"Error in get_response: {str(e)}")
            raise

    def query_pdf(self, message, pdf_text, chatbot_type):
        """Query a PDF document with a specific question."""
        try:
            if chatbot_type == 'professional':
                return self.professional_chatbot.query_pdf_after_report(message, pdf_text)
            else:
                raise ValueError(f"PDF querying not supported for chatbot type: {chatbot_type}")
        except Exception as e:
            print(f"Error in query_pdf: {str(e)}")
            raise

    def handle_pdf(self, file, chatbot_type):
        """Handle PDF file upload and processing."""
        tmp_path = None
        doc = None
        try:
            if not file or not file.filename:
                return "No file uploaded", "error", None

            if not file.filename.lower().endswith('.pdf'):
                return "Only PDF files are supported", "error", None

            if chatbot_type != 'professional':
                return "Invalid chatbot type for document processing", "error", None

            # Save the file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                file.save(tmp.name)
                tmp_path = tmp.name

            # Extract text from PDF
            doc = fitz.open(tmp_path)
            text = ""
            for page in doc:
                text += page.get_text()

            if not text.strip():
                return "Could not extract text from the PDF", "error", None

            # Extract case information
            case_name = self._extract_case_name(text)
            date = self._extract_date(text)
            judges = self._extract_judges(text)
            summary = self._extract_summary(text)
            conclusion = self._extract_conclusion(text)

            # Create the report
            report = f"""
            <div class="document-analysis">
                <div class="case-header">
                    <h3>🏛️ Case Name: {case_name}</h3>
                    <p>📅 Date: {date}</p>
                    <p>👨‍⚖️ Judges: {judges}</p>
                </div>

                <div class="case-content">
                    <div class="case-section">
                        <h4>🧠 Summary:</h4>
                        <p>{summary}</p>
                    </div>

                    <div class="case-section">
                        <h4>✅ Conclusion:</h4>
                        <p>{conclusion}</p>
                    </div>
                </div>
            </div>
            """

            return report, "success", text

        except Exception as e:
            print(f"Error processing PDF: {str(e)}")
            return f"Error processing PDF: {str(e)}", "error", None

        finally:
            # Clean up resources
            if doc:
                try:
                    doc.close()
                except:
                    pass
            
            # Delete temp file after a short delay to ensure it's not in use
            if tmp_path and os.path.exists(tmp_path):
                try:
                    import time
                    time.sleep(0.1)  # Small delay to ensure file is released
                    os.unlink(tmp_path)
                except Exception as e:
                    print(f"Warning: Could not delete temporary file: {str(e)}")

    def _extract_case_name(self, text):
        """Extract case name from the text."""
        # Look for common patterns in Indian Supreme Court case names
        patterns = [
            r'(?:IN THE SUPREME COURT OF INDIA.*?)(?:CASE NO\.|CIVIL APPEAL NO\.|CRIMINAL APPEAL NO\.|WRIT PETITION NO\.)\s+(\d+)\s+OF\s+\d{4}\s+([A-Z][A-Za-z\s]+(?:VS\.|VERSUS|VS)[A-Z][A-Za-z\s]+)',
            r'(?:IN THE SUPREME COURT OF INDIA.*?)([A-Z][A-Za-z\s]+(?:VS\.|VERSUS|VS)[A-Z][A-Za-z\s]+)',
            r'(?:PETITIONER|APPELLANT)[\s:]+([A-Z][A-Za-z\s]+(?:VS\.|VERSUS|VS)[A-Z][A-Za-z\s]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                # If pattern has two groups, combine them
                if len(match.groups()) > 1:
                    return f"Case No. {match.group(1)} - {match.group(2).strip()}"
                return match.group(1).strip()
        
        return "Case name not found"

    def _extract_date(self, text):
        """Extract date from the text."""
        # Look for common date patterns in Indian judgments
        patterns = [
            r'(?:DATE OF JUDGMENT|DATED|JUDGMENT DELIVERED ON)[\s:]+(\d{1,2}/\d{1,2}/\d{4})',
            r'(?:DATE OF JUDGMENT|DATED|JUDGMENT DELIVERED ON)[\s:]+(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
            r'(\d{1,2}/\d{1,2}/\d{4})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "Date not found"

    def _extract_judges(self, text):
        """Extract judges' names from the text."""
        # Look for common patterns in Indian Supreme Court judge listings
        patterns = [
            r'(?:BENCH|CORAM|BEFORE)[\s:]+(?:Justice|Hon\'ble|Honorable)?\s*([A-Z][A-Za-z\s\.]+(?:J\.|Justice))',
            r'(?:JUDGMENT BY|DELIVERED BY)[\s:]+(?:Justice|Hon\'ble|Honorable)?\s*([A-Z][A-Za-z\s\.]+(?:J\.|Justice))',
            r'(?:Justice|Hon\'ble|Honorable)\s+([A-Z][A-Za-z\s\.]+(?:J\.|Justice))'
        ]
        
        judges = []
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                judge = match.group(1).strip()
                if judge not in judges:
                    judges.append(judge)
        
        return ", ".join(judges) if judges else "Judges not found"

    def _extract_summary(self, text):
        """Extract case summary from the text."""
        # Look for summary sections in Indian judgments
        patterns = [
            r'(?:JUDGMENT|FACTS|BACKGROUND)[\s:]+([^.]{50,500}\.)',
            r'(?:The appeal|This appeal|The petition)[\s:]+([^.]{50,500}\.)',
            r'(?:The main issue|The principal question)[\s:]+([^.]{50,500}\.)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        
        # If no specific section found, take first few sentences after the header
        sentences = sent_tokenize(text)
        for i, sentence in enumerate(sentences):
            if "JUDGMENT" in sentence.upper() and i + 1 < len(sentences):
                return " ".join(sentences[i+1:i+4])
        
        return "Summary not found"

    def _extract_conclusion(self, text):
        """Extract conclusion from the text."""
        # Look for conclusion sections in Indian judgments
        patterns = [
            r'(?:HELD|CONCLUSION|DECISION)[\s:]+([^.]{50,500}\.)',
            r'(?:Therefore|Hence|Accordingly)[\s:]+([^.]{50,500}\.)',
            r'(?:In view of the above|For the reasons stated above)[\s:]+([^.]{50,500}\.)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        
        # If no specific section found, take last few sentences
        sentences = sent_tokenize(text)
        if len(sentences) > 2:
            return " ".join(sentences[-3:])
        
        return "Conclusion not found" 