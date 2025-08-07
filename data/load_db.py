# import os
# import pandas as pd
# import sqlite3

# # Path to the CSV file
# csv_path = os.path.join(os.path.dirname(__file__), 'servicenow_incidents.csv')

# # SQLite database path (store in backend directory for simplicity)
# db_path = os.path.join(os.path.dirname(__file__), 'incidents.db')

# try:
#     # Read the CSV file
#     df = pd.read_csv(csv_path)
    
#     # Connect to SQLite database (creates the file if it doesn't exist)
#     conn = sqlite3.connect(db_path)
#     cursor = conn.cursor()
    
#     # Create the incidents table
#     create_table_query = """
#     CREATE TABLE IF NOT EXISTS incidents (
#         ticket_id TEXT PRIMARY KEY,
#         short_description TEXT,
#         description TEXT,
#         priority TEXT,
#         close_notes TEXT,
#         known_solution TEXT,
#         root_cause TEXT
#     )
#     """
#     cursor.execute(create_table_query)
    
#     # Insert data from CSV into the table
#     for _, row in df.iterrows():
#         insert_query = """
#         INSERT OR REPLACE INTO incidents (ticket_id, short_description, description, priority, close_notes, known_solution, root_cause)
#         VALUES (?, ?, ?, ?, ?, ?, ?)
#         """
#         cursor.execute(insert_query, (
#             row['ticket_id'],
#             row['short_description'],
#             row['description'],
#             row['priority'],
#             row['close_notes'],
#             row['known_solution'],
#             row['root_cause']
#         ))
    
#     # Commit changes
#     conn.commit()
#     print(f"Successfully loaded {len(df)} rows into SQLite database at {db_path}")
    
#     # Verify data (optional)
#     cursor.execute("SELECT * FROM incidents LIMIT 5")
#     rows = cursor.fetchall()
#     print("Sample data from database:")
#     for row in rows:
#         print(row)

# except FileNotFoundError:
#     print(f"Error: CSV file not found at {csv_path}")
# except pd.errors.EmptyDataError:
#     print("Error: CSV file is empty")
# except sqlite3.Error as e:
#     print(f"Database error: {str(e)}")
# except Exception as e:
#     print(f"Unexpected error: {str(e)}")
# finally:
#     # Close the connection
#     if 'conn' in locals():
#         conn.close()

import pandas as pd

# Path to your CSV file
file_path = r'/home/juanhun/mcp-server-sample/data/short_incidents.csv'

# Read the CSV
df = pd.read_csv(file_path)

# Keep only the first two columns
df = df.iloc[:, :2]

# Overwrite the original file
df.to_csv(file_path, index=False)
 

