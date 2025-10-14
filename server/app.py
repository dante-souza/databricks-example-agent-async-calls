import logging
from typing import Annotated, Any
from fastapi import Depends, FastAPI, BackgroundTasks
from pydantic import BaseModel, ValidationError
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import (
    ChatMessage,
    ChatMessageRole,
)
from dotenv import load_dotenv
import uuid

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.info("Logger initialized successfully!")

load_dotenv()

ENDPOINT_NAME = os.getenv("SERVING_ENDPOINT_NAME")

if not ENDPOINT_NAME:
    logger.error("SERVING_ENDPOINT_NAME environment variable is not set")
    raise ValueError("SERVING_ENDPOINT_NAME environment variable is not set")

app = FastAPI()
ui_app = StaticFiles(directory="client/build", html=True)
api_app = FastAPI()

# PLEASE NOTE THE ORDER OF THE MOUNTS MATTERS
app.mount("/api", api_app)
app.mount("/", ui_app)

origins = [
    "http://localhost:3000",
]

# Make sure CORS is applied to both app and api_app
# This is only needed for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# client
def client():
    return WorkspaceClient()


# Model for the request body
class ChatRequest(BaseModel):
    question: str


# Simplified response model
class ChatResponse(BaseModel):
    question_id: str

#################################################


import os
import time

import pandas as pd
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from sqlalchemy import create_engine, event, text

app_config = Config()
workspace_client = WorkspaceClient()

postgres_username = app_config.client_id
postgres_host = os.getenv("PGHOST")
postgres_port = 5432
postgres_database = "databricks_postgres"

postgres_pool = create_engine(f"postgresql+psycopg://{postgres_username}:@{postgres_host}:{postgres_port}/{postgres_database}")

@event.listens_for(postgres_pool, "do_connect")
def provide_token(dialect, conn_rec, cargs, cparams):
    """Provide the App's OAuth token. Caching is managed by WorkspaceClient"""
    cparams["password"] = workspace_client.config.oauth_token().access_token


class QuestionRequest(BaseModel):
    question: str

class StartConversationResponse(BaseModel):
    question_id: str


def insert_status(question_id, question, status, answer=""):
    """Update the status and manager note for a specific holiday request."""
    with postgres_pool.begin() as conn:
        conn.execute(
            text("""INSERT INTO public.requests_test (question_id, question, status, answer) VALUES (:question_id, :question, :status, :answer)"""),
            {"question_id": question_id, "question": question, "status": status, "answer": answer}
        )

def update_status(question_id, status, answer):
    """Update the status and manager note for a specific holiday request."""
    with postgres_pool.begin() as conn:
        conn.execute(
            text("""UPDATE public.requests_test SET status = :status, answer = :answer WHERE question_id = :question_id""")
            , {"question_id": question_id, "status": status, "answer": answer}
        )


def call_agent(question, question_id):
    response = workspace_client.serving_endpoints.query(
        ENDPOINT_NAME,
        messages=[ChatMessage(content=question, role=ChatMessageRole.USER)],
    )
    agent_answer = response.choices[0].message.content
    update_status(question_id, "Done", agent_answer)



@api_app.post("/start-conversation", response_model=ChatResponse)
async def start_conversation(request: ChatRequest, background_tasks: BackgroundTasks):
    question_id = str(uuid.uuid4())
    background_tasks.add_task(call_agent, request.question, question_id)
    insert_status(question_id, request.question, "Processing")
    return {"question_id": question_id}

@api_app.get("/get-status/{question_id}")
def get_status(question_id: str):
    with postgres_pool.begin() as conn:
        result = conn.execute(
            text("SELECT status FROM public.requests_test WHERE question_id = :question_id"),
            {"question_id": question_id},
        ).fetchone()
    if result and result[0] == "Done":
        return True
    else:
        return False

    
@api_app.get("/get-answer/{question_id}")
def get_answer(question_id: str):
    with postgres_pool.begin() as conn:
        result = conn.execute(
            text("SELECT answer FROM public.requests_test WHERE question_id = :question_id"),
            {"question_id": question_id},
        ).fetchone()
    return result[0] if result else ""


    

