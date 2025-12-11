import os
from flask import Flask, request, render_template
import google.generativeai as genai  # <--- VIGTIGT: Det officielle bibliotek
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv 

# 1. Indlæs miljøvariabler (.env filen)
load_dotenv()

app = Flask(__name__)

# --- KONFIGURATION ---
# Tilpas stien hvis din mappe hedder noget andet (f.eks. chroma_db)
VECTOR_DB_PATH = "bodil_data_db" 

# --- INITIALISERING ---

# A. Sprogmodel (Embeddings)
# Vi bruger stadig den lokale model til at søge i databasen, da det er hurtigt og gratis.
print("⏳ Indlæser sprogmodel (Embeddings)...")
# Husk: Hvis du skiftede til 'paraphrase-multilingual...' i create_db, skal du også bruge den her!
embeddings = SentenceTransformerEmbeddings(model_name="paraphrase-multilingual-MiniLM-L12-v2")

# B. Vektorlager (Databasen)
try:
    vector_db = Chroma(persist_directory=VECTOR_DB_PATH, embedding_function=embeddings)
    retriever = vector_db.as_retriever(search_kwargs={"k": 5}) 
    print("✅ Chroma DB og Retriever indlæst.")
except Exception as e:
    print(f"❌ FEJL: Kunne ikke indlæse Chroma DB. Fejl: {e}")
    retriever = None

# C. Gemini API Setup
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ ADVARSEL: GEMINI_API_KEY mangler i .env filen!")
else:
    # Konfigurer Google GenAI med din nøgle
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Vælg model. 'gemini-1.5-flash' er hurtig, billig og god til tekst.
    model = genai.GenerativeModel('gemini-flash-latest')
    print("✅ Gemini API klar.")


# --- RAG FUNKTIONEN ---
def get_rag_answer(question):
    # Tjek om systemet er klar
    if not retriever:
        return "Fejl: Databasen er ikke indlæst."
    if not GEMINI_API_KEY:
        return "Fejl: Mangler API-nøgle til Gemini."

    # 1. Retrieval (Find viden)
    print(f"🔍 Søger efter viden om: {question}")
    docs = retriever.invoke(question)
    
    if not docs:
        return "Jeg kunne desværre ikke finde noget relevant information i mine dokumenter."

    # Saml teksten fra de fundne PDF-sider
    context = "\n\n".join([doc.page_content for doc in docs])

    # 2. Prompt (Instruktion til Gemini)
# 2. Prompt (Instruktion til Gemini)
# 2. Prompt (Instruktion til Gemini)
    prompt = (
        "Du er en direkte og effektiv support-bot for Bodil Energi. "
        "Din opgave er at svare brugeren så kort som muligt baseret på konteksten. "
        
        # HER ER REGLERNE FOR SVARET:
        "REGLER:"
        "1. Svar på dansk."
        "2. Hold svaret på MAKSIMALT 3 sætninger."
        "3. Gå direkte til pointen (ingen 'Hej', 'Tak for spørgsmålet' eller 'Her er informationen')."
        "4. Brug IKKE punktopstillinger eller lister."
        
        f"\n\nKONTEKST FRA DOKUMENTER:\n{context}\n\n"
        f"BRUGERENS SPØRGSMÅL: {question}"
    )

    # 3. Generation (Spørg Gemini)
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Fejl ved kontakt til Google Gemini: {e}"


# --- FLASK WEB SERVER ---
@app.route('/', methods=['GET', 'POST'])
def index():
    svar_tekst = ""
    bruger_sporgsmaal = ""  # <--- 1. Opret en tom variabel her

    if request.method == 'POST':
        bruger_sporgsmaal = request.form.get('sporgsmaal') # <--- 2. Gem det brugeren skrev
        
        if bruger_sporgsmaal:
            svar_tekst = get_rag_answer(bruger_sporgsmaal)
    
    # 3. Send BÅDE 'svar' OG 'sporgsmaal' med tilbage til HTML
    return render_template('index.html', svar=svar_tekst, sporgsmaal=bruger_sporgsmaal)

if __name__ == '__main__':
    app.run(debug=True)