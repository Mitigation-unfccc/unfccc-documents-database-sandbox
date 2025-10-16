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
Your task is to summarize official decisions of the COP, CMA, and CMP of the UNFCCC in a consistent, clear, neutral, and factual manner.

# **Detailed instructions**:
1. *Read the full decision text carefully to identify*:
- The adopting body (COP, CMA, or CMP)
- The objective or intent of the decision
- The main actions, provisions, or mandates
- Any follow-up mechanisms, reporting requests, or deadlines
- The formal reference (which will be the title of the decision)

2. *Write a concise summary in no more than 200 words in continuous paragraph(s) form.*

3. *Do not interpret or evaluate. Avoid political or speculative language stay strictly factual and descriptive.*

4. *Use consistent institutional language*:
- Refer to actors as “Parties”, “the Secretariat”, “the Conference of the Parties”, etc.
- Use the verbs present in the decisions paragraphs.
- Prefer present tense and formal UN tone.
- Maintain neutral phrasing.
- Try to exclude preambular text, contextual rhetoric, or debates summarize only the operative content, unless needed.

# **Quality standard remarks**:
- Consistency: Each summary must adhere to a uniform structure, tone, and terminology across all outputs to ensure institutional consistency and comparability.
- Neutrality: No interpretation, opinions, or inferred meaning.
- Clarity: Sentences are short, precise, and written in standard UN English.
- Completeness: All key actions and responsible entities are mentioned.

# **Output format**:
The output consists only of the summarized text, written as cohesive paragraph(s) (split into a second paragraph only if absolutely necessary for readability).
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
        print("Summaries generated", f"{cost=}")
    
    results = []
    for i, (decision_symbol, _) in enumerate(decisions.items()):
        results.append({
            "symbol": decision_symbol,
            "summary": responses_decision_summary[i].summary.strip()
        })
        if i+1 >= len(responses_decision_summary): break
    
    df = pd.DataFrame(results)
    df.to_csv("decision_summaries.csv", encoding="utf-8")
        
