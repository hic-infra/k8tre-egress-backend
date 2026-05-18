from fastapi import FastAPI, Response
from app.api import download_file, get_files
from app.settings import Settings
from fastapi.middleware.cors import CORSMiddleware

settings = Settings()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.fe_url],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/list")
def list_egress(projectid: str | None = None,
              userid: str | None = None,
              date_range: str | None = None):
    return {}

@app.get("/egress/{egress_id}")
async def get_egress(egress_id: str):
    return await get_files(egress_id)

@app.post("/egress/{egress_id}")
def set_egress(egress_id: str):
    pass

@app.get("/egress/{egress_id}/{file_id}")
async def get_egress(egress_id: str, file_id: str):
    content, content_type, content_disposition = await download_file(egress_id, file_id)

    headers = {
        "Content-Disposition": content_disposition or f'attachment; filename="{file_id}"'
    }

    return Response(content=content, media_type=content_type, headers=headers)
