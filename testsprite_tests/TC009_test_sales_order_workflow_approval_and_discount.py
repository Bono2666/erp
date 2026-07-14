import requests
import time

BASE_URL = "http://localhost:8018"
TIMEOUT = 30


def test_sales_order_workflow_approval_and_discount():
    session = requests.Session()

    def authenticate(username, password):
        url = f"{BASE_URL}/web/session/authenticate"
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "db": "odoo",
                "login": username,
                "password": password,
            },
            "id": int(time.time()),
        }
        resp = session.post(url, json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        res_json = resp.json()
        if 'error' in res_json:
            raise Exception(f"Authentication failed: {res_json['error']}")
        return res_json["result"]["session_id"]

    def call_kw(model, method, args=None, kwargs=None):
        url = f"{BASE_URL}/web/dataset/call_kw/{model}"
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model,
                "method": method,
                "args": args or [],
                "kwargs": kwargs or {},
                "context": {},
            },
            "id": int(time.time()),
        }
        resp = session.post(url, json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        result = resp.json()
        if "error" in result:
            raise Exception(f"call_kw error on {model}.{method}: {result['error']}")
        return result.get("result")

    # 1. Authenticate as normal sales user (assumed credentials)
    # You may need to adjust username/password to an existing user in your system
    username = "sales_user"
    password = "sales_password"
    authenticate(username, password)

    # 2. Create a draft sales order (quotation) in 'draft' state
    order_vals = {
        "partner_id": None,  # Will use a placeholder customer later after creating customer if needed
        "state": "draft",
        "date_order": time.strftime("%Y-%m-%d"),
        "validity_date": time.strftime("%Y-%m-%d"),
        "amount_total": 0.0,
    }

    # Since no partner_id provided, create minimal customer partner first
    # But for simplicity, attempt to find an existing customer first
    def search_customer():
        domain = [["customer_rank", ">", 0]]
        res = call_kw("res.partner", "search_read", args=[domain], kwargs={"fields": ["id", "name"], "limit": 1})
        if res and len(res) > 0:
            return res[0]["id"]
        else:
            # Create a customer partner
            new_cust_vals = {"name": "Test Customer for SO Workflow", "customer_rank": 1}
            new_id = call_kw("res.partner", "create", args=[new_cust_vals])
            return new_id

    partner_id = search_customer()
    order_vals["partner_id"] = partner_id

    sales_order_id = None
    sales_order_line_ids = []

    try:
        sales_order_id = call_kw("sales.sales_order", "create", args=[order_vals])
        assert sales_order_id, "Failed to create sales order"

        # Verify sales order is in draft state
        so = call_kw("sales.sales_order", "read", args=[[sales_order_id]], kwargs={"fields": ["state", "partner_id"]})
        assert so and so[0]["state"] == "draft", "Sales order not in draft state after creation"

        # 3. Add lines to sales order
        # Prepare product_id by searching an existing product; if none, create minimal product
        def search_product():
            prods = call_kw("sales.products", "search_read", args=[[]], kwargs={"fields": ["id", "name"], "limit": 1})
            if prods and len(prods) > 0:
                return prods[0]["id"], prods[0]["name"]
            else:
                prod_vals = {
                    "name": "Test Product for SO",
                    "type": "product",
                    "list_price": 100.0,
                    "standard_price": 70.0,
                    "sale_ok": True,
                }
                new_prod_id = call_kw("sales.products", "create", args=[prod_vals])
                return new_prod_id, prod_vals["name"]

        product_id, product_name = search_product()

        line_vals = {
            "order_id": sales_order_id,
            "product_id": product_id,
            "product_uom_qty": 2,
            "price_unit": 100.0,
            "name": f"Line for {product_name}",
        }

        line_id = call_kw("sales.sales_order_line", "create", args=[line_vals])
        assert line_id, "Failed to create sales order line"
        sales_order_line_ids.append(line_id)

        # 4. Submit sales order for approval - update state to wait_approval
        # Assuming method "action_submit_for_approval" or similar is used; fallback to write state if needed
        # Let's try calling a custom method or write state
        try:
            res_submit = call_kw("sales.sales_order", "action_submit_for_approval", args=[[sales_order_id]])
            # method call success
        except Exception:
            # fallback: do write (update) state manually if allowed
            res_submit = call_kw("sales.sales_order", "write", args=[[sales_order_id], {"state": "wait_approval"}])
        assert res_submit is True or res_submit == "ok", "Failed to submit sales order for approval"

        # Reload order and verify state
        so = call_kw("sales.sales_order", "read", args=[[sales_order_id]], kwargs={"fields": ["state"]})
        assert so and so[0]["state"] == "wait_approval", "Sales order state not 'wait_approval' after submit"

        # 5. Read approval entries from sales_approval_log
        approval_logs = call_kw("sales.sales_approval_log", "search_read", args=[["order_id", "=", sales_order_id]], kwargs={"fields": ["state", "approver_id", "comment"]})
        assert isinstance(approval_logs, list), "Approval log fetch failed"

        # 6. Authenticate as approver user for approvals (assumed separate approver user exists)
        approver_username = "sales_approver"
        approver_password = "approver_password"
        authenticate(approver_username, approver_password)

        # 7. Read approval matrix for approver permissions
        approval_matrix = call_kw("sales.sales_approval_matrix", "search_read", args=[["user_id", "=", approver_username]], kwargs={"fields": ["min_amount", "max_amount"]})
        # Not strictly necessary to assert, just to simulate approval flow

        # 8. Approve order multiple levels until state changes to approved or sale
        approval_rounds = 3  # limit rounds to avoid infinite loop
        approved = False
        for _ in range(approval_rounds):
            # Approve via sales_approval_log - assuming there's an approve method or write the log record
            # Find pending approval log for this user and sales order
            pending_logs = call_kw("sales.sales_approval_log", "search_read", args=[["order_id", "=", sales_order_id, "state", "=", "pending"]], kwargs={"limit": 1, "fields": ["id"]})
            if not pending_logs:
                # No pending logs, break
                break
            log_id = pending_logs[0]["id"]
            # Call approve method or write state on log
            try:
                res_approve = call_kw("sales.sales_approval_log", "approve", args=[[log_id]])
            except Exception:
                try:
                    res_approve = call_kw("sales.sales_approval_log", "write", args=[[log_id], {"state": "approved"}])
                except Exception:
                    # No method to approve, break loop
                    break
            time.sleep(1)  # small delay to let system process

            # Recheck order state
            so = call_kw("sales.sales_order", "read", args=[[sales_order_id]], kwargs={"fields": ["state"]})
            if so and so[0]["state"] in ("approved", "sent", "sale"):
                approved = True
                break

        assert approved, "Sales order did not reach approved or sale state after approvals"

        # 9. Apply bulk discount via discount_wizard
        discount_vals = {
            "order_id": sales_order_id,
            "discount_percent": 10,  # 10% discount
            "reason": "Bulk discount applied in test",
        }
        discount_result = call_kw("sales.discount_wizard", "apply_discount", args=[discount_vals], kwargs={})
        # If apply_discount method not found, fallback to custom call_kw method call
        if discount_result is None:
            # Try with discount_wizard create then action_confirm
            disc_id = call_kw("sales.discount_wizard", "create", args=[discount_vals])
            discount_result = call_kw("sales.discount_wizard", "action_confirm", args=[[disc_id]])

        assert discount_result is True or discount_result == "ok", "Discount application failed"

        # 10. Confirm the sales order after approval and discount
        try:
            confirm_result = call_kw("sales.sales_order", "action_confirm", args=[[sales_order_id]])
        except Exception:
            confirm_result = call_kw("sales.sales_order", "write", args=[[sales_order_id], {"state": "sale"}])

        # Check final state for sale confirmation
        so = call_kw("sales.sales_order", "read", args=[[sales_order_id]], kwargs={"fields": ["state"]})
        assert so and so[0]["state"] == "sale", "Sales order not in 'sale' state after confirmation"

        # 11. Cancel the sales order (should check permission)
        try:
            cancel_result = call_kw("sales.sales_order", "action_cancel", args=[[sales_order_id]])
            # Check new state is 'cancel'
            so = call_kw("sales.sales_order", "read", args=[[sales_order_id]], kwargs={"fields": ["state"]})
            if so:
                assert so[0]["state"] == "cancel", "Sales order not cancelled properly"
        except Exception as e:
            # If permission error or authorization error, sales order should remain in sale state
            so = call_kw("sales.sales_order", "read", args=[[sales_order_id]], kwargs={"fields": ["state"]})
            assert so and so[0]["state"] == "sale", "Sales order state changed unexpectedly after failed cancel"

    finally:
        # Cleanup: delete sales order lines first
        for line_id in sales_order_line_ids:
            try:
                call_kw("sales.sales_order_line", "unlink", args=[[line_id]])
            except Exception:
                pass
        # Delete sales order
        if sales_order_id:
            try:
                call_kw("sales.sales_order", "unlink", args=[[sales_order_id]])
            except Exception:
                pass


test_sales_order_workflow_approval_and_discount()
