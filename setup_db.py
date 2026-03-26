"""
Database setup script - creates the MySQL database.
Run: python setup_db.py
"""
import pymysql  # type: ignore
from dotenv import load_dotenv  # type: ignore
import os
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "bvrit_bus_db")

try:
    conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD)
    cursor = conn.cursor()
    cursor.execute(f"DROP DATABASE IF EXISTS `{DB_NAME}`")
    cursor.execute(f"CREATE DATABASE `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    print(f"Database '{DB_NAME}' created successfully!")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error creating database: {e}")
