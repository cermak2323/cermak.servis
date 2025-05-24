#!/bin/bash

# Install Python dependencies
pip install -r requirements.txt

# Create database tables
python create_tables.py

# Create admin user
python create_admin.py

# Run any other necessary setup scripts
python init_data.py 