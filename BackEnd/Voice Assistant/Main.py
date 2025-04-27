import os
import webbrowser
import speech_recognition as sr
import win32com.client
from transformers import pipeline

def say(text):
    speaker = win32com.client.Dispatch("SAPI.SpVoice")
    speaker.Rate = -2
    speaker.Speak("\u200B" + text)

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


text_gen = pipeline("text2text-generation", model="google/flan-t5-base")


last_topic = None

def generate_answer(query):
    global last_topic

    
    for key in legal_topics.keys():
        if key in query:
            last_topic = key
            topic_info = legal_topics[key]
            response = f"{topic_info['summary']} {topic_info['example']}"
            print("Answer:", response)
            say(response)
            return

    if "more specific" in query or "example" in query:
        if last_topic:
            topic_info = legal_topics[last_topic]
            detailed_response = f"Sure. {topic_info['summary']} {topic_info['example']}"
            print("Answer:", detailed_response)
            say(detailed_response)
        else:
            say("Could you please tell me which topic you want more details about?")
        return

    
    prompt = f"Answer this legal question in detail with examples: {query}\nContext: {legal_topics}"
    result = text_gen(prompt, max_new_tokens=200)[0]["generated_text"]
    print("Answer:", result)
    say(result)

def handle_basic_commands(query):
    if "open youtube" in query:
        say("Opening YouTube.")
        webbrowser.open("https://youtube.com")
        return True
    elif "open wikipedia" in query:
        say("Opening Wikipedia.")
        webbrowser.open("https://wikipedia.org")
        return True
    elif "exit" in query or "stop" in query:
        say("Okay Cyril, exiting ArguLex. Have a great day!")
        exit()
    return False

if __name__ == "__main__":
    say("Hello Cyril, ArguLex voice assistant is now active and ready to answer your legal questions.")
    
    while True:
        query = take_command()

        if not query:
            say("Sorry, I didn't catch that. Please repeat.")
            continue

        if not handle_basic_commands(query):
            generate_answer(query)
