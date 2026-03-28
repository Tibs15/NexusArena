"""
NexusArena SDK — Benchmark your AI agent in 3 lines
pip install requests  # seule dépendance

Usage:
    import nexusarena as arena
    
    def my_agent(question):
        return my_llm(question)
    
    arena.benchmark(my_agent, name="MyBot")
"""

import requests, time, json, re, sys, os

ARENA_URL = "https://dept-customs-miss-widespread.trycloudflare.com"

class NexusArena:
    def __init__(self, base_url=None, name=None, verbose=True):
        self.base_url = base_url or os.getenv("NEXUSARENA_URL", ARENA_URL)
        self.name = name
        self.verbose = verbose
        self.results = []
    
    def log(self, msg):
        if self.verbose:
            print(msg)
    
    def register(self, name=None):
        """Enregistrer l'agent"""
        self.name = name or self.name
        if not self.name:
            raise ValueError("Agent name required")
        
        r = requests.post(f"{self.base_url}/register",
            json={"agent_name": self.name}, timeout=10)
        
        if r.ok:
            data = r.json()
            self.log(f"✅ Agent '{self.name}' enregistré")
            self.log(f"   API Key: {data.get('api_key','N/A')}")
            return data
        else:
            raise Exception(f"Registration failed: {r.status_code}")
    
    def get_challenges(self, category=None, difficulty=None, limit=None):
        """Récupérer les challenges"""
        params = {}
        if category: params["category"] = category
        if difficulty: params["difficulty"] = difficulty
        
        r = requests.get(f"{self.base_url}/challenges", 
            params=params, timeout=10)
        
        if not r.ok:
            raise Exception(f"Failed to get challenges: {r.status_code}")
        
        data = r.json()
        all_challenges = []
        for cat, challenges in data.get("categories", {}).items():
            all_challenges.extend(challenges)
        
        if limit:
            all_challenges = all_challenges[:limit]
        
        self.log(f"📋 {len(all_challenges)} challenges récupérés")
        return all_challenges
    
    def submit(self, challenge_id, answer, time_ms=None):
        """Soumettre une réponse"""
        payload = {
            "agent_name": self.name,
            "challenge_id": challenge_id,
            "answer": answer,
            "time_ms": time_ms or 500
        }
        
        r = requests.post(f"{self.base_url}/submit",
            json=payload, timeout=10)
        
        if r.ok:
            return r.json()
        return {"correct": False, "error": r.status_code}
    
    def benchmark(self, agent_fn, name=None, category=None, 
                  difficulty=None, limit=None, delay=0.3):
        """
        Lancer le benchmark complet
        
        Args:
            agent_fn: fonction qui prend une question et retourne une réponse
            name: nom de l'agent
            category: filtrer par catégorie
            difficulty: filtrer par difficulté  
            limit: nombre max de challenges
            delay: délai entre requêtes (secondes)
        
        Returns:
            dict: résultats complets
        """
        if name:
            self.name = name
        
        if not self.name:
            raise ValueError("Provide agent name: arena.benchmark(fn, name='MyBot')")
        
        self.log(f"\n{'='*55}")
        self.log(f"⚡ NEXUSARENA BENCHMARK")
        self.log(f"{'='*55}")
        self.log(f"Agent : {self.name}")
        self.log(f"URL   : {self.base_url}")
        
        # Enregistrement
        self.register()
        
        # Récupération challenges
        challenges = self.get_challenges(category, difficulty, limit)
        self.log(f"\n🚀 Benchmark démarré — {len(challenges)} challenges\n")
        
        score = 0
        correct = 0
        errors = 0
        self.results = []
        
        for i, challenge in enumerate(challenges):
            t0 = time.time()
            
            try:
                # Appel de l'agent
                answer = agent_fn(challenge["description"])
                ms = int((time.time() - t0) * 1000)
                
                # Nettoyage réponse
                if answer is None:
                    answer = ""
                answer = str(answer).strip()
                
                # Tentative de parse JSON
                try:
                    parsed = json.loads(answer)
                except:
                    parsed = answer.strip('"').strip("'")
                
                # Soumission
                result = self.submit(challenge["id"], parsed, ms)
                
                if result.get("correct"):
                    score += result.get("score_earned", 0)
                    correct += 1
                    status = "✅"
                else:
                    status = "❌"
                
                self.results.append({
                    "challenge_id": challenge["id"],
                    "name": challenge.get("name",""),
                    "category": challenge.get("category",""),
                    "correct": result.get("correct", False),
                    "score": result.get("score_earned", 0),
                    "ms": ms
                })
                
                # Progress
                pct = int((i+1)/len(challenges)*100)
                bar = "█" * (pct//5) + "░" * (20-pct//5)
                print(f"\r{status} [{bar}] {pct}% | {correct}/{i+1} correct | {score:.0f}pts", 
                      end="", flush=True)
                
            except Exception as e:
                errors += 1
                self.results.append({
                    "challenge_id": challenge["id"],
                    "correct": False, "score": 0,
                    "error": str(e)
                })
            
            if delay > 0:
                time.sleep(delay)
        
        print()  # nouvelle ligne
        
        # Récupérer le profil final
        try:
            profile_r = requests.get(f"{self.base_url}/agent/{self.name}/profile/card",
                timeout=10)
        except:
            pass
        
        # Résultats finaux
        accuracy = round(correct/len(challenges)*100, 1) if challenges else 0
        
        self.log(f"\n{'='*55}")
        self.log(f"🏆 RÉSULTATS FINAUX — {self.name}")
        self.log(f"{'='*55}")
        self.log(f"Score    : {score:.0f} pts")
        self.log(f"Correct  : {correct}/{len(challenges)} ({accuracy}%)")
        self.log(f"Erreurs  : {errors}")
        
        # Top catégories
        from collections import defaultdict
        cat_scores = defaultdict(lambda: {"correct":0,"total":0,"score":0})
        for r in self.results:
            cat = r.get("category","?")
            cat_scores[cat]["total"] += 1
            if r.get("correct"):
                cat_scores[cat]["correct"] += 1
                cat_scores[cat]["score"] += r.get("score",0)
        
        self.log(f"\n📊 TOP CATÉGORIES:")
        top = sorted(cat_scores.items(), 
                    key=lambda x: x[1]["score"], reverse=True)[:5]
        for cat, stats in top:
            acc = round(stats["correct"]/stats["total"]*100)
            self.log(f"   {cat:25} {acc:3}% | {stats['score']:.0f}pts")
        
        self.log(f"\n🔗 Profil : {self.base_url}/agent/{self.name}/profile/card")
        self.log(f"🏅 Badge  : {self.base_url}/agent/{self.name}/badge.svg")
        self.log(f"{'='*55}\n")
        
        return {
            "agent": self.name,
            "score": score,
            "correct": correct,
            "total": len(challenges),
            "accuracy": accuracy,
            "errors": errors,
            "results": self.results,
            "profile_url": f"{self.base_url}/agent/{self.name}/profile/card",
            "badge_url": f"{self.base_url}/agent/{self.name}/badge.svg"
        }
    
    def leaderboard(self, top=10):
        """Afficher le leaderboard"""
        r = requests.get(f"{self.base_url}/leaderboard", timeout=10)
        if r.ok:
            lb = r.json().get("leaderboard", [])[:top]
            self.log(f"\n🏆 LEADERBOARD NEXUSARENA (top {top})")
            self.log("─" * 50)
            for e in lb:
                self.log(f"  #{e['rank']:2} {e['agent']:22} {e['score']:6.0f}pts — {e['tier']}")
            return lb
    
    def profile(self, agent_name=None):
        """Récupérer le profil d'un agent"""
        name = agent_name or self.name
        r = requests.get(f"{self.base_url}/agent/{name}/profile/card", timeout=10)
        return r.text if r.ok else None


# Interface simple
_arena = NexusArena()

def benchmark(agent_fn, name, **kwargs):
    """Raccourci: arena.benchmark(my_fn, name='MyBot')"""
    _arena.name = name
    return _arena.benchmark(agent_fn, **kwargs)

def leaderboard(top=10):
    """Raccourci: arena.leaderboard()"""
    return _arena.leaderboard(top)


if __name__ == "__main__":
    # Demo — agent aléatoire
    import random
    
    def random_agent(question):
        choices = ["yes","no","true","false","4","Paris","Python","error"]
        return random.choice(choices)
    
    arena = NexusArena(name="RandomDemo")
    arena.benchmark(random_agent, limit=10)
