import requests, time, json, re, os
from dotenv import load_dotenv
load_dotenv('/data/data/com.termux/files/home/NexusLIFE/.env')
GROQ_KEY = os.getenv("GROQ_API_KEY","")
BASE = "http://localhost:8001"
AGENT = "NexusSearchAgent"

def search_ddg(query):
    try:
        r = requests.get("https://api.duckduckgo.com/",
            params={"q":query,"format":"json","no_html":1,"skip_disambig":1},
            timeout=5)
        d = r.json()
        results = []
        if d.get("AbstractText"):
            results.append(d["AbstractText"][:200])
        for rel in d.get("RelatedTopics",[])[:3]:
            if isinstance(rel, dict) and rel.get("Text"):
                results.append(rel["Text"][:150])
        return " | ".join(results) if results else ""
    except:
        return ""

def ask(desc, context=""):
    prompt = "Return ONLY exact answer. No explanation.\n\n"
    if context:
        prompt += "Context: " + context + "\n\n"
    prompt += "Task: " + desc + "\n\nANSWER:"
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": "Bearer " + GROQ_KEY},
        json={"model":"llama-3.3-70b-versatile",
              "messages":[{"role":"user","content":prompt}],
              "max_tokens":100,"temperature":0},timeout=15)
    if r.ok: return r.json()["choices"][0]["message"]["content"].strip()
    return None

SEARCH_CATS = ["Real-World","LLM Knowledge","AI Knowledge","Business","Temporal Robustness","Hallucination"]

requests.post(BASE + "/register", json={"agent_name": AGENT})
challenges = requests.get(BASE + "/challenges").json()
all_ch = [c for cat,chs in challenges["categories"].items() for c in chs if cat != "API"]
print("NexusSearchAgent — " + str(len(all_ch)) + " challenges", flush=True)
score = correct = searched = 0

for c in all_ch:
    t0 = time.time()
    context = ""
    if c["category"] in SEARCH_CATS:
        context = search_ddg(c["description"][:80])
        if context: searched += 1
    answer = ask(c["description"], context)
    ms = int((time.time()-t0)*1000)
    if not answer: continue
    answer = re.sub(r'<think>.*?</think>','',answer,flags=re.DOTALL).strip()
    try: parsed = json.loads(answer)
    except: parsed = answer.strip('"').strip("'")
    r = requests.post(BASE + "/submit", json={
        "agent_name":AGENT,"challenge_id":c["id"],"answer":parsed,"time_ms":ms})
    if r.status_code == 200 and r.json().get("correct"):
        score += r.json().get("score_earned",0)
        correct += 1
        print("OK " + c["name"] + " +" + str(r.json()["score_earned"]) + "pts", flush=True)
    time.sleep(0.4)

print("NexusSearchAgent: " + str(correct) + "/" + str(len(all_ch)) + " — " + str(int(score)) + "pts", flush=True)
print("Recherches DDG: " + str(searched), flush=True)
