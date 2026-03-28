import requests, subprocess, tempfile, os, time, json, re
from dotenv import load_dotenv
load_dotenv("/data/data/com.termux/files/home/NexusLIFE/.env")
GROQ_KEY = os.getenv("GROQ_API_KEY","")
BASE = "http://localhost:8001"
AGENT = "NexusCodeAgent"

def ask_llm(prompt):
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": "Bearer " + GROQ_KEY},
        json={"model":"llama-3.3-70b-versatile",
              "messages":[{"role":"user","content":prompt}],
              "max_tokens":300,"temperature":0},timeout=20)
    if r.ok: return r.json()["choices"][0]["message"]["content"].strip()
    return None

def execute_python(code, timeout=5):
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            fname = f.name
        result = subprocess.run(["python3", fname],
            capture_output=True, text=True, timeout=timeout)
        os.unlink(fname)
        return result.stdout.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", 1
    except Exception as e:
        return str(e), 1

def solve(challenge):
    desc = challenge["description"]
    cat = challenge["category"]
    if cat in ["Code", "Math", "Algorithm", "Code Execution", "Crypto"]:
        prompt = "Solve this challenge by writing Python code that prints ONLY the answer.\n\nChallenge: " + desc + "\n\nWrite ONLY a Python code block:"
        response = ask_llm(prompt)
        if response:
            m = re.search(r"```python\n(.*?)```", response, re.DOTALL)
            if not m:
                m = re.search(r"```\n(.*?)```", response, re.DOTALL)
            if m:
                out, rc = execute_python(m.group(1))
                if rc == 0 and out:
                    return out, "code"
    prompt = "Return ONLY exact answer. No explanation.\n\nTask: " + desc + "\n\nANSWER:"
    return ask_llm(prompt), "direct"

requests.post(BASE + "/register", json={"agent_name": AGENT})
challenges = requests.get(BASE + "/challenges").json()
all_ch = [c for cat,chs in challenges["categories"].items() for c in chs if cat != "API"]
print("NexusCodeAgent — " + str(len(all_ch)) + " challenges")
score = correct = code_used = 0
for c in all_ch:
    t0 = time.time()
    answer, method = solve(c)
    ms = int((time.time()-t0)*1000)
    if not answer: continue
    answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.DOTALL).strip()
    try: parsed = json.loads(answer)
    except: parsed = answer.strip(chr(34)).strip(chr(39))
    r = requests.post(BASE + "/submit", json={
        "agent_name":AGENT,"challenge_id":c["id"],"answer":parsed,"time_ms":ms})
    if r.status_code == 200:
        res = r.json()
        if res.get("correct"):
            score += res.get("score_earned",0)
            correct += 1
            if method == "code": code_used += 1
            print("OK [" + method + "] " + c["name"] + " +" + str(res["score_earned"]) + "pts")
        else:
            print("XX [" + method + "] " + c["name"])
    time.sleep(0.4)
print("\nNexusCodeAgent: " + str(correct) + "/" + str(len(all_ch)) + " — " + str(int(score)) + "pts")
print("Code execute: " + str(code_used) + " fois")
