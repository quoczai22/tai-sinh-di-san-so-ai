from fastapi import FastAPI

app = FastAPI(title="Tai Sinh Di San So AI Backend")


@app.get("/health")
def health_check():
    return {"status": "ok"}
