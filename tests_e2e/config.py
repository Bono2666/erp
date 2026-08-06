import os
import time

BASE_URL = os.environ.get("ODOO_URL", "http://localhost:8018")
DB_NAME = os.environ.get("ODOO_DB", "erp")
LOGIN = os.environ.get("ODOO_LOGIN", "trihambono@gmail.com")
PASSWORD = os.environ.get("ODOO_PASSWORD", "Tr1-B0n0")
TIMEOUT = 30_000


def unique_suffix():
    return time.strftime("%Y%m%d%H%M%S")
