#!/usr/bin/env bash
set -e # stop if any command fails

UNFCCC_DOCUMENTS_DATABASE_PATH="/home/dbs/unfccc-documents-database"

# Create the python virtual environment (if it does not already exist)
if [ ! -d ".venv" ]; then
	echo "Creating python virtual environment in .venv..."
	python3 -m venv ".venv"
fi

# Activate the venv
source ".venv/bin/activate"

# Install the unfccc documents database package in editiable mode
echo "Installing unfccc-documents-database from $UNFCCC_DOCUMENTS_DATABASE_PATH in editable mode..."
pip install -e "$UNFCCC_DOCUMENTS_DATABASE_PATH"
pip install -r "$UNFCCC_DOCUMENTS_DATABASE_PATH/requirements.txt"

echo "Setup complete: python virtual environment ready with unfccc-documents-database package installed."
