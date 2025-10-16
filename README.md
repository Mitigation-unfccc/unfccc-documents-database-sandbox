# Guidelines
## Installing the virtual environment
- Each experiment or analysis must be placed in a subfolder, with its individual environment so as to not contaminate other experiments.

It is important to move to the subfolder and trigger the setup script from there.
```
cd project
../setup_venv_with_unfccc_documents_database.sh
source .venv/bin/activate
```

## Usage
- In order to use the necessary utils from the unfccc documents database repo, just import them as if you were working inside that folder

To establish the db connection:
```
from init_db import engine
```

To import the data models of the db:
```
from data_models.document_organizational_representation.py import Document
```
