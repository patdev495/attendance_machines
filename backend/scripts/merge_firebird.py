import argparse
import os
import shutil
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

def clean_name(val):
    if val is None:
        return ""
    return val.strip()

def get_columns(cursor, table):
    """Retrieve columns of a table in order."""
    cursor.execute(f"""
        SELECT TRIM(rf.RDB$FIELD_NAME)
        FROM RDB$RELATION_FIELDS rf
        WHERE TRIM(rf.RDB$RELATION_NAME) = '{table.upper()}'
        ORDER BY rf.RDB$FIELD_POSITION
    """)
    return [r[0] for r in cursor.fetchall()]

def get_primary_key(cursor, table):
    """Retrieve primary key column of a table."""
    cursor.execute(f"""
        SELECT TRIM(s.RDB$FIELD_NAME)
        FROM RDB$RELATION_CONSTRAINTS c
        JOIN RDB$INDEX_SEGMENTS s ON c.RDB$INDEX_NAME = s.RDB$INDEX_NAME
        WHERE TRIM(c.RDB$RELATION_NAME) = '{table.upper()}' AND c.RDB$CONSTRAINT_TYPE = 'PRIMARY KEY'
        ORDER BY s.RDB$FIELD_POSITION
    """)
    rows = cursor.fetchall()
    return rows[0][0] if rows else None

def get_max_id(cursor, table, id_col):
    """Get max ID in table, return 0 if empty or error."""
    try:
        cursor.execute(f"SELECT MAX({id_col}) FROM {table}")
        val = cursor.fetchone()[0]
        return int(val) if val is not None else 0
    except Exception:
        return 0

def merge_databases(source_path, target_path, output_path, host, port, user, password, fb_library, charset):
    print("=== Firebird Database Merge Tool ===")
    print(f"Source DB: {source_path}")
    print(f"Target DB: {target_path}")
    print(f"Output DB: {output_path}")
    
    # 1. Create a copy of target DB to output path
    if os.path.exists(output_path):
        print(f"Warning: Output file {output_path} already exists. It will be overwritten.")
    try:
        shutil.copy2(target_path, output_path)
        print(f"Created a copy of target DB at: {output_path}")
    except Exception as e:
        print(f"Error copying target DB to output: {e}", file=sys.stderr)
        sys.exit(1)

    # Load client library
    if fb_library:
        if os.path.exists(fb_library):
            print(f"Loading custom Firebird client library: {fb_library}")
            fdb.load_api(fb_library)
        else:
            print(f"Warning: Custom library path not found: {fb_library}")

    # Connect to both databases
    try:
        conn_args = {
            'user': user,
            'password': password,
            'charset': charset
        }
        if host:
            conn_args['host'] = host
        if port:
            conn_args['port'] = int(port)

        print("Connecting to Source DB...")
        conn_src = fdb.connect(database=source_path, **conn_args)
        
        print("Connecting to Target (Output) DB...")
        conn_tgt = fdb.connect(database=output_path, **conn_args)
        
        print("Successfully connected to both databases!")
    except Exception as e:
        print(f"Error connecting to database: {e}", file=sys.stderr)
        sys.exit(1)

    cur_src = conn_src.cursor()
    cur_tgt = conn_tgt.cursor()

    try:
        # Check standard tables
        required_tables = ["KQZ_DEVINFO", "KQZ_BRCH", "KQZ_EMPLOYEE", "KQZ_CARD"]
        for table in required_tables:
            cur_src.execute(f"SELECT 1 FROM rdb$relations WHERE rdb$relation_name = '{table}'")
            if not cur_src.fetchone():
                raise Exception(f"Source database is missing required table: {table}")
            cur_tgt.execute(f"SELECT 1 FROM rdb$relations WHERE rdb$relation_name = '{table}'")
            if not cur_tgt.fetchone():
                raise Exception(f"Target database is missing required table: {table}")

        # === MERGE DEVICES (KQZ_DEVINFO) ===
        print("\n--- Merging Devices (KQZ_DEVINFO) ---")
        dev_cols = get_columns(cur_tgt, "KQZ_DEVINFO")
        dev_pk = get_primary_key(cur_tgt, "KQZ_DEVINFO") or "DEVID"
        
        cur_src.execute(f"SELECT {', '.join(dev_cols)} FROM KQZ_DEVINFO")
        src_devs = cur_src.fetchall()
        
        cur_tgt.execute(f"SELECT {dev_pk}, SERIAL, IPADDRESS FROM KQZ_DEVINFO")
        tgt_devs = cur_tgt.fetchall()
        
        # Build maps and lookup
        tgt_dev_by_serial = {clean_name(r[1]): r[0] for r in tgt_devs if r[1]}
        tgt_dev_by_ip = {clean_name(r[2]): r[0] for r in tgt_devs if r[2]}
        dev_id_map = {} # source_devid -> target_devid
        
        next_dev_id = get_max_id(cur_tgt, "KQZ_DEVINFO", dev_pk) + 1
        new_devs_count = 0

        for dev_row in src_devs:
            dev_data = dict(zip(dev_cols, dev_row))
            src_dev_id = dev_data[dev_pk]
            serial = clean_name(dev_data.get("SERIAL"))
            ip = clean_name(dev_data.get("IPADDRESS"))
            
            tgt_dev_id = None
            if serial and serial in tgt_dev_by_serial:
                tgt_dev_id = tgt_dev_by_serial[serial]
            elif ip and ip in tgt_dev_by_ip:
                tgt_dev_id = tgt_dev_by_ip[ip]
                
            if tgt_dev_id is not None:
                dev_id_map[src_dev_id] = tgt_dev_id
                print(f"Device mapped: Source ID {src_dev_id} -> Target ID {tgt_dev_id} (Serial: {serial or 'N/A'}, IP: {ip or 'N/A'})")
            else:
                # Add new device
                new_id = next_dev_id
                next_dev_id += 1
                dev_id_map[src_dev_id] = new_id
                
                # Copy row with new ID
                dev_data[dev_pk] = new_id
                
                # Build insert
                cols = list(dev_data.keys())
                placeholders = [f":{c}" for c in cols] # fdb supports named placeholders or standard positional '?'
                # Note: fdb python uses standard python DB-API param style (usually positional '?' or named depending on fdb API)
                # In fdb, positional '?' is standard.
                sql = f"INSERT INTO KQZ_DEVINFO ({', '.join(cols)}) VALUES ({', '.join(['?'] * len(cols))})"
                vals = [dev_data[c] for c in cols]
                cur_tgt.execute(sql, vals)
                new_devs_count += 1
                print(f"Added new device: Source ID {src_dev_id} -> Target ID {new_id} (Serial: {serial or 'N/A'}, IP: {ip or 'N/A'})")

        # === MERGE DEPARTMENTS (KQZ_BRCH) ===
        print("\n--- Merging Departments (KQZ_BRCH) ---")
        brch_cols = get_columns(cur_tgt, "KQZ_BRCH")
        brch_pk = get_primary_key(cur_tgt, "KQZ_BRCH") or "BRCHID"
        
        cur_src.execute(f"SELECT {', '.join(brch_cols)} FROM KQZ_BRCH")
        src_brchs = cur_src.fetchall()
        
        cur_tgt.execute(f"SELECT {brch_pk}, BRCHNAME, PID FROM KQZ_BRCH")
        tgt_brchs = cur_tgt.fetchall()
        
        # Key: (clean_name(BRCHNAME), normalized_PID), Value: BRCHID
        tgt_brch_lookup = {}
        for r in tgt_brchs:
            name = clean_name(r[1])
            pid = r[2] if (r[2] is not None and r[2] != 0) else 0
            tgt_brch_lookup[(name, pid)] = r[0]
            
        brch_id_map = {} # source_brchid -> target_brchid
        
        # Build parent mapping for source departments to sort them by depth
        src_pid_by_id = {}
        for brch_row in src_brchs:
            brch_data = dict(zip(brch_cols, brch_row))
            src_pid_by_id[brch_data[brch_pk]] = brch_data.get("PID")
            
        def get_depth(brch_id):
            depth = 0
            curr = brch_id
            visited = set()
            while curr in src_pid_by_id and src_pid_by_id[curr] is not None and src_pid_by_id[curr] != 0:
                if curr in visited:
                    break
                visited.add(curr)
                curr = src_pid_by_id[curr]
                depth += 1
            return depth
            
        # Sort source departments by depth so parent departments are processed first
        src_brchs_sorted = sorted(src_brchs, key=lambda row: get_depth(dict(zip(brch_cols, row))[brch_pk]))
        
        next_brch_id = get_max_id(cur_tgt, "KQZ_BRCH", brch_pk) + 1
        new_brch_count = 0

        for brch_row in src_brchs_sorted:
            brch_data = dict(zip(brch_cols, brch_row))
            src_brch_id = brch_data[brch_pk]
            name = clean_name(brch_data.get("BRCHNAME"))
            src_pid = brch_data.get("PID")
            
            # Resolve parent ID in target database
            tgt_pid = 0
            if src_pid is not None and src_pid != 0:
                tgt_pid = brch_id_map.get(src_pid, 0)
                
            lookup_key = (name, tgt_pid)
            
            if lookup_key in tgt_brch_lookup:
                tgt_brch_id = tgt_brch_lookup[lookup_key]
                brch_id_map[src_brch_id] = tgt_brch_id
                print(f"Department mapped: Source ID {src_brch_id} -> Target ID {tgt_brch_id} (Name: {name}, Parent ID: {tgt_pid})")
            else:
                new_id = next_brch_id
                next_brch_id += 1
                brch_id_map[src_brch_id] = new_id
                
                brch_data[brch_pk] = new_id
                brch_data["PID"] = tgt_pid if tgt_pid != 0 else None
                
                cols = list(brch_data.keys())
                sql = f"INSERT INTO KQZ_BRCH ({', '.join(cols)}) VALUES ({', '.join(['?'] * len(cols))})"
                vals = [brch_data[c] for c in cols]
                cur_tgt.execute(sql, vals)
                new_brch_count += 1
                
                # Update lookup mapping
                tgt_brch_lookup[lookup_key] = new_id
                print(f"Added new department: Source ID {src_brch_id} -> Target ID {new_id} (Name: {name}, Parent ID: {tgt_pid})")

        # === MERGE EMPLOYEES (KQZ_EMPLOYEE) ===
        print("\n--- Merging Employees (KQZ_EMPLOYEE) ---")
        emp_cols = get_columns(cur_tgt, "KQZ_EMPLOYEE")
        emp_pk = get_primary_key(cur_tgt, "KQZ_EMPLOYEE") or "EMPLOYEEID"
        
        cur_src.execute(f"SELECT {', '.join(emp_cols)} FROM KQZ_EMPLOYEE")
        src_emps = cur_src.fetchall()
        
        cur_tgt.execute(f"SELECT {emp_pk}, EMPLOYEECODE, EMPLOYEENAME FROM KQZ_EMPLOYEE")
        tgt_emps = cur_tgt.fetchall()
        
        tgt_emp_by_code = {clean_name(r[1]): (r[0], clean_name(r[2])) for r in tgt_emps if r[1]}
        emp_id_map = {} # source_empid -> target_empid
        
        next_emp_id = get_max_id(cur_tgt, "KQZ_EMPLOYEE", emp_pk) + 1
        new_emp_count = 0
        updated_emp_count = 0

        for emp_row in src_emps:
            emp_data = dict(zip(emp_cols, emp_row))
            src_emp_id = emp_data[emp_pk]
            code = clean_name(emp_data.get("EMPLOYEECODE"))
            name = clean_name(emp_data.get("EMPLOYEENAME"))
            src_brch_id = emp_data.get("BRCHID")
            
            # Map branch/department
            tgt_brch_id = brch_id_map.get(src_brch_id)
            if tgt_brch_id is None:
                # If branch mapping not found, assign to root branch or default
                tgt_brch_id = list(brch_id_map.values())[0] if brch_id_map else 0
                
            # Get target department name
            cur_tgt.execute("SELECT BRCHNAME FROM KQZ_BRCH WHERE BRCHID = ?", (tgt_brch_id,))
            row_brch = cur_tgt.fetchone()
            tgt_brch_name = row_brch[0] if row_brch else "Unknown"
            
            emp_data["BRCHID"] = tgt_brch_id
            emp_data["BRCHNAME"] = tgt_brch_name

            if code in tgt_emp_by_code:
                # Employee exists - update details and map
                tgt_emp_id, tgt_name = tgt_emp_by_code[code]
                emp_id_map[src_emp_id] = tgt_emp_id
                
                # Check if we should update info (e.g. templates/photo/name)
                # Overwrite templates & photo if source has them
                update_cols = []
                update_vals = []
                
                # We update name, templates, photo, card code, etc.
                cols_to_update = ["EMPLOYEENAME", "HDCPINFO", "PHOTO", "CARDCODE", "IDCARD", "MOBILE", "BRCHID", "BRCHNAME"]
                for col in cols_to_update:
                    if col in emp_data and emp_data[col] is not None:
                        update_cols.append(col)
                        update_vals.append(emp_data[col])
                        
                if update_cols:
                    set_clause = ", ".join([f"{col} = ?" for col in update_cols])
                    sql = f"UPDATE KQZ_EMPLOYEE SET {set_clause} WHERE {emp_pk} = ?"
                    update_vals.append(tgt_emp_id)
                    cur_tgt.execute(sql, update_vals)
                    updated_emp_count += 1
                    
                print(f"Employee updated: Source ID {src_emp_id} -> Target ID {tgt_emp_id} (Code: {code}, Name: {name})")
            else:
                # Employee doesn't exist - insert new
                new_id = next_emp_id
                next_emp_id += 1
                emp_id_map[src_emp_id] = new_id
                
                emp_data[emp_pk] = new_id
                
                cols = list(emp_data.keys())
                sql = f"INSERT INTO KQZ_EMPLOYEE ({', '.join(cols)}) VALUES ({', '.join(['?'] * len(cols))})"
                vals = [emp_data[c] for c in cols]
                cur_tgt.execute(sql, vals)
                new_emp_count += 1
                print(f"Added new employee: Source ID {src_emp_id} -> Target ID {new_id} (Code: {code}, Name: {name})")

        # === MERGE LOGS (KQZ_CARD) ===
        print("\n--- Merging Attendance Logs (KQZ_CARD) ---")
        card_cols = get_columns(cur_tgt, "KQZ_CARD")
        card_pk = get_primary_key(cur_tgt, "KQZ_CARD") or "CARDID"
        
        cur_src.execute(f"SELECT {', '.join(card_cols)} FROM KQZ_CARD")
        src_cards = cur_src.fetchall()
        
        # Load existing target cards to memory to avoid duplicate insertion (using composite key employee_id + card_time)
        cur_tgt.execute("SELECT EMPLOYEEID, CARDTIME FROM KQZ_CARD")
        tgt_card_keys = {(r[0], r[1]) for r in cur_tgt.fetchall()}
        print(f"Found {len(tgt_card_keys)} existing logs in Target DB.")

        next_card_id = get_max_id(cur_tgt, "KQZ_CARD", card_pk) + 1
        new_card_count = 0

        for card_row in src_cards:
            card_data = dict(zip(card_cols, card_row))
            src_emp_id = card_data.get("EMPLOYEEID")
            card_time = card_data.get("CARDTIME")
            src_dev_id = card_data.get("DEVID")
            
            # Map employee
            tgt_emp_id = emp_id_map.get(src_emp_id)
            if tgt_emp_id is None:
                # Log has no corresponding employee in target, skip it
                print(f"Warning: Skipped log for source employee ID {src_emp_id} - Employee not found/mapped.")
                continue
                
            # Map device (if device exists)
            tgt_dev_id = dev_id_map.get(src_dev_id, src_dev_id)
            
            # Check for duplicate
            if (tgt_emp_id, card_time) in tgt_card_keys:
                # Log already exists, skip
                continue
                
            # Add log
            new_id = next_card_id
            next_card_id += 1
            
            card_data[card_pk] = new_id
            card_data["EMPLOYEEID"] = tgt_emp_id
            card_data["DEVID"] = tgt_dev_id
            
            cols = list(card_data.keys())
            sql = f"INSERT INTO KQZ_CARD ({', '.join(cols)}) VALUES ({', '.join(['?'] * len(cols))})"
            vals = [card_data[c] for c in cols]
            cur_tgt.execute(sql, vals)
            new_card_count += 1
            
            # Record it in memory lookup to prevent duplicates inside the batch itself
            tgt_card_keys.add((tgt_emp_id, card_time))

        print(f"Inserted {new_card_count} new attendance logs.")

        # === UPDATE GENERATORS ===
        print("\n--- Updating Generators/Sequences ---")
        generators_to_update = {
            "GEN_DEVID": ("KQZ_DEVINFO", dev_pk),
            "GEN_BRCHID": ("KQZ_BRCH", brch_pk),
            "GEN_EMPLOYEEID": ("KQZ_EMPLOYEE", emp_pk),
            "GEN_CARDID": ("KQZ_CARD", card_pk)
        }
        
        for gen, (table, col) in generators_to_update.items():
            max_val = get_max_id(cur_tgt, table, col)
            # Check if generator exists
            cur_tgt.execute(f"SELECT 1 FROM RDB$GENERATORS WHERE TRIM(RDB$GENERATOR_NAME) = '{gen}'")
            if cur_tgt.fetchone():
                cur_tgt.execute(f"SET GENERATOR {gen} TO {max_val}")
                print(f"Set Generator {gen} to value {max_val}")
            else:
                print(f"Warning: Generator {gen} not found in database system tables.")

        # Commit all changes
        conn_tgt.commit()
        print("\n=== Success! Database Merge Completed ===")
        print(f"Merged database saved to: {output_path}")
        print(f"Summary of changes:")
        print(f"- New Devices: {new_devs_count}")
        print(f"- New Departments: {new_brch_count}")
        print(f"- New Employees: {new_emp_count}")
        print(f"- Updated Employees: {updated_emp_count}")
        print(f"- New Attendance Logs: {new_card_count}")

    except Exception as e:
        conn_tgt.rollback()
        print(f"\nError occurred during merge, rolling back changes: {e}", file=sys.stderr)
        # Delete output file if it was partially merged and failed
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
                print("Deleted partial output file to prevent corrupt database.")
            except Exception:
                pass
        sys.exit(1)
    finally:
        # Clear references to cursors and fetched data to allow garbage collection
        # of BlobReader objects while the database connection is still open.
        cur_src = None
        cur_tgt = None
        src_emps = None
        src_cards = None
        src_devs = None
        src_brchs = None
        
        # Clean up loop variables that might hold references
        if 'emp_row' in locals(): emp_row = None
        if 'emp_data' in locals(): emp_data = None
        if 'card_row' in locals(): card_row = None
        if 'card_data' in locals(): card_data = None
        if 'dev_row' in locals(): dev_row = None
        if 'dev_data' in locals(): dev_data = None
        if 'brch_row' in locals(): brch_row = None
        if 'brch_data' in locals(): brch_data = None
        
        import gc
        gc.collect()
        
        try:
            if 'conn_src' in locals() and conn_src:
                conn_src.close()
        except Exception:
            pass
        try:
            if 'conn_tgt' in locals() and conn_tgt:
                conn_tgt.close()
        except Exception:
            pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge two Hanvon FaceAtt Firebird databases.")
    parser.add_argument("--source", required=True, help="Path to Source Firebird DB file (e.g. HWATT_1.GDB)")
    parser.add_argument("--target", required=True, help="Path to Target Firebird DB file (e.g. HWATT_2.GDB)")
    parser.add_argument("--output", required=True, help="Path to write the Merged output file (e.g. HWATT_MERGED.GDB)")
    parser.add_argument("--host", default=None, help="Firebird server host (default: local connection)")
    parser.add_argument("--port", default=None, help="Firebird server port (default: default 3050)")
    parser.add_argument("--user", default="SYSDBA", help="Username (default: SYSDBA)")
    parser.add_argument("--password", default="masterkey", help="Password (default: masterkey)")
    parser.add_argument("--fb-library", default=None, help="Path to fbclient.dll or gds32.dll client library")
    parser.add_argument("--charset", default="UTF8", help="Database connection charset (default: UTF8)")
    
    args = parser.parse_args()
    merge_databases(
        args.source,
        args.target,
        args.output,
        args.host,
        args.port,
        args.user,
        args.password,
        args.fb_library,
        args.charset
    )
