
from sqlalchemy import inspect

from init_db import engine

inspector = inspect(engine)
print(inspector.get_table_names())
