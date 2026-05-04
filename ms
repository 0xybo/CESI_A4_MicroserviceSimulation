#!/bin/zsh

# Activate the virtual environment if it exists and if we're not already in one
if [ -z "$VIRTUAL_ENV" ] && [ -f "venv/bin/activate" ]; then
    source "venv/bin/activate"
fi

# Run the main Python script with all arguments passed to this shell script
python -m src "$@"