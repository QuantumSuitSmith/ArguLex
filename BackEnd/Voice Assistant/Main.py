import webbrowser
import urllib.parse
import time
import speech_recognition as sr
import win32com.client
from transformers import pipeline

# Text-to-Speech
def say(text):
    speaker = win32com.client.Dispatch("SAPI.SpVoice")
    speaker.Rate = -2
    speaker.Speak("\u200B" + text)

# Voice input
def take_command():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Say Something...")
        recognizer.pause_threshold = 1
        audio = recognizer.listen(source)
        try:
            query = recognizer.recognize_google(audio, language="en-in")
            print(f"User said: {query}")
            return query.lower()
        except sr.UnknownValueError:
            print("Could not understand audio")
            return ""
        except sr.RequestError as e:
            print(f"Speech Recognition error: {e}")
            return ""

# Legal topics dataset
legal_topics = {
    "fir": {
        "summary": "An FIR (First Information Report) is a written document prepared by the police when they receive information about a cognizable offense. It marks the beginning of the investigation process.",
        "example": "For example, if someone is assaulted, the victim or witness can file an FIR at the police station."
    },
    "section 420": {
        "summary": "Section 420 of the Indian Penal Code (IPC) punishes cheating and dishonestly inducing delivery of property with up to 7 years imprisonment and a fine.",
        "example": "For example: Selling fake gold as real gold falls under Section 420."
    },
    "section 41": {
        "summary": "Section 41 of the Code of Criminal Procedure (CrPC) allows police to arrest a person without a warrant under certain circumstances, like committing a cognizable offense.",
        "example": "For example: If someone is caught stealing in a store, the police can arrest them without a warrant."
    }
}

# Load text generation model
text_gen = pipeline("text2text-generation", model="google/flan-t5-base")

# Track last topic
last_topic = None

# Check if query is legal
def is_legal_query(query):
    keywords = [
        "fir", "section", "ipc", "crpc", "law", "legal", "bail", "arrest", "court",
        "police", "warrant", "punishment", "rights", "act", "petition", "judge", "trial", "judgment"
    ]
    return any(keyword in query.lower() for keyword in keywords)

# Generate answer
def generate_answer(query):
    global last_topic

    # If clearly non-legal, reject politely
    if not is_legal_query(query):
        say("Sorry, I can only help with legal questions. Please ask a legal query.")
        return

    # Check known legal topics
    for key in legal_topics.keys():
        if key in query:
            last_topic = key
            topic_info = legal_topics[key]
            response = f"{topic_info['summary']} {topic_info['example']}"
            print("Answer:", response)
            say(response)
            return

    # Requesting more details
    if "more specific" in query or "example" in query:
        if last_topic:
            topic_info = legal_topics[last_topic]
            detailed_response = f"Sure. {topic_info['summary']} {topic_info['example']}"
            print("Answer:", detailed_response)
            say(detailed_response)
        else:
            say("Could you please tell me which topic you want more details about?")
        return

    # Default legal answer using model
    prompt = f"Answer this legal question in detail with examples: {query}\nContext: {legal_topics}"
    result = text_gen(prompt, max_new_tokens=200)[0]["generated_text"]
    print("Answer:", result)
    say(result)

# Handle basic commands
def handle_basic_commands(query):
    if query.startswith("search for") or query.startswith("google"):
        search_term = query.replace("search for", "").replace("google", "").strip()
        if search_term:
            say(f"Searching Google for {search_term}")
            encoded_search = urllib.parse.quote_plus(search_term)
            webbrowser.open(f"https://www.google.com/search?q={encoded_search}")
        else:
            say("Please tell me what you'd like to search for.")
        return True

    elif "thank you" in query or "exit" in query or "stop" in query:
        say("Alright Cyril, ArguLex is signing off. Wishing you a great day ahead.")
        exit()
    return False

# Main loop
if __name__ == "__main__":
    while True:
        query = take_command()

        if not query:
            say("Sorry, I didn't catch that. Please repeat.")
            continue

        if not handle_basic_commands(query):
            generate_answer(query)
