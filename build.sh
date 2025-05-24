#!/bin/bash

# Install Python dependencies
pip install -r requirements.txt

# Initialize migrations directory if it doesn't exist
flask db init

# Generate migration
flask db migrate -m "Initial migration"

# Apply migrations
flask db upgrade

# Create admin user
python create_admin.py

# Run any other necessary setup scripts
python init_data.py

# Update permissions
python update_all_permissions.py 