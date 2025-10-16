import os
from dotenv import load_dotenv

if load_dotenv(".env"):
    key: str | None = os.getenv("OPENAI_API_KEY")
    if key is not None:
        os.environ["OPENAI_API_KEY"] = key
    else:
        raise ValueError("OPENAI_API_KEY not found in the .env file")
else:
    raise ValueError("(.env NOT FOUND) Please set up the .env file")

from typing import Optional
from pydantic import BaseModel, Field

from langchain_core.runnables import Runnable
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langchain_community.callbacks.manager import get_openai_callback
from langchain.prompts import ChatPromptTemplate

from sqlalchemy import select
from sqlalchemy.orm import Session

from init_db import engine
from data_models.document_organizational_representation import Document
from data_models.document_specific_representation import Decision

if __name__ == "__main__":
    with Session(engine) as session:
        rows = session.execute(
            select(Decision, Document)
            .join(Decision.document)
        )
        for decision, document in rows:
            print(f"{decision.symbol} [{decision.id}] ({document.symbol} [{document.id}])")
    
    # -- Get the decision documents --

    #

    
    # # -- Get the decisions summaries --
    
    # # Agents initialization
    
    # class DecisionSummaryAgentResponse(BaseModel):
    #     summary: str = Field(description="The summary of the decision.")
    # DECISION_SUMMARY_SYSTEM_PROMPT = """
    # """
    # DECISION_SUMMARY_USER_PROMPT = "{decision}"

    # decision_summary_agent: Runnable = ChatOpenAI(model="gpt-5-mini", temperature=0.0).with_structured_output(DecisionSummaryAgentResponse)
    # decision_summary_agent_message: ChatPromptTemplate = ChatPromptTemplate(
    #     messages=[("system", DECISION_SUMMARY_SYSTEM_PROMPT), ("user", DECISION_SUMMARY_USER_PROMPT)]
    # )
    
    # # Call the agents to get the decision summaries
    # cost = 0.0
    # with get_openai_callback() as cb:
    #     responses_decision_summary: list[DecisionSummaryAgentResponse] = decision_summary_agent.batch(messages)
    #     cost += cb.total_cost
