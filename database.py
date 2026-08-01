import os
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

DB_NAME = os.getenv("DB_NAME", "neurovoice")
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "autocommit": True,
}


def get_connection():
    config = dict(DB_CONFIG)
    config["database"] = DB_NAME
    return mysql.connector.connect(**config)


def init_db():
    base_config = dict(DB_CONFIG)
    conn = mysql.connector.connect(**base_config)
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    cursor.execute(f"USE {DB_NAME}")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS progress (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT UNIQUE NOT NULL,
            words INT DEFAULT 0,
            images INT DEFAULT 0,
            phrases INT DEFAULT 0,
            correct INT DEFAULT 0,
            attempts INT DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS practice_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            practice_type VARCHAR(50) NOT NULL,
            item_name VARCHAR(100) NOT NULL,
            user_text TEXT NOT NULL,
            target_text TEXT NOT NULL,
            accuracy_score INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            practice_type VARCHAR(50) NOT NULL,
            total_attempts INT DEFAULT 0,
            total_correct INT DEFAULT 0,
            average_accuracy INT DEFAULT 0,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    cursor.close()
    conn.close()
