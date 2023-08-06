import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from app1 import user_router, create_db_tables

create_db_tables()

app = FastAPI()
app.include_router(user_router)

app.get(path='/', response_class=HTMLResponse)
def hello():
    hello_str = "<h1>Hello FastAPI !</h1>"
    return HTMLResponse(content=hello_str)

if __name__ == "__main__":
    port = 8100
    uvicorn.run("main:app", port=port, log_level="info")
