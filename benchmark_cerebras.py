import requests, os, time, json, re
from dotenv import load_dotenv
load_dotenv('/data/data/com.termux/files/home/NexusLIFE/.env')
KEY = os.getenv("CEREBRAS_API_KEY","")
BASE = "http://localhost:8001"

def clean(t):
    t = re.sub(r'<think>.*?</think>', '', str(t), flags=re.DOTALL)
    return re.sub(r"```[a-zA-Z]*\n?","",t).replace("```","").strip()

def ask(desc, model):
    r = requests.post("https://api.cerebras.ai/v1/chat/completions",
        headers={"Authorization": "Bearer " + KEY},
        json={"model":model,
              "messages":[{"role":"user","content":
                f"Return ONLY exact answer. No explanation. No markdown.\n\nTask: {desc}\n\nANSWER:"}],
              "max_tokens":150,"temperature":0},timeout=20)
    if r.ok: return r.json()["choices"][0]["message"]["content"].strip()
    return None

agents = [
    ("Cerebras_Qwen235B", "qwen-3-235b-a22b-instruct-2507"),
    ("Cerebras_Llama8B",  "llama3.1-8b"),
]

challenges = requests.get(f"{BASE}/challenges").json()
all_ch = [c for cat,chs in challenges["categories"].items()
          for c in chs if cat != "API"]
print(f"START — {len(all_ch)} challenges · {len(agents)} agents", flush=True)

for agent, model in agents:
    requests.post(f"{BASE}/register", json={"agent_name": agent})
    score = correct = 0
    print(f"\n{agent}...", flush=True)
    for c in all_ch:
        t0 = time.time()
        answer = ask(c["description"], model)
        ms = int((time.time()-t0)*1000)
        if not answer: continue
        cleaned = clean(answer)
        try: parsed = json.loads(cleaned)
        except: parsed = cleaned.strip('"').strip("'")
        r = requests.post(f"{BASE}/submit", json={
            "agent_name":agent,"challenge_id":c["id"],
            "answer":parsed,"time_ms":ms})
        if r.status_code == 200 and r.json().get("correct"):
            score += r.json().get("score_earned",0)
            correct += 1
        time.sleep(0.3)
    print(f"{agent}: {correct}/{len(all_ch)} — {score:.0f}pts", flush=True)

print("\nDONE", flush=True)
