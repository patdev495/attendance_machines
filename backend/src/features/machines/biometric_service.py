import pandas as pd
import io
from sqlalchemy.orm import Session
from database import EmployeeMetadata, EmployeeFingerprint
from datetime import datetime
from .service import get_users_from_machine

class BiometricExportService:
    @staticmethod
    def generate_excel_from_db(db: Session, ip: str = None) -> io.BytesIO:
        """
        Generates an Excel file containing fingerprints.
        If IP is provided, it only exports fingerprints for employees currently on that machine.
        """
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

        if ip:
            # Check for tagged data first
            has_tagged_data = db.query(EmployeeFingerprint).filter(EmployeeFingerprint.source_ip == ip).first()
            if has_tagged_data:
                query = query.filter(EmployeeFingerprint.source_ip == ip)
            else:
                # Fallback to machine user list
                users, status = get_users_from_machine(ip)
                if status == "Success" and users:
                    allowed_ids = [str(u['user_id']) for u in users]
                    query = query.filter(EmployeeFingerprint.employee_id.in_(allowed_ids))
            
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
            workbook = writer.book
            worksheet = writer.sheets['Fingerprints']
            header_format = workbook.add_format({
                'bold': True, 'text_wrap': True, 'valign': 'top', 'fg_color': '#D7E4BC', 'border': 1
            })
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                column_len = max(df[value].astype(str).map(len).max(), len(value)) + 2
                if value == "Template Data (Base64)": column_len = 30
                worksheet.set_column(col_num, col_num, column_len)
        output.seek(0)
        return output
