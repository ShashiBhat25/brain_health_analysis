import mysql.connector
import os

# Database configuration
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'root'),
    'database': 'healthcare_system'
}

def add_graph_image_column():
    """Add graph_image column to brain_reports table if it doesn't exist."""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'healthcare_system' 
            AND TABLE_NAME = 'brain_reports' 
            AND COLUMN_NAME = 'graph_image'
        """)
        
        exists = cursor.fetchone()[0]
        
        if exists == 0:
            print("Adding 'graph_image' column to brain_reports table...")
            cursor.execute("""
                ALTER TABLE brain_reports 
                ADD COLUMN graph_image LONGTEXT AFTER features
            """)
            conn.commit()
            print("✓ Column 'graph_image' added successfully!")
        else:
            print("✓ Column 'graph_image' already exists.")
        
        cursor.close()
        conn.close()
        
    except mysql.connector.Error as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_graph_image_column()
