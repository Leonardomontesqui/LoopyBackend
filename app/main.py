from fastapi import FastAPI
# from dotenv import load_dotenv 
# from agents import Agent, Runner, trace
app = FastAPI()

@app.get("/")
async def hello():
    return {"message": "Hello from uv + FastAPI!"}