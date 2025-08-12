import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from prompt_template import system_prompt
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise ValueError("Missing OPENROUTER_API_KEY in .env file")

app = FastAPI()

# Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProblemRequest(BaseModel):
    problem: str

llm = ChatOpenAI(
    model_name="mistralai/mistral-7b-instruct",
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=OPENROUTER_API_KEY,
    max_tokens=2000,
    temperature=0.3
)

@app.post("/generate_prompt")
async def generate_prompt(req: ProblemRequest):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": req.problem}
    ]

    try:
        response = llm.invoke(messages)
        content = response.content.strip()

        data = extract_json(content)
        if not data:
            return {"error": "Model did not return valid JSON.", "raw_output": content}

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
        return {"error": str(e)}

import re

def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return None
    return None
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)