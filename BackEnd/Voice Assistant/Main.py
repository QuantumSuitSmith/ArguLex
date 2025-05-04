import webbrowser
import urllib.parse
import requests
import speech_recognition as sr
import win32com.client

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
            return ""
        except sr.RequestError as e:
            print(f"Speech Recognition error: {e}")
            return ""

# Known legal topics
legal_topics = {
    "fir": {
        "summary": "An FIR (First Information Report) is a document filed by police when a cognizable offense is reported. It begins the investigation.",
        "example": "For example, if someone is assaulted, the victim can file an FIR at the police station."
    },
    "section 420": {
        "summary": "Section 420 of the Indian Penal Code deals with cheating and dishonestly inducing delivery of property.",
        "example": "For example: Selling fake gold as real gold falls under Section 420."
    },
    "pocso": {
        "summary": "The POCSO Act (Protection of Children from Sexual Offences) is a law to protect children from sexual abuse.",
        "example": "Any sexual act involving a child below 18 is punishable under POCSO."
    }
}

# Expanded legal keywords
legal_keywords = list(set([
    "law", "legal", "rights", "fundamental rights", "article", "act", "bill", "constitution",
    "ipc", "section", "penal code", "clause", "rule", "pocso", "sc/st act", "498a", "dowry", "posh", "nda", "nrc",
    "court", "high court", "supreme court", "tribunal", "judge", "magistrate", "session court",
    "judgment", "petition", "appeal", "trial", "case", "litigation", "legal aid",
    "sue", "sued", "arrest", "remand", "charge sheet", "cross examination", "summons", "witness",
    "confession", "hearing", "bail", "evidence", "fir", "charge", "verdict", "compensation",
    "advocate", "lawyer", "attorney", "solicitor",
    "divorce", "property", "murder", "theft", "cheating", "contract", "fraud",
    "tenant", "landlord", "will", "lease", "possession", "partition", "trespass",
    "marriage", "alimony", "custody", "maintenance", "adoption", "guardianship",
    "gratuity", "labour law", "wages", "employment", "termination", "notice period", "employment contract",
    "cyber crime", "hacking", "data breach", "privacy law", "it act", "online fraud", "phishing",
    "criminal", "civil", "crime", "offense", "bailable", "non-bailable", "punishment", "sentence",
    "vote", "voting", "election", "right to vote", "adult suffrage",
    "notary", "affidavit", "minor", "guardian", "succession", "intestate", "juvenile", "oath", "injunction", "compliance", "consumer forum"
]))


def fetch_web_answer(query):
    say("Opening Google to search for the answer.")
    webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}")
    return "I've opened Google with your query."

# Generate legal answer
def generate_answer(query):
    if not any(keyword in query for keyword in legal_keywords):
        say("This doesn't seem to be a legal question. Please ask a legal query.")
        return

    for key in legal_topics.keys():
        if key in query:
            topic_info = legal_topics[key]
            response = f"{topic_info['summary']} {topic_info['example']}"
            print("Answer:", response)
            say(response)
            return

    say("This topic is not in my database. Let me search the web.")
    result = fetch_web_answer(query)
    print("Web result:", result)
    say(result)

# Basic commands
def handle_basic_commands(query):
    query = query.lower()

    if "exit" in query or "stop" in query or "quit" in query:
        say("Okay Cyril, exiting ArguLex. Have a great day!")
        exit()

    elif "file fir" in query or "lodge fir" in query:
        say("You can file an FIR at the police station or online. Opening the online portal.")
        webbrowser.open("https://www.tspolice.gov.in/firstatus")
        return True

    elif "check case status" in query:
        say("Redirecting to the e-Courts portal.")
        webbrowser.open("https://ecourts.gov.in/")
        return True

    elif "find police station" in query:
        say("Searching nearby police stations.")
        webbrowser.open("https://www.google.com/maps/search/police+station+near+me/")
        return True

    elif "get legal help" in query or "connect with lawyer" in query:
        say("Redirecting you to legal aid services.")
        webbrowser.open("https://nalsa.gov.in/")
        return True

    elif "how to write legal notice" in query:
        say("Opening a guide on writing a legal notice.")
        webbrowser.open("https://blog.ipleaders.in/how-to-draft-a-legal-notice/")
        return True

    elif "know my rights" in query:
        say("Opening a guide to your fundamental legal rights.")
        webbrowser.open("https://www.legalserviceindia.com/legal/article-13-know-your-rights-as-an-indian-citizen.html")
        return True

    return False

# Main loop
if __name__ == "__main__":
    say("Hello Cyril, ArguLex voice assistant is ready to answer your legal questions.")
    while True:
        query = take_command()
        if not query:
            say("Sorry, I didn't catch that. Please repeat.")
            continue

        if not handle_basic_commands(query):
            generate_answer(query)
