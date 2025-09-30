# backend/db_utils.py

import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "$sujCHER2956"),
        database=os.getenv("DB_NAME", "ignitiondb")
    )

def get_machine_details(machine_id: int):
    """Fetch machine details from MySQL"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT machine_id, machine_name, machine_type, location, manufacturer, install_date, status
        FROM machines
        WHERE machine_id = %s
    """
    cursor.execute(query, (machine_id,))
    row = cursor.fetchone()

    cursor.close()
    conn.close()

    if not row:
        return f"⚠️ No details found for Machine {machine_id}"

    # Format with nice markdown for dashboard
    return f"""
    📌 **Machine {row['machine_id']} Details**  
    - 🔖 Name: {row['machine_name']}  
    - ⚙️ Type: {row['machine_type']}  
    - 📍 Location: {row['location']}  
    - 🏭 Manufacturer: {row['manufacturer']}  
    - 📅 Installed on: {row['install_date']}  
    """
