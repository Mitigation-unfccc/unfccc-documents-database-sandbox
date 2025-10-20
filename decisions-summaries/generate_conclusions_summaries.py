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
    
    print(conclusions["FCCC/SBSTA/2024/7"])
