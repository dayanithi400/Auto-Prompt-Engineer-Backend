import os
import json
import re
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from prompt_template import system_prompt, system_prompt_poml, system_prompt_image, system_prompt_video

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise ValueError("Missing OPENROUTER_API_KEY in .env file")

app = FastAPI()

# Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PromptRequest(BaseModel):
    problem: str

llm = ChatOpenAI(
    model_name="mistralai/mistral-7b-instruct",
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=OPENROUTER_API_KEY,
    max_tokens=2000,
    temperature=0.3
)

@app.post("/generate_prompt")
async def generate_prompt(req: PromptRequest):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": req.problem}
    ]

    try:
        response = llm.invoke(messages)
        content = response.content.strip()

        data = extract_json(content)
        if not data:
            return JSONResponse(
                status_code=400,
                content={"error": "Model did not return valid JSON.", "raw_output": content}
            )

        few_shots_text = ""
        for i, example in enumerate(data.get("few_shots", []), start=1):
            few_shots_text += f"Example {i}:\nInput: {example['input']}\nOutput: {example['output']}\n\n"

        structured_prompt = f"""
[Role]
{data['role']}

[Task]
{data['task']}

[Context]
{data['context']}

[Reasoning Instruction]
{data['reasoning_instruction']}

[Few Shots]
{few_shots_text.strip()}

[Output Format]
{data['output_format']}

[Stop Conditions]
{data['stop_conditions']}
"""
        return {"structured_prompt": structured_prompt}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/generate_poml")
async def generate_poml(req: PromptRequest):
    messages = [
        {"role": "system", "content": system_prompt_poml},
        {"role": "user", "content": req.problem}
    ]
    try:
        response = llm.invoke(messages)
        content = response.content.strip()
        if not content.startswith("<POML>"):
            return JSONResponse(
                status_code=400,
                content={"error": "Model did not return valid POML.", "raw_output": content}
            )
        return {"poml_prompt": content}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/generate_image_json")
async def generate_image_json(req: PromptRequest):
    messages = [
        {"role": "system", "content": system_prompt_image},
        {"role": "user", "content": req.problem}
    ]
    try:
        response = llm.invoke(messages)
        content = response.content.strip()
        data = extract_json(content)
        if not data:
            return JSONResponse(
                status_code=400,
                content={"error": "Model did not return valid JSON.", "raw_output": content}
            )
        return {"image_prompt_json": data}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/generate_video_json")
async def generate_video_json(req: PromptRequest):
    messages = [
        {"role": "system", "content": system_prompt_video},
        {"role": "user", "content": req.problem}
    ]
    try:
        response = llm.invoke(messages)
        content = response.content.strip()
        data = extract_json(content)
        if not data:
            return JSONResponse(
                status_code=400,
                content={"error": "Model did not return valid JSON.", "raw_output": content}
            )
        return {"video_prompt_json": data}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

def extract_json(text):
    # Try to find JSON in the text
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return None
    return None

@app.get("/")
def home():
    return {"status": "Backend is running!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)