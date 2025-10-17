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
from sqlalchemy.orm import Session, selectinload

from init_db import engine

from data_models.document_core_representation import Block
from data_models.document_specific_representation import Decision, DecisionBlockMap

import pandas as pd

if __name__ == "__main__":
    # -- Get the decision documents --

    decisions = {}
    with Session(engine) as session:
        rows = session.execute(
            select(Decision)
            .options(
                selectinload(Decision.decision_blocks_map).selectinload(DecisionBlockMap.block).selectinload(Block.paragraph),
                selectinload(Decision.decision_blocks_map).selectinload(DecisionBlockMap.block).selectinload(Block.table),
            )
        ).scalars().all()

        for decision in rows:
            print(f"{decision.symbol} [{decision.id}]")
            blocks = [decision_block_map.block for decision_block_map in decision.decision_blocks_map]
            text = ""
            for block in blocks:
                if block.paragraph:
                    if block.numbering:
                        text += f"{block.numbering.strip}\t"
                    text += f"{block.paragraph.text.strip()}\n"
                elif block.table:
                    if block.table.caption:
                        text += f"{block.table.caption.strip()}\n"
                    text += f"{block.table.cells_text}\n"
            
            decisions[decision.symbol] = text
    
    # -- Get the decisions summaries --
    
    # Agents initialization
    DECISION_SUMMARY_SYSTEM_PROMPT = """
Your task is to distill official decisions of the COP, CMA, and CMP of the UNFCCC into exactly 3 sentences that capture the essential substance and purpose, in a consistent, clear, neutral, and factual manner.

# **Content Prioritization**:
 
First sentence: Identify the core purpose of the decision and the adopting body - what fundamental issue or mechanism does this decision address?
Second sentence: Highlight the most significant operational element - what concrete action, timeline, or institutional arrangement is being established?
Third sentence: Capture the broader significance or primary implementation mechanism - how does this decision advance climate action or governance?
 
# **Drafting Requirements**:
 
Produce exactly 3 complete, standalone sentences - no more, no less
Each sentence must be clear, concise, and factually accurate
Focus exclusively on the most substantive and consequential elements
Prioritize explaining what the decision accomplishes over listing what it says
Use precise institutional terminology while maintaining accessibility
 
# **Quality Standards Remarks**:
- Prefer present tense and formal UN tone.
- Maintain neutral phrasing. (e.g. use the style "The decision talks about loss and damage and authorization " and do not say " The CMA decided that...")
- Precision: Every word must carry significant informational value
- Comprehensiveness: Despite brevity, capture the decision's essential purpose and mechanism
- Neutrality: No interpretive or evaluative language
- Clarity: Each sentence should be immediately understandable to someone familiar with UNFCCC processes

# **Output format**:
Provide only three sentences with no additional commentary, headings, or formatting.
"""
    DECISION_SUMMARY_USER_PROMPT = "{decision}"
    class DecisionSummaryAgentResponse(BaseModel):
        summary: str = Field(description="The summary of the decision.")

    decision_summary_agent: Runnable = ChatOpenAI(model="gpt-5-mini", temperature=0.0).with_structured_output(DecisionSummaryAgentResponse)
    decision_summary_agent_message: ChatPromptTemplate = ChatPromptTemplate(
        messages=[("system", DECISION_SUMMARY_SYSTEM_PROMPT), ("user", DECISION_SUMMARY_USER_PROMPT)]
    )
    
    # Call the agents to get the decision summaries
    messages = []
    for decision_symbol, decision_text in decisions.items():
        messages.append(decision_summary_agent_message.format_messages(decision=decision_text))
        break

    cost = 0.0
    with get_openai_callback() as cb:
        responses_decision_summary: list[DecisionSummaryAgentResponse] = decision_summary_agent.batch(messages)
        cost += cb.total_cost
        print("Generated summaries", f"{cost=}")
    
    results = []
    for i, (decision_symbol, _) in enumerate(decisions.items()):
        results.append({
            "symbol": decision_symbol,
            "summary": responses_decision_summary[i].summary.strip()
        })
        if i+1 < len(responses_decision_summary): break
    
    df = pd.DataFrame(results)
    df.to_csv("decision_summaries.csv", encoding="utf-8")
        