import requests

BASE_URL = "http://localhost:8018"
TIMEOUT = 30

LOGIN_PAYLOAD = {
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "db": "erp",
        "login": "trihambono@gmail.com",
        "password": "Tr1-B0n0",
    }
}


def login():
    response = requests.post(
        f"{BASE_URL}/web/session/authenticate",
        json=LOGIN_PAYLOAD,
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    result = response.json()
    if "result" not in result or "uid" not in result["result"]:
        raise Exception("Login failed or invalid response format")
    session_id = result.get("result", {}).get("session_id")
    csrf_token = response.cookies.get("csrf_token")
    return result["result"]["uid"], session_id, csrf_token, response.cookies


def call_kw(model, method, args=None, kwargs=None, fields=None, context=None, session=None, cookies=None, csrf_token=None):
    headers = {
        "Content-Type": "application/json",
        "X-Openerp-Session-Id": session if session else "",
    }
    if csrf_token:
        headers["X-CSRF-TOKEN"] = csrf_token

    data = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": model,
            "method": method,
            "args": args or [],
            "kwargs": kwargs or {},
        },
    }
    if fields is not None:
        data["params"]["kwargs"]["fields"] = fields
    if context is not None:
        data["params"]["kwargs"]["context"] = context

    resp = requests.post(
        f"{BASE_URL}/web/dataset/call_kw",
        json=data,
        headers=headers,
        cookies=cookies,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    result = resp.json()
    if "error" in result:
        raise Exception(f"Server returned error: {result['error']}")
    return result.get("result")


def create_resource(model, values, session, cookies, csrf_token):
    return call_kw(
        model=model,
        method="create",
        args=[values],
        session=session,
        cookies=cookies,
        csrf_token=csrf_token,
    )


def unlink_resource(model, record_id, session, cookies, csrf_token):
    return call_kw(
        model=model,
        method="unlink",
        args=[[record_id]],
        session=session,
        cookies=cookies,
        csrf_token=csrf_token,
    )


def write_resource(model, record_id, values, session, cookies, csrf_token):
    return call_kw(
        model=model,
        method="write",
        args=[[record_id], values],
        session=session,
        cookies=cookies,
        csrf_token=csrf_token,
    )


def browse_resource(model, record_id, fields, session, cookies, csrf_token):
    return call_kw(
        model=model,
        method="read",
        args=[[record_id]],
        kwargs={"fields": fields},
        session=session,
        cookies=cookies,
        csrf_token=csrf_token,
    )


def post_invoice(invoice_id, session, cookies, csrf_token):
    # Posting invoice might be a workflow action or custom method
    # Often Odoo uses button_post or action_post; check /web/dataset/call_kw for 'button_validate', 'action_post', or similar
    return call_kw(
        model="sales.invoice",
        method="action_post",
        args=[[invoice_id]],
        session=session,
        cookies=cookies,
        csrf_token=csrf_token,
    )


def test_billto_selection_on_invoice_creation_and_validation():
    uid, session, csrf_token, cookies = login()

    # Step 1: Obtain a valid bill_to_id for testing
    domain = []  # no filter, get multiple bill_to records
    bill_to_ids = call_kw(
        model="sales.bill_to",
        method="search",
        args=[domain],
        kwargs={"limit": 1},
        session=session,
        cookies=cookies,
        csrf_token=csrf_token,
    )
    assert bill_to_ids, "No Bill To records found to perform test."

    valid_bill_to_id = bill_to_ids[0]

    # Step 2: Get a valid customer
    customer_ids = call_kw(
        model="sales.customer",
        method="search",
        args=[[]],
        kwargs={"limit": 1},
        session=session,
        cookies=cookies,
        csrf_token=csrf_token,
    )
    assert customer_ids, "No sales.customer record found."
    customer_id = customer_ids[0]

    # Create a sales order with minimal data (customer only)
    sales_order_vals = {
        "customer_id": customer_id,
    }

    sales_order_id = None
    invoice_id = None
    try:
        # Create sales order
        sales_order_id = create_resource(
            "sales.sales_order", sales_order_vals, session, cookies, csrf_token
        )
        assert isinstance(sales_order_id, int), "Failed to create sales order"

        # Create invoice with valid bill_to_id and minimal required fields
        invoice_vals_valid = {
            "sales_order_id": sales_order_id,
            "customer_id": customer_id,
            "bill_to_id": valid_bill_to_id,
            "document_type": "invoice",
            "invoice_type": "regular",
        }
        invoice_id = create_resource(
            "sales.invoice", invoice_vals_valid, session, cookies, csrf_token
        )
        assert isinstance(invoice_id, int), "Failed to create invoice with valid bill_to_id"

        # Read invoice to verify bill_to_id and billing address resolved
        invoice_data = browse_resource(
            "sales.invoice", invoice_id, ["bill_to_id", "customer_address"], session, cookies, csrf_token
        )
        assert invoice_data, "Invoice data not found after creation"
        invoice_record = invoice_data[0]
        assert invoice_record.get("bill_to_id") and invoice_record["bill_to_id"][0] == valid_bill_to_id, "bill_to_id mismatch on invoice"

        # Attempt to create invoice with invalid bill_to_id
        invalid_bill_to_id = -1  # Usually negative IDs do not exist
        invoice_vals_invalid = {
            "sales_order_id": sales_order_id,
            "customer_id": customer_id,
            "bill_to_id": invalid_bill_to_id,
            "document_type": "invoice",
            "invoice_type": "regular",
        }
        error_raised = False
        try:
            create_resource("sales.invoice", invoice_vals_invalid, session, cookies, csrf_token)
        except Exception as e:
            error_raised = True
            assert "bill_to_id" in str(e) or "relation" in str(e) or "Validation" in str(e), f"Unexpected error message: {str(e)}"
        assert error_raised, "Creating invoice with invalid bill_to_id did not raise error"

        # Create a valid invoice first to test update with invalid bill_to_id
        invoice_update_id = create_resource(
            "sales.invoice", invoice_vals_valid, session, cookies, csrf_token
        )
        assert isinstance(invoice_update_id, int), "Failed to create invoice for update test"

        error_raised = False
        try:
            write_resource(
                "sales.invoice",
                invoice_update_id,
                {"bill_to_id": invalid_bill_to_id},
                session,
                cookies,
                csrf_token,
            )
        except Exception as e:
            error_raised = True
            assert "bill_to_id" in str(e) or "relation" in str(e) or "Validation" in str(e), f"Unexpected error message on update: {str(e)}"
        assert error_raised, "Updating invoice with invalid bill_to_id did not raise error"

        # Cleanup invoice_update_id
        unlink_resource(
            "sales.invoice", invoice_update_id, session, cookies, csrf_token
        )
    finally:
        # Cleanup created invoice and sales order if exist
        if invoice_id:
            try:
                unlink_resource("sales.invoice", invoice_id, session, cookies, csrf_token)
            except:
                pass
        if sales_order_id:
            try:
                unlink_resource("sales.sales_order", sales_order_id, session, cookies, csrf_token)
            except:
                pass


test_billto_selection_on_invoice_creation_and_validation()
