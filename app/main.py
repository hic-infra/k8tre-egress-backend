from fastapi import FastAPI
from app.settings import Settings

settings = Settings()
app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/list")
def list_egress(projectid: str | None = None,
              userid: str | None = None,
              date_range: str | None = None):
    return {}

@app.get("/egress/{egress_id}")
def get_egress(egress_id: str):
    pass

@app.post("/egress/{egress_id}")
def set_egress(egress_id: str):
    pass
