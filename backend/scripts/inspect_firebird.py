import argparse
import os
import sys
import ctypes

# Monkey patch ctypes to support older Firebird client DLLs that lack newer API functions (like fb_shutdown)
original_getattr = ctypes.CDLL.__getattr__

def custom_getattr(self, name):
    try:
        return original_getattr(self, name)
    except AttributeError:
        if name.startswith('fb_') or name.startswith('isc_'):
            return ctypes.WINFUNCTYPE(ctypes.c_long)(lambda *args: 0)
        raise

ctypes.CDLL.__getattr__ = custom_getattr

import fdb

# Mapping field type code to readable name
FIELD_TYPES = {
    7: "SMALLINT",
    8: "INTEGER",
    10: "FLOAT",
    12: "DATE",
    13: "TIME",
    14: "CHAR",
    16: "INT64",
    27: "DOUBLE",
    35: "TIMESTAMP",
    37: "VARCHAR",
    261: "BLOB"
}

def clean_name(val):
    if val is None:
        return ""
    return val.strip()

def inspect_database(db_path, host, port, user, password, fb_library, charset):
    print(f"Connecting to database: {db_path}...")
    
    # Load client library if specified
    if fb_library:
        if os.path.exists(fb_library):
            print(f"Loading custom Firebird client library: {fb_library}")
            fdb.load_api(fb_library)
        else:
            print(f"Warning: Custom library path not found: {fb_library}")
    
    try:
        # Build connection string or connection args
        conn_args = {
            'database': db_path,
            'user': user,
            'password': password,
            'charset': charset
        }
        if host:
            conn_args['host'] = host
        if port:
            conn_args['port'] = int(port)
            
        conn = fdb.connect(**conn_args)
        print("Successfully connected to Firebird database!")
    except Exception as e:
        print(f"Error connecting to database: {e}", file=sys.stderr)
        print("Please verify connection details and Firebird server/client installation.", file=sys.stderr)
        sys.exit(1)

    cursor = conn.cursor()
    
    # 1. Get all user tables
    cursor.execute("""
        SELECT RDB$RELATION_NAME
        FROM RDB$RELATIONS
        WHERE COALESCE(RDB$SYSTEM_FLAG, 0) = 0 AND RDB$VIEW_BLR IS NULL
        ORDER BY RDB$RELATION_NAME
    """)
    tables = [clean_name(row[0]) for row in cursor.fetchall()]
    print(f"Found {len(tables)} user table(s).")
    
    report_lines = []
    report_lines.append("# Firebird Database Inspection Report")
    report_lines.append(f"- **Database File**: {db_path}")
    report_lines.append(f"- **Host**: {host or 'Local'}")
    report_lines.append(f"- **Port**: {port or 'Default'}")
    report_lines.append("")
    report_lines.append("## Table Summary")
    
    # Table counts
    table_counts = {}
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            table_counts[table] = count
        except Exception as e:
            table_counts[table] = f"Error: {e}"
            
    for table, count in table_counts.items():
        report_lines.append(f"- `{table}`: {count} rows")
        
    report_lines.append("")
    report_lines.append("## Detailed Schema")
    
    for table in tables:
        table_escaped = table.replace("'", "''")
        report_lines.append(f"### Table: `{table}` (Rows: {table_counts.get(table)})")
        
        # Get Primary Key(s)
        cursor.execute(f"""
            SELECT s.RDB$FIELD_NAME
            FROM RDB$RELATION_CONSTRAINTS c
            JOIN RDB$INDEX_SEGMENTS s ON c.RDB$INDEX_NAME = s.RDB$INDEX_NAME
            WHERE TRIM(c.RDB$RELATION_NAME) = '{table_escaped}' AND c.RDB$CONSTRAINT_TYPE = 'PRIMARY KEY'
            ORDER BY s.RDB$FIELD_POSITION
        """)
        pk_cols = [clean_name(row[0]) for row in cursor.fetchall()]
        report_lines.append(f"- **Primary Key**: {', '.join(pk_cols) if pk_cols else 'None'}")
        
        # Get Foreign Keys
        cursor.execute(f"""
            SELECT 
                clean_c.RDB$CONSTRAINT_NAME,
                clean_rc.RDB$RELATION_NAME,
                clean_s.RDB$FIELD_NAME,
                clean_rs.RDB$FIELD_NAME
            FROM (
                SELECT RDB$CONSTRAINT_NAME, RDB$INDEX_NAME, RDB$RELATION_NAME 
                FROM RDB$RELATION_CONSTRAINTS 
                WHERE TRIM(RDB$RELATION_NAME) = '{table_escaped}' AND RDB$CONSTRAINT_TYPE = 'FOREIGN KEY'
            ) clean_c
            JOIN RDB$REF_CONSTRAINTS r ON clean_c.RDB$CONSTRAINT_NAME = r.RDB$CONSTRAINT_NAME
            JOIN RDB$RELATION_CONSTRAINTS clean_rc ON r.RDB$CONST_NAME_UQ = clean_rc.RDB$CONSTRAINT_NAME
            JOIN RDB$INDEX_SEGMENTS clean_s ON clean_c.RDB$INDEX_NAME = clean_s.RDB$INDEX_NAME
            JOIN RDB$INDEX_SEGMENTS clean_rs ON clean_rc.RDB$INDEX_NAME = clean_rs.RDB$INDEX_NAME 
                AND clean_s.RDB$FIELD_POSITION = clean_rs.RDB$FIELD_POSITION
            ORDER BY clean_c.RDB$CONSTRAINT_NAME, clean_s.RDB$FIELD_POSITION
        """)
        fk_rows = cursor.fetchall()
        
        fks = {}
        for constraint, ref_table, col, ref_col in fk_rows:
            c_name = clean_name(constraint)
            ref_t = clean_name(ref_table)
            col_n = clean_name(col)
            ref_col_n = clean_name(ref_col)
            
            if c_name not in fks:
                fks[c_name] = {"ref_table": ref_t, "mappings": []}
            fks[c_name]["mappings"].append(f"{col_n} -> {ref_col_n}")
            
        if fks:
            report_lines.append("- **Foreign Keys**:")
            for c_name, fk_info in fks.items():
                report_lines.append(f"  - `{c_name}`: references `{fk_info['ref_table']}` ({', '.join(fk_info['mappings'])})")
        else:
            report_lines.append("- **Foreign Keys**: None")
            
        # Get Columns
        cursor.execute(f"""
            SELECT 
                rf.RDB$FIELD_NAME,
                f.RDB$FIELD_TYPE,
                f.RDB$FIELD_LENGTH,
                f.RDB$FIELD_SCALE,
                f.RDB$FIELD_SUB_TYPE,
                rf.RDB$NULL_FLAG
            FROM RDB$RELATION_FIELDS rf
            JOIN RDB$FIELDS f ON rf.RDB$FIELD_SOURCE = f.RDB$FIELD_NAME
            WHERE TRIM(rf.RDB$RELATION_NAME) = '{table_escaped}'
            ORDER BY rf.RDB$FIELD_POSITION
        """)
        col_rows = cursor.fetchall()
        
        report_lines.append("")
        report_lines.append("| Column Name | Type | Length/Scale | Nullable |")
        report_lines.append("| --- | --- | --- | --- |")
        for col_name, field_type, field_len, field_scale, field_sub_type, null_flag in col_rows:
            col_n = clean_name(col_name)
            type_code = int(field_type) if field_type else 0
            type_name = FIELD_TYPES.get(type_code, f"UNKNOWN ({type_code})")
            
            # Format length/scale
            len_scale = str(field_len)
            if field_scale and int(field_scale) < 0:
                len_scale += f" / scale {field_scale}"
            if type_code == 261: # BLOB
                len_scale = f"Subtype {field_sub_type or 0}"
                
            nullable = "YES" if not null_flag else "NO"
            report_lines.append(f"| `{col_n}` | {type_name} | {len_scale} | {nullable} |")
            
        report_lines.append("")
        
    conn.close()
    
    # Save report to a file
    report_content = "\n".join(report_lines)
    report_file = os.path.splitext(db_path)[0] + "_schema.md"
    try:
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"Successfully generated schema report at: {report_file}")
    except Exception as e:
        print(f"Failed to write schema report file: {e}", file=sys.stderr)
        # Print a small summary to stdout anyway
        print(report_content[:2000])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect a Firebird database schema.")
    parser.add_argument("--db-path", required=True, help="Path to Firebird DB file (e.g. .GDB or .FDB)")
    parser.add_argument("--host", default=None, help="Firebird server host (default: local connection)")
    parser.add_argument("--port", default=None, help="Firebird server port (default: default 3050)")
    parser.add_argument("--user", default="SYSDBA", help="Username (default: SYSDBA)")
    parser.add_argument("--password", default="masterkey", help="Password (default: masterkey)")
    parser.add_argument("--fb-library", default=None, help="Path to fbclient.dll or gds32.dll client library")
    parser.add_argument("--charset", default="UTF8", help="Database connection charset (default: UTF8)")
    
    args = parser.parse_args()
    inspect_database(
        args.db_path,
        args.host,
        args.port,
        args.user,
        args.password,
        args.fb_library,
        args.charset
    )
