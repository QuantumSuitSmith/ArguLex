import csv
import os
from typing import Dict, List, Optional
import re

class BaseChatbot:
    def __init__(self, ipc_path: str, constitutional_path: str):
        self.ipc_path = ipc_path
        self.constitutional_path = constitutional_path
        self.ipc_knowledge_base: Dict[str, List[str]] = {}
        self.constitutional_knowledge_base: Dict[str, List[str]] = {}
        self.load_knowledge_bases()

    def load_knowledge_bases(self):
        """Load both IPC and Constitutional Law knowledge bases from CSV files"""
        # Load IPC dataset
        try:
            with open(self.ipc_path, 'r', encoding='utf-8') as f:
                csv_reader = csv.DictReader(f)
                for row in csv_reader:
                    section = row['Section'].strip()
                    description = row['Description'].strip()
                    offense = row['Offense'].strip()
                    punishment = row['Punishment'].strip()
                    
                    if section not in self.ipc_knowledge_base:
                        self.ipc_knowledge_base[section] = []
                    self.ipc_knowledge_base[section].append({
                        'description': description,
                        'offense': offense,
                        'punishment': punishment
                    })
        except FileNotFoundError:
            print(f"Warning: IPC knowledge base file not found at {self.ipc_path}")

        # Load Constitutional Law dataset
        try:
            with open(self.constitutional_path, 'r', encoding='utf-8') as f:
                csv_reader = csv.DictReader(f)
                for row in csv_reader:
                    article = row['article_id'].strip()
                    description = row['article_desc'].strip()
                    
                    if article not in self.constitutional_knowledge_base:
                        self.constitutional_knowledge_base[article] = []
                    self.constitutional_knowledge_base[article].append({
                        'description': description
                    })
        except FileNotFoundError:
            print(f"Warning: Constitutional Law knowledge base file not found at {self.constitutional_path}")

    def preprocess_query(self, query: str) -> str:
        """Clean and normalize the user query"""
        query = query.lower()
        query = re.sub(r'[^\w\s]', '', query)
        query = ' '.join(query.split())
        return query

    def find_best_match(self, query: str) -> tuple[Optional[str], str]:
        """Find the best matching response for the query"""
        query = self.preprocess_query(query)
        
        # Extract section number from query if present
        section_match = re.search(r'section\s*(\d+[a-zA-Z]*)', query, re.IGNORECASE)
        if section_match:
            section_num = section_match.group(1)
            ipc_section = f"IPC_{section_num}"
            if ipc_section in self.ipc_knowledge_base:
                return ipc_section, 'ipc'
        
        # Extract article number from query if present
        article_match = re.search(r'article\s*(\d+[a-zA-Z]*)', query, re.IGNORECASE)
        if article_match:
            article_num = article_match.group(1)
            article = f"Article {article_num} of Indian Constitution"
            if article in self.constitutional_knowledge_base:
                return article, 'constitutional'
        
        # Check if query is about IPC
        if any(word in query for word in ['ipc', 'penal code', 'crime', 'punishment', 'section']):
            for section in self.ipc_knowledge_base.keys():
                section_num = section.replace('IPC_', '')
                if section_num.lower() in query:
                    return section, 'ipc'
        
        # Check if query is about Constitutional Law
        if any(word in query for word in ['constitution', 'article', 'fundamental rights', 'constitutional']):
            for article in self.constitutional_knowledge_base.keys():
                if article.lower() in query:
                    return article, 'constitutional'
        
        # If no direct match, try keyword matching
        best_match = None
        max_matches = 0
        source = 'ipc'
        
        # Check IPC knowledge base
        for section in self.ipc_knowledge_base.keys():
            section_num = section.replace('IPC_', '')
            query_words = set(query.split())
            section_words = set(section_num.split())
            matches = len(query_words.intersection(section_words))
            
            if matches > max_matches:
                max_matches = matches
                best_match = section
                source = 'ipc'
        
        # Check Constitutional knowledge base
        for article in self.constitutional_knowledge_base.keys():
            query_words = set(query.split())
            article_words = set(article.split())
            matches = len(query_words.intersection(article_words))
            
            if matches > max_matches:
                max_matches = matches
                best_match = article
                source = 'constitutional'
        
        return best_match, source

    def get_response(self, query: str) -> str:
        """Get a response for the user query"""
        best_match, source = self.find_best_match(query)
        
        if best_match:
            if source == 'ipc':
                responses = self.ipc_knowledge_base[best_match]
            else:
                responses = self.constitutional_knowledge_base[best_match]
            return responses[0]
        
        return "I'm sorry, I don't have enough information to answer that question. Could you please rephrase or ask something else?"

class GeneralChatbot(BaseChatbot):
    def __init__(self):
        super().__init__('data/ipc_sections.csv', 'data/constitutional_dataset.csv')
    
    def get_response(self, query: str) -> str:
        """Get a simplified response for general legal queries"""
        best_match, source = self.find_best_match(query)
        
        if best_match:
            if source == 'ipc':
                data = self.ipc_knowledge_base[best_match][0]
                response = f"Section {best_match} of the IPC:\n\n"
                response += f"{data['description']}\n\n"
                response += f"Offense: {data['offense']}\n"
                response += f"Punishment: {data['punishment']}"
            else:
                data = self.constitutional_knowledge_base[best_match][0]
                response = f"{best_match}:\n\n"
                response += f"{data['description']}"
            
            response += "\n\nNote: This is a simplified explanation. For detailed legal advice, please consult a legal expert."
            return response
        
        return "I'm sorry, I couldn't find specific information about that. This is the general legal assistant. For more detailed legal advice, please consult a legal expert."

class ProfessionalChatbot(BaseChatbot):
    def __init__(self):
        super().__init__('data/ipc_sections.csv', 'data/constitutional_dataset.csv')
    
    def get_response(self, query: str) -> str:
        """Get a detailed response for professional legal queries"""
        best_match, source = self.find_best_match(query)
        
        if best_match:
            if source == 'ipc':
                data = self.ipc_knowledge_base[best_match][0]
                response = f"IPC {best_match}:\n\n"
                response += "Legal Analysis:\n\n"
                response += f"1. Description:\n{data['description']}\n\n"
                response += f"2. Offense Classification:\n{data['offense']}\n\n"
                response += f"3. Prescribed Punishment:\n{data['punishment']}\n\n"
                response += "4. Key Elements:\n"
                response += "   - Actus Reus (Criminal Act)\n"
                response += "   - Mens Rea (Criminal Intent)\n"
                response += "   - Causation and Harm\n\n"
                response += "5. Important Considerations:\n"
                response += "   - Burden of Proof: Beyond reasonable doubt\n"
                response += "   - Standard of Evidence\n"
                response += "   - Defenses Available\n"
            else:
                data = self.constitutional_knowledge_base[best_match][0]
                response = f"{best_match}:\n\n"
                response += "Legal Analysis:\n\n"
                response += f"1. Constitutional Provision:\n{data['description']}\n\n"
                response += "2. Scope and Application:\n"
                response += "   - Fundamental Rights/Directive Principles\n"
                response += "   - Constitutional Obligations\n"
                response += "   - State's Responsibilities\n\n"
                response += "3. Judicial Interpretation:\n"
                response += "   - Supreme Court Precedents\n"
                response += "   - Constitutional Bench Decisions\n"
                response += "   - Evolution of Jurisprudence\n"
            
            response += "\nDisclaimer: This analysis is for informational purposes only. For specific legal advice, please consult a qualified legal practitioner."
            return response
        
        return "I'm sorry, I couldn't find specific information about that query. Please provide more specific details, including relevant section numbers or article references." 