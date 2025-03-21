# Modify the beginning of your init_db.py file
import os
import sqlalchemy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OVERRIDE environment variables for testing
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5433"  # Make sure this matches your proxy port

def init_db():
    # Database configuration
    db_user = os.environ.get("DB_USER")
    db_pass = os.environ.get("DB_PASS")
    db_name = os.environ.get("DB_NAME")
    db_host = os.environ.get("DB_HOST")  # Should now be "localhost"
    db_port = os.environ.get("DB_PORT")  # Should now be "5432"
    
    print(f"Connecting to: {db_host}:{db_port}/{db_name} as {db_user}")
    
    # For Cloud SQL with PostgreSQL
    db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    
    # Create engine with timeout
    engine = sqlalchemy.create_engine(
        db_url,
        connect_args={"connect_timeout": 10}
    )
    
    # Continue with the rest of your code...
    
    # Create tables
    with engine.connect() as conn:
        # Example: Create a simple table for demonstration
        conn.execute(sqlalchemy.text("""
        CREATE TABLE IF NOT EXISTS your_table (
            id SERIAL PRIMARY KEY,
            field1 VARCHAR(255) NOT NULL,
            field2 VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """))
        
        # Add some example data
        conn.execute(sqlalchemy.text("""
        INSERT INTO your_table (field1, field2)
        VALUES 
            ('Example 1', 'Description 1'),
            ('Example 2', 'Description 2'),
            ('Example 3', 'Description 3')
        ON CONFLICT DO NOTHING
        """))
        
        conn.commit()
        
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_db()