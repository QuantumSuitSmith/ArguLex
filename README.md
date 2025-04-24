# ⚖️ ArguLex: Indian Law Voice-Enabled Legal Assistant

**ArguLex** is an AI-powered legal assistant that helps users understand Indian laws using natural language, semantic search, and voice-based interaction. It uses powerful NLP tools to retrieve and explain information from two key legal sources:

- 🧾 **Indian Penal Code (IPC)**
- 📜 **Constitution of India**

---

## 🧠 Overview

ArguLex is designed to democratize access to legal knowledge by combining:
- Vector search with Sentence Transformers
- Generative AI using OpenAI models
- Voice input/output for conversational access
- A clean Gradio-based chat interface

---

## 📚 Datasets Included

### 1. **Indian Penal Code (IPC) Dataset**
- Contains all major IPC sections with:
  - Section number
  - Title
  - Full legal description
- 🗂 Format: CSV and JSON

📌 **Source**: [Kaggle - akshit2605/ipc-sections-dataset](https://www.kaggle.com/datasets/akshit2605/ipc-sections-dataset)

---

### 2. **Indian Constitution Dataset**
- Includes Articles with:
  - Article number
  - Title/headline
  - Full content of the article
- 🗂 Format: JSON and CSV

📌 **Source**: [Hugging Face - Sharathhebbar24/Indian-Constitution](https://huggingface.co/datasets/Sharathhebbar24/Indian-Constitution)

---

## 🔍 Key Features

- 🔎 **Semantic Legal Search** — Retrieve relevant laws/articles from user queries using Sentence Transformers.
- 💬 **Chatbot Interface** — Ask any legal question and get structured, human-like answers.
- 🗣️ **Voice Assistant** — Speak your query and hear back the AI-generated legal answer.
- 🌐 **Gradio Web Interface** — User-friendly, browser-based access to the chatbot.

---

## 🛠️ Project Structure

```bash
📦 argulex-legal-ai
├── data/
│   ├── ipc_sections.csv
│   └── indian_constitution.csv
├── app/
│   ├── chatbot.py           # Retrieval and RAG logic
│   ├── voice_interface.py   # Voice input/output
│   └── interface.py         # Gradio UI
├── models/
│   └── embedding_model.pkl
├── requirements.txt
└── README.md
