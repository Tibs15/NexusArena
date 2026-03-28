import requests, time, json, re, os
from dotenv import load_dotenv
load_dotenv('/data/data/com.termux/files/home/NexusLIFE/.env')
GROQ_KEY = os.getenv("GROQ_API_KEY","")
BASE = "http://localhost:8001"
AGENT = "NexusChainAgent"

def ask(messages, max_tokens=200):
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": "Bearer " + GROQ_KEY},
        json={"model":"llama-3.3-70b-versatile",
              "messages":messages,"max_tokens":max_tokens,"temperature":0},timeout=15)
    if r.ok: return r.json()["choices"][0]["message"]["content"].strip()
    return None

def chain_solve(challenge):
    desc = challenge["description"]
    cat = challenge["category"]
    
    # Etape 1 — analyser le type de problème
    step1 = ask([
        {"role":"user","content":"What type of problem is this? Answer in 5 words max.\n\nProblem: " + desc}
    ], 20)
    
    # Etape 2 — raisonner
    step2 = ask([
        {"role":"user","content":"Problem: " + desc},
        {"role":"assistant","content":"Problem type: " + (step1 or "unknown")},
        {"role":"user","content":"Now solve it step by step in 2 sentences max."}
    ], 80)
    
    # Etape 3 — extraire la réponse finale
    step3 = ask([
        {"role":"user","content":"Problem: " + desc},
        {"role":"assistant","content":"Reasoning: " + (step2 or "")},
        {"role":"user","content":"Return ONLY the exact final answer, nothing else:"}
    ], 50)
    
    return step3

requests.post(BASE + "/register", json={"agent_name": AGENT})
challenges = requests.get(BASE + "/challenges").json()
all_ch = [c for cat,chs in challenges["categories"].items() for c in chs if cat != "API"]
print("NexusChainAgent — " + str(len(all_ch)) + " challenges", flush=True)
print("Mode: 3-step chain of thought\n", flush=True)
score = correct = 0

for c in all_ch:
    t0 = time.time()
    answer = chain_solve(c)
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
    else:
        print("XX " + c["name"], flush=True)
    time.sleep(0.5)

print("\nNexusChainAgent: " + str(correct) + "/" + str(len(all_ch)) + " — " + str(int(score)) + "pts", flush=True)
