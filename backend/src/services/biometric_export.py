import pandas as pd
import io
from sqlalchemy.orm import Session
from database import EmployeeMetadata, EmployeeFingerprint
from datetime import datetime

class BiometricExportService:
    @staticmethod
    def generate_excel_from_db(db: Session, ip: str = None) -> io.BytesIO:
        """
        Generates an Excel file containing fingerprints.
        If IP is provided, it only exports fingerprints for employees currently on that machine.
        """
        # 1. Prepare the query
        query = db.query(
            EmployeeFingerprint.employee_id,
            EmployeeMetadata.emp_name,
            EmployeeMetadata.department,
            EmployeeMetadata.status,
            EmployeeFingerprint.template_id,
            EmployeeFingerprint.template_data,
            EmployeeFingerprint.source_ip,
            EmployeeFingerprint.created_at
        ).outerjoin(EmployeeMetadata, EmployeeFingerprint.employee_id == EmployeeMetadata.employee_id)

        # 2. Apply filtering if IP is provided
        if ip:
            # First, check if we have any fingerprints explicitly tagged with this source_ip
            # This is the most reliable way since we just added traceability.
            has_tagged_data = db.query(EmployeeFingerprint).filter(EmployeeFingerprint.source_ip == ip).first()
            
            if has_tagged_data:
                query = query.filter(EmployeeFingerprint.source_ip == ip)
            else:
                # Fallback: Connect to machine to get the IDs (for older data or cross-synced data)
                from sync_service import get_users_from_machine
                machine_users = get_users_from_machine(ip)
                if isinstance(machine_users, list) and len(machine_users) > 0:
                    allowed_ids = [str(u['user_id']) for u in machine_users]
                    query = query.filter(EmployeeFingerprint.employee_id.in_(allowed_ids))
                else:
                    # If machine is offline AND no tagged data exists, we have nothing to export
                    # We continue but the result will likely be empty.
                    pass
            
        results = query.all()
        
        data = []
        for r in results:
            data.append({
                "Employee ID": r.employee_id,
                "Name": r.emp_name or "Unknown",
                "Department": r.department or "N/A",
                "Status": r.status or "Active",
                "Source Machine": r.source_ip or "N/A",
                "Capture Date": r.created_at.strftime('%Y-%m-%d %H:%M:%S') if r.created_at else "N/A",
                "Finger Slot (0-9)": r.template_id,
                "Template Data (Base64)": r.template_data
            })
            
        df = pd.DataFrame(data)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Fingerprints', index=False)
            
            # Format columns
            workbook = writer.book
            worksheet = writer.sheets['Fingerprints']
            
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })
            
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                column_len = max(df[value].astype(str).map(len).max(), len(value)) + 2
                # Cap column width for template data
                if value == "Template Data (Base64)":
                    column_len = 30
                worksheet.set_column(col_num, col_num, column_len)
                
        output.seek(0)
        return output
