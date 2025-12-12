from fastapi import FastAPI
app = FastAPI()
@app.get("/users/{id}")
def get_user(id: int): return {"id": id}