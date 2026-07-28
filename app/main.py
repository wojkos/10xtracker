from fastapi import FastAPI

from app import api
from app.mcp import add_mcp_transport

app = FastAPI()
app.include_router(api.router, prefix="/api")
add_mcp_transport(app)
app.frontend("/", directory="dist")
