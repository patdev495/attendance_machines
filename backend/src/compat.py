"""
Database compatibility layer for MSSQL ↔ SQLite.

Registers custom SQLAlchemy compiler extensions so that MSSQL-specific
functions (DATEADD, LTRIM, RTRIM, CAST to Date/Time) emit correct SQL
on both MSSQL and SQLite backends.

Import this module ONCE at startup (database.py) to activate the compilers.
"""
import os
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import functions
from sqlalchemy import DateTime

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# ─────────────────────────────────────────────────────────────────────
# DATEADD — MSSQL: DATEADD(day, -1, col)
#           SQLite: datetime(col, '-1 day')
# ─────────────────────────────────────────────────────────────────────
class dateadd(functions.GenericFunction):
    type = DateTime()
    name = "dateadd"
    inherit_cache = True


@compiles(dateadd, "sqlite")
def _dateadd_sqlite(element, compiler, **kw):
    """
    Translate DATEADD(interval, offset, column) to SQLite datetime().
    Usage in SA: func.dateadd(text("day"), text("-1"), col)
    """
    args = list(element.clauses)
    if len(args) == 3:
        # args[0] = interval literal (day/hour), args[1] = offset, args[2] = column
        interval = compiler.process(args[0], **kw).strip("'\"")
        offset = compiler.process(args[1], **kw).strip("'\"")
        col = compiler.process(args[2], **kw)
        return f"datetime({col}, '{offset} {interval}')"
    return f"datetime({compiler.process(args[-1], **kw)})"


# ─────────────────────────────────────────────────────────────────────
# LTRIM / RTRIM — MSSQL has LTRIM/RTRIM natively.
#                 SQLite also has LTRIM/RTRIM natively since 3.x.
#                 No override needed — both dialects support them.
# ─────────────────────────────────────────────────────────────────────
# (No action needed — SQLAlchemy func.ltrim/func.rtrim work on both.)


# ─────────────────────────────────────────────────────────────────────
# Collate helper — MSSQL uses COLLATE Vietnamese_CI_AI,
#                  SQLite has no such collation → fall back to NOCASE.
# ─────────────────────────────────────────────────────────────────────
def safe_ilike(column, pattern):
    """
    Case-insensitive LIKE that works on both MSSQL and SQLite.
    On MSSQL: uses .collate('Vietnamese_CI_AI').ilike()
    On SQLite: uses plain .ilike() (already case-insensitive for ASCII)
    """
    if DEMO_MODE:
        return column.ilike(pattern)
    else:
        return column.collate('Vietnamese_CI_AI').ilike(pattern)

# ─────────────────────────────────────────────────────────────────────
# CAST to Date / Time — MSSQL: CAST(col AS DATE)
#                       SQLite: date(col) or time(col)
# ─────────────────────────────────────────────────────────────────────
from sqlalchemy.sql.elements import Cast
from sqlalchemy.sql.sqltypes import Date, Time

@compiles(Cast, "sqlite")
def _cast_sqlite(element, compiler, **kw):
    if isinstance(element.type, Date):
        return f"date({compiler.process(element.clause, **kw)})"
    if isinstance(element.type, Time):
        return f"time({compiler.process(element.clause, **kw)})"
    return compiler.visit_cast(element, **kw)
