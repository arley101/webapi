# main.py  (en la raíz del repo)
from app.main import app  # importa el FastAPI que ya tienes dentro de /app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)