import os


# Get the directory of the current script (backend folder)
current_dir = os.path.dirname(os.path.abspath(__file__))

# Construct and normalize the path to the database (../data/incidents.db)
DB_PATH = os.path.normpath(os.path.join(current_dir, '..', 'data', 'incidents.db'))