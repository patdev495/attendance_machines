import pyodbc
try:
    conn_str = 'driver={ODBC Driver 18 for SQL Server};server=192.168.209.18;database=MIS;uid=mis01;pwd=mis01;TrustServerCertificate=yes'
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    print("--- Table: Employees ---")
    cursor.execute("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Employees'")
    for row in cursor.fetchall():
        print(f"Column: {row[0]}, Type: {row[1]}")
        
    print("\n--- Table: AttendanceLogs ---")
    cursor.execute("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'AttendanceLogs'")
    for row in cursor.fetchall():
        print(f"Column: {row[0]}, Type: {row[1]}")
        
    conn.close()
except Exception as e:
    print(f"ERROR: {e}")
