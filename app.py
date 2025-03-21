from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sqlalchemy
from dotenv import load_dotenv
import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Database connection parameters
db_user = os.environ.get("DB_USER", "postgres")
db_pass = os.environ.get("DB_PASS", "")
db_name = os.environ.get("DB_NAME", "postgres")
db_host = os.environ.get("DB_HOST", "localhost")
db_port = os.environ.get("DB_PORT", "5433")

# Log these values to confirm
print(f"Database connection parameters: {db_host}:{db_port}/{db_name}")

# Database connection string
db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

# Create database engine
engine = sqlalchemy.create_engine(db_url)

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Welcome to the Flask SQL API. Use /api/items to access the API."}), 200

@app.route('/api/db-test', methods=['GET'])
def test_db():
    try:
        print("Testing database connection...")
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text("SELECT 1"))
            print("Database query successful!")
            return jsonify({"message": "Database connection successful"}), 200
    except Exception as e:
        error_msg = f"Database connection error: {str(e)}"
        print(f"ERROR in /api/db-test: {error_msg}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": error_msg}), 500

# Basic route to check if API is running
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "API is running"}), 200

# GET all items
@app.route('/api/test', methods=['GET'])
def test_api():
    return jsonify({"message": "API is working"}), 200

# GET all tables in the database
@app.route('/api/tables', methods=['GET'])
def get_all_tables():
    try:
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            
            tables = [row[0] for row in result]
            return jsonify(tables), 200
    except Exception as e:
        error_msg = f"Database error: {str(e)}"
        print(f"ERROR in /api/tables: {error_msg}")
        return jsonify({"error": error_msg}), 500

# Get data from any table by name
@app.route('/api/table/<string:table_name>', methods=['GET'])
def get_table_data(table_name):
    try:
        # Security check to prevent SQL injection
        allowed_tables = []
        with engine.connect() as conn:
            tables_result = conn.execute(sqlalchemy.text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            allowed_tables = [row[0] for row in tables_result]
        
        if table_name not in allowed_tables:
            return jsonify({"error": "Table not found or access denied"}), 404
        
        # Get table data
        with engine.connect() as conn:
            # Get columns first
            columns_result = conn.execute(sqlalchemy.text(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = :table_name
                ORDER BY ordinal_position
            """), {"table_name": table_name})
            
            columns = [{"name": row[0], "type": row[1]} for row in columns_result]
            column_names = [col["name"] for col in columns]
            
            # Get data
            # Use proper SQLAlchemy parameterized query with table name
            query = sqlalchemy.text(f"SELECT * FROM {table_name} LIMIT 1000")
            data_result = conn.execute(query)
            
            rows = []
            for row in data_result:
                row_data = {}
                for i, col in enumerate(column_names):
                    # Handle date/time conversion for JSON
                    if isinstance(row[i], (datetime.date, datetime.datetime)):
                        row_data[col] = row[i].isoformat()
                    else:
                        row_data[col] = row[i]
                rows.append(row_data)
            
            return jsonify({
                "columns": columns,
                "data": rows
            }), 200
    except Exception as e:
        error_msg = f"Database error: {str(e)}"
        print(f"ERROR in /api/table/{table_name}: {error_msg}")
        return jsonify({"error": error_msg}), 500

# Search across a table
@app.route('/api/search/<string:table_name>', methods=['GET'])
def search_table(table_name):
    try:
        search_term = request.args.get('q', '')
        column = request.args.get('column', '')
        
        if not search_term:
            return jsonify({"error": "Search term is required"}), 400
        
        # Security check to prevent SQL injection
        allowed_tables = []
        with engine.connect() as conn:
            tables_result = conn.execute(sqlalchemy.text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            allowed_tables = [row[0] for row in tables_result]
        
        if table_name not in allowed_tables:
            return jsonify({"error": "Table not found or access denied"}), 404
        
        # Get table columns
        with engine.connect() as conn:
            columns_result = conn.execute(sqlalchemy.text(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = :table_name
                ORDER BY ordinal_position
            """), {"table_name": table_name})
            
            columns = [{"name": row[0], "type": row[1]} for row in columns_result]
            column_names = [col["name"] for col in columns]
            
            # Build search query
            if column and column in column_names:
                # Search in specific column
                search_query = f"""
                    SELECT * FROM {table_name}
                    WHERE CAST({column} AS TEXT) ILIKE :search_term
                    LIMIT 100
                """
                params = {"search_term": f"%{search_term}%"}
            else:
                # Search across all text/varchar columns
                search_conditions = []
                for col in columns:
                    if col["type"].startswith('character') or col["type"] in ('text', 'varchar'):
                        search_conditions.append(f"CAST({col['name']} AS TEXT) ILIKE :search_term")
                
                if not search_conditions:
                    return jsonify({"error": "No text columns found for search"}), 400
                
                search_query = f"""
                    SELECT * FROM {table_name}
                    WHERE {" OR ".join(search_conditions)}
                    LIMIT 100
                """
                params = {"search_term": f"%{search_term}%"}
            
            # Execute search
            data_result = conn.execute(sqlalchemy.text(search_query), params)
            
            rows = []
            for row in data_result:
                row_data = {}
                for i, col in enumerate(column_names):
                    # Handle date/time conversion for JSON
                    if isinstance(row[i], (datetime.date, datetime.datetime)):
                        row_data[col] = row[i].isoformat()
                    else:
                        row_data[col] = row[i]
                rows.append(row_data)
            
            return jsonify({
                "columns": columns,
                "data": rows,
                "count": len(rows)
            }), 200
    except Exception as e:
        error_msg = f"Search error: {str(e)}"
        print(f"ERROR in /api/search/{table_name}: {error_msg}")
        return jsonify({"error": error_msg}), 500

# GET all items
@app.route('/api/items', methods=['GET'])
def get_all_items():
    try:
        # First, check if the 'your_table' table exists
        with engine.connect() as conn:
            check_result = conn.execute(sqlalchemy.text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'your_table'
                );
            """))
            table_exists = check_result.scalar()
            
            if not table_exists:
                # If table doesn't exist, return a specific message
                return jsonify({"error": "Table 'your_table' does not exist. Use /api/tables to see available tables."}), 404
        
        # Connect to the database
        with engine.connect() as conn:
            # Execute a query to get all items
            result = conn.execute(sqlalchemy.text(
                "SELECT id, field1, field2, created_at FROM your_table ORDER BY id"
            ))
            
            # Convert result to list of dictionaries
            items = []
            for row in result:
                items.append({
                    "id": row[0],
                    "field1": row[1],
                    "field2": row[2],
                    "created_at": row[3].isoformat() if row[3] else None
                })
            
            return jsonify(items), 200
    except Exception as e:
        error_msg = f"Database error: {str(e)}"
        print(f"ERROR in /api/items: {error_msg}")
        return jsonify({"error": error_msg}), 500

# GET a specific item by ID
@app.route('/api/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    try:
        # Connect to the database
        with engine.connect() as conn:
            # Execute a query to get the specific item
            result = conn.execute(sqlalchemy.text(
                "SELECT id, field1, field2, created_at FROM your_table WHERE id = :id"
            ), {"id": item_id})
            
            # Get the first row from the result
            row = result.fetchone()
            
            if row:
                item = {
                    "id": row[0],
                    "field1": row[1],
                    "field2": row[2],
                    "created_at": row[3].isoformat() if row[3] else None
                }
                return jsonify(item), 200
            else:
                return jsonify({"error": "Item not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# POST a new item
@app.route('/api/items', methods=['POST'])
def create_item():
    try:
        # Get JSON data from request
        data = request.get_json()
        
        # Validate required fields
        if not data or 'field1' not in data or 'field2' not in data:
            return jsonify({"error": "Missing required fields (field1, field2)"}), 400
        
        # Connect to the database
        with engine.connect() as conn:
            # Execute a query to insert the new item
            result = conn.execute(sqlalchemy.text(
                "INSERT INTO your_table (field1, field2) VALUES (:field1, :field2) RETURNING id"
            ), {
                "field1": data['field1'],
                "field2": data['field2']
            })
            
            # Get the ID of the newly created item
            new_id = result.scalar()
            
            return jsonify({"id": new_id, "message": "Item created successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# PUT (update) an existing item
@app.route('/api/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    try:
        # Get JSON data from request
        data = request.get_json()
        
        # Validate required fields
        if not data or ('field1' not in data and 'field2' not in data):
            return jsonify({"error": "Missing at least one field to update (field1, field2)"}), 400
        
        # Connect to the database
        with engine.connect() as conn:
            # Check if the item exists
            check_result = conn.execute(sqlalchemy.text(
                "SELECT id FROM your_table WHERE id = :id"
            ), {"id": item_id})
            
            if not check_result.fetchone():
                return jsonify({"error": "Item not found"}), 404
            
            # Build the update query based on provided fields
            update_fields = []
            params = {"id": item_id}
            
            if 'field1' in data:
                update_fields.append("field1 = :field1")
                params["field1"] = data['field1']
            
            if 'field2' in data:
                update_fields.append("field2 = :field2")
                params["field2"] = data['field2']
            
            update_query = f"UPDATE your_table SET {', '.join(update_fields)} WHERE id = :id"
            
            # Execute the update query
            conn.execute(sqlalchemy.text(update_query), params)
            
            return jsonify({"message": "Item updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# DELETE an item
@app.route('/api/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    try:
        # Connect to the database
        with engine.connect() as conn:
            # Check if the item exists
            check_result = conn.execute(sqlalchemy.text(
                "SELECT id FROM your_table WHERE id = :id"
            ), {"id": item_id})
            
            if not check_result.fetchone():
                return jsonify({"error": "Item not found"}), 404
            
            # Execute a query to delete the item
            conn.execute(sqlalchemy.text(
                "DELETE FROM your_table WHERE id = :id"
            ), {"id": item_id})
            
            return jsonify({"message": "Item deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))