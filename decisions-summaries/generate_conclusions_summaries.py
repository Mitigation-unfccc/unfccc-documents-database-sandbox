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

from sqlalchemy import select, or_
from sqlalchemy.orm import Session, selectinload

from init_db import engine

from data_models.document_core_representation import Block, DocumentCore
from data_models.document_organizational_representation import Document, Body

import pandas as pd

if __name__ == "__main__":
    # -- Get the conclusions documents --
    
    conclusions = {}
    with Session(engine) as session:
        rows = session.execute(
            select(Document)
            .join(Document.body)
            .options(
                selectinload(Document.core).selectinload(DocumentCore.blocks).selectinload(Block.paragraph),
                selectinload(Document.core).selectinload(DocumentCore.blocks).selectinload(Block.table),
            )
            .where(
                or_(
                    Body.symbol == "SBI",
                    Body.symbol == "SBSTA"
                )
            )
        ).scalars().all()

        for conclusion in rows:
            print(f"{conclusion.symbol} [{conclusion.id}]")
            blocks = [block for block in conclusion.core.blocks]
            text = ""
            for block in blocks:
                if block.paragraph:
                    if block.numbering:
                        text += f"{block.numbering.strip()}\t"
                    text += f"{block.paragraph.text.strip()}\n"
                elif block.table:
                    if block.table.caption:
                        text += f"{block.table.caption.strip()}\n"
                    text += f"{block.table.cells_text}\n"
            
            conclusions[conclusion.symbol] = text
    
    # -- Get the conclusions summaries --
    
    # Agents initialization
    CONCLUSION_SUMMARY_SYSTEM_PROMPT = """
Your task is to distill official conclusions of the SBI and SBSTA of the UNFCCC into exactly 3 sentences that capture the essential substance and purpose, in a consistent, clear, neutral, and factual manner.

# **Content Prioritization**:
First sentence: Identify the core purpose of the conclusion and the adopting body - what fundamental issue or mechanism does this conclusion address?
Second sentence: Highlight the most significant operational element - what concrete action, timeline, or institutional arrangement is being established?
Third sentence: Capture the broader significance or primary implementation mechanism - how does this conclusion advance climate action or governance?

# **Drafting Requirements**:
- Produce exactly 3 complete, standalone sentences - no more, no less. The first sentence should always contain the conclusion symbol mentioned (e.g "Conclusion FCCC/SBSTA/2024/7")
- Each sentence must be clear, concise, and factually accurate.
- Focus exclusively on the most substantive and consequential elements.
- Prioritize explaining what the conclusion accomplishes over listing what it says.
- Use precise institutional terminology while maintaining accessibility.
- Prefer present tense and formal UN tone.
- Always use the abbreviations of bodies only (even the first time they appear, to save up output length, e.g. instead of "Conference of the Parties" use just "COP").
- Maintain neutral phrasing. (e.g. use the style "The conclusion talks about loss and damage and authorization " and do not say " The CMA decided that...")

# **Quality Standards Remarks**:
- Precision: Every word must carry significant informational value.
- Comprehensiveness: Despite brevity, capture the conclusion's essential purpose and mechanism.
- Neutrality: No interpretive or evaluative language.
- Clarity: Each sentence should be immediately understandable to someone familiar with UNFCCC processes.

# **Output format**:
Provide only three sentences with no additional commentary, headings, or formatting.
"""
    CONCLUSION_SUMMARY_USER_PROMPT = "{conclusion}"
    class ConclusionSummaryAgentResponse(BaseModel):
        summary: str = Field(description="The summary of the conclusion.")

    conclusion_summary_agent: Runnable = ChatOpenAI(model="gpt-5-mini", temperature=0.0).with_structured_output(ConclusionSummaryAgentResponse)
    conclusion_summary_agent_message: ChatPromptTemplate = ChatPromptTemplate(
        messages=[("system", CONCLUSION_SUMMARY_SYSTEM_PROMPT), ("user", CONCLUSION_SUMMARY_USER_PROMPT)]
    )
    
    # Call the agents to get the conclusion summaries
    messages = []
    for conclusion_symbol, conclusion_text in conclusions.items():
        messages.append(conclusion_summary_agent_message.format_messages(conclusion=f"{conclusion_symbol}\n{conclusion_text}"))
        break

    cost = 0.0
    with get_openai_callback() as cb:
        responses_conclusion_summary: list[ConclusionSummaryAgentResponse] = conclusion_summary_agent.batch(messages)
        cost += cb.total_cost
        print("Summaries generated", f"{cost=}")
    
    results = []
    for i, (conclusion_symbol, _) in enumerate(conclusions.items()):
        results.append({
            "symbol": conclusion_symbol,
            "summary": responses_conclusion_summary[i].summary.strip()
        })
        if i+1 >= len(responses_conclusion_summary): break # Just for when we want to run a subset
    
    df = pd.DataFrame(results)
    df.to_csv("conclusion_summaries.csv", encoding="utf-8")
