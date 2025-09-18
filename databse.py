import psycopg2
import os
import uuid

class PostgresDB():

    def __init__(self):
        self.conn = psycopg2.connect(
            dbname='resume_screening',
            user='postgres',
            password='0000',
            port=5432
        )
    
    def connect(self):
        return self.conn.cursor()

    def create_table(self):
        cur = self.connect()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS resume_metadata (
            doc_id TEXT PRIMARY KEY,
            filename TEXT,
            file_path TEXT,
            uploaded_at TIMESTAMP DEFAULT NOW()
        )
        """)
        self.conn.commit()
        cur.close()

    def get_doc_id_from_table(self, doc_id):
        cur = self.connect()
        cur.execute("SELECT * FROM resume_metadata WHERE doc_id = %s", (doc_id,))
        data = cur.fetchall()
        cur.close()
        return data
    
    def get_file_path(self, doc_id):
        cur = self.connect()
        cur.execute("SELECT file_path FROM resume_metadata WHERE doc_id = %s", (doc_id,))
        row = cur.fetchone()
        cur.close()
        return row[0] if row else None
    
    
    def insert_metadata(self, doc_id, filename, file_path):
        cur = self.connect()
        cur.execute(
            "INSERT INTO resume_metadata (doc_id, filename, file_path) VALUES (%s, %s, %s)",
            (doc_id, filename, file_path)
        )
        self.conn.commit()
        cur.close()


