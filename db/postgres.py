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

    def fetch_all(self):
        cur = self.connect()
        cur.execute("SELECT doc_id, filename, file_path, uploaded_at FROM resume_metadata ORDER BY uploaded_at DESC")
        data = cur.fetchall()
        cur.close()
        return data


    def search(self, keyword: str):
        cur = self.connect()
        keyword = f"%{keyword.lower()}%"
        cur.execute("""
            SELECT doc_id, filename, file_path, uploaded_at
            FROM resume_metadata
            WHERE LOWER(filename) LIKE %s OR LOWER(doc_id) LIKE %s
            ORDER BY uploaded_at DESC
        """, (keyword, keyword))
        data = cur.fetchall()
        cur.close()
        return data


    def sort_by(self, mode: str):

        if mode == "Newest First":
            order = "DESC"
        elif mode == "Oldest First":
            order = "ASC"
        else:
            return self.fetch_all()

        cur = self.connect()
        cur.execute(f"""
            SELECT doc_id, filename, file_path, uploaded_at
            FROM resume_metadata
            ORDER BY uploaded_at {order}
        """)
        data = cur.fetchall()
        cur.close()
        return data


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

        
    def list_resumes(self):
        cur = self.connect()
        cur.execute("""
            SELECT doc_id, filename, uploaded_at
            FROM resume_metadata
            ORDER BY uploaded_at DESC
        """)
        rows = cur.fetchall()
        cur.close()
        return rows
    

    def fetch_all(self):
        cur = self.connect()
        cur.execute("SELECT doc_id, filename, file_path, uploaded_at FROM resume_metadata")
        data = cur.fetchall()
        cur.close()
        return data
    
    


    def search(self, keyword: str):
        cur = self.connect()
        keyword = f"%{keyword.lower()}%"
        cur.execute("""
            SELECT doc_id, filename, file_path, uploaded_at
            FROM resume_metadata
            WHERE LOWER(filename) LIKE %s OR LOWER(doc_id) LIKE %s
            ORDER BY uploaded_at DESC
        """, (keyword, keyword))
        data = cur.fetchall()
        cur.close()
        return data


    def sort_by(self, mode: str):

        if mode == "Newest First":
            order = "DESC"
        elif mode == "Oldest First":
            order = "ASC"
        else:
            return self.fetch_all()

        cur = self.connect()
        cur.execute(f"""
            SELECT doc_id, filename, file_path, uploaded_at
            FROM resume_metadata
            ORDER BY uploaded_at {order}
        """)
        data = cur.fetchall()
        cur.close()
        return data



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

cur = PostgresDB()
