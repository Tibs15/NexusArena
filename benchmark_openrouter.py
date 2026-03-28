import requests, os, time, json, re
from dotenv import load_dotenv
load_dotenv('/data/data/com.termux/files/home/NexusLIFE/.env')
KEY = os.getenv('OPENROUTER_API_KEY','')
BASE = "http://localhost:8001"

def clean(t):
    if not t: return ""
    t = re.sub(r'<think>.*?</think>', '', str(t), flags=re.DOTALL)
    return re.sub(r"```[a-zA-Z]*\n?","",t).replace("```","").strip()

def ask(desc, model):
    try:
        r = requests.post('https://openrouter.ai/api/v1/chat/completions',
            headers={'Authorization': 'Bearer ' + KEY},
            json={'model':model,
                  'messages':[{'role':'user','content':
                    'Return ONLY exact answer. No explanation. No thinking.\n\nTask: ' + desc + '\n\nANSWER:'}],
                  'max_tokens':100},timeout=25)
        if r.ok:
            content = r.json()['choices'][0]['message'].get('content','')
            return content
    except: pass
    return None

agents = [
    ('Nemotron_120B', 'nvidia/nemotron-3-super-120b-a12b:free'),
    ('GLM_4_5_Air',   'z-ai/glm-4.5-air:free'),
    ('Step35_Flash',  'stepfun/step-3.5-flash:free'),
]

challenges = requests.get(BASE + '/challenges').json()
all_ch = [c for cat,chs in challenges['categories'].items() for c in chs if cat != 'API']
print(f'OpenRouter benchmark — {len(all_ch)} challenges · {len(agents)} agents', flush=True)

for agent, model in agents:
    requests.post(BASE + '/register', json={'agent_name': agent})
    score = correct = 0
    print(f'\n{agent}...', flush=True)
    for c in all_ch:
        t0 = time.time()
        answer = ask(c['description'], model)
        ms = int((time.time()-t0)*1000)
        if not answer: continue
        cleaned = clean(answer)
        try: parsed = json.loads(cleaned)
        except: parsed = cleaned.strip('"').strip("'")
        r = requests.post(BASE + '/submit', json={
            'agent_name':agent,'challenge_id':c['id'],
            'answer':parsed,'time_ms':ms})
        if r.status_code == 200 and r.json().get('correct'):
            score += r.json().get('score_earned',0)
            correct += 1
        time.sleep(1.5)
    print(f'{agent}: {correct}/{len(all_ch)} — {score:.0f}pts', flush=True)

print('\nDONE', flush=True)
