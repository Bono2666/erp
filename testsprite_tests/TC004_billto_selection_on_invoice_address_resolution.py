import requests

BASE_URL = "http://localhost:8018"
TIMEOUT = 30

LOGIN_EMAIL = "trihambono@gmail.com"
LOGIN_PASSWORD = "Tr1-B0n0"
DB = "erp"

HEADERS_JSON = {"Content-Type": "application/json"}
SESSION = requests.Session()

def login():
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": DB,
            "login": LOGIN_EMAIL,
            "password": LOGIN_PASSWORD,
        },
        "id": 1,
    }
    resp = SESSION.post(f"{BASE_URL}/web/session/authenticate", json=payload, headers=HEADERS_JSON, timeout=TIMEOUT)
    resp.raise_for_status()
    res_json = resp.json()
    if "result" not in res_json or "uid" not in res_json["result"]:
        raise Exception("Authentication failed, no uid found.")
    return res_json["result"]["uid"]

def call_kw(model, method, args=None, kwargs=None, context=None):
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}
    params = {
        "model": model,
        "method": method,
        "args": args,
        "kwargs": kwargs,
        "context": context or {},
    }
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": params,
        "id": 1,
    }
    resp = SESSION.post(f"{BASE_URL}/web/dataset/call_kw", json=payload, headers=HEADERS_JSON, timeout=TIMEOUT)
    resp.raise_for_status()
    res_json = resp.json()
    if "error" in res_json:
        raise Exception(res_json["error"])
    return res_json.get("result")

def test_billto_selection_on_invoice_address_resolution():
    # Login and get uid/session
    uid = login()

    created_sales_order_id = None
    created_invoice_id = None
    created_customer_id = None
    created_bill_to_id = None

    try:
        # Step 1: Create a Customer (sales.customer) with required fields
        customer_vals = {
            "customer_name": "Test Customer for TC004",
            "cust_category": 1,
            "email": "tc004_test@example.com",
        }
        created_customer_id = call_kw("sales.customer", "create", args=[customer_vals])
        assert isinstance(created_customer_id, int) and created_customer_id > 0, "Failed to create customer."

        # Step 2: Create a Bill To record linked to the customer (sales.bill_to)
        bill_to_vals = {
            "bill_name": "Test Bill To Address",
            "customer_id": created_customer_id,
            "address": "123 Billing St, BillingCity, 12345",
        }
        created_bill_to_id = call_kw("sales.bill_to", "create", args=[bill_to_vals])
        assert isinstance(created_bill_to_id, int) and created_bill_to_id > 0, "Failed to create Bill To record."

        # Step 3: Create a Sales Order linked to the customer, with bill_to_id set
        sales_order_vals = {
            "customer_id": created_customer_id,
            "bill_to_id": created_bill_to_id,
        }
        created_sales_order_id = call_kw("sales.sales_order", "create", args=[sales_order_vals])
        assert isinstance(created_sales_order_id, int) and created_sales_order_id > 0, "Failed to create Sales Order."

        # Step 4: Retrieve Sales Order to confirm bill_to_id is populated
        sales_order_read_fields = ["id", "customer_id", "bill_to_id"]
        sales_order_data = call_kw("sales.sales_order", "read", args=[[created_sales_order_id], sales_order_read_fields])
        assert sales_order_data and len(sales_order_data) == 1, "Sales Order read failed."
        sales_order = sales_order_data[0]
        assert sales_order["bill_to_id"][0] == created_bill_to_id, "bill_to_id on Sales Order incorrect."

        # Step 5: Create Invoice from Sales Order with bill_to_id resolution
        invoice_vals = {
            "sales_order_id": created_sales_order_id,
            "customer_id": created_customer_id,
            "bill_to_id": created_bill_to_id,
            "document_type": "invoice",
            "invoice_type": "regular",
            "customer_address": "123 Billing St, BillingCity, 12345",
        }
        created_invoice_id = call_kw("sales.invoice", "create", args=[invoice_vals])
        assert isinstance(created_invoice_id, int) and created_invoice_id > 0, "Failed to create Invoice."

        # Step 6: Read Invoice to verify bill_to_id and billing address resolution
        invoice_read_fields = ["id", "bill_to_id", "customer_address"]
        invoice_data = call_kw("sales.invoice", "read", args=[[created_invoice_id], invoice_read_fields])
        assert invoice_data and len(invoice_data) == 1, "Invoice read failed."
        invoice = invoice_data[0]

        # Check bill_to_id matches expected
        assert invoice["bill_to_id"][0] == created_bill_to_id, "bill_to_id on Invoice not resolved correctly."

        # Validate customer_address field exists and contains expected content related to bill_to
        customer_address = invoice.get("customer_address")
        assert customer_address and isinstance(customer_address, str), "Billing address not resolved or missing."

        # Expected substrings from bill_to for address validation
        assert "123 Billing St" in customer_address, "Billing address does not contain street info."

    finally:
        # Cleanup created records in reverse order
        if created_invoice_id:
            try:
                call_kw("sales.invoice", "unlink", args=[[created_invoice_id]])
            except Exception:
                pass
        if created_sales_order_id:
            try:
                call_kw("sales.sales_order", "unlink", args=[[created_sales_order_id]])
            except Exception:
                pass
        if created_bill_to_id:
            try:
                call_kw("sales.bill_to", "unlink", args=[[created_bill_to_id]])
            except Exception:
                pass
        if created_customer_id:
            try:
                call_kw("sales.customer", "unlink", args=[[created_customer_id]])
            except Exception:
                pass

test_billto_selection_on_invoice_address_resolution()