import uvicorn, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from arena import app, init_db
init_db()
uvicorn.run(app, host="0.0.0.0", port=8001)
