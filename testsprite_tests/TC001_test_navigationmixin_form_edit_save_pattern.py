import requests
import xml.etree.ElementTree as ET

BASE_URL = "http://localhost:8018"
TIMEOUT = 30

class OdooSession:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json"
        })
        self.session_id = None
        self.csrf_token = None

    def login(self, db, login, password):
        # Step 1 GET /web/login to get initial cookies and csrf token if any
        r = self.session.get(f"{self.base_url}/web/login", timeout=TIMEOUT)
        r.raise_for_status()
        # Typically Odoo does not require explicit CSRF token header, but good to check cookies

        # Step 2 POST /web/session/authenticate
        auth_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "db": db,
                "login": login,
                "password": password,
                "context": {}
            },
            "id": 1
        }
        r = self.session.post(f"{self.base_url}/web/session/authenticate", json=auth_payload, timeout=TIMEOUT)
        r.raise_for_status()
        res = r.json()
        assert 'result' in res and 'uid' in res['result'], "Authentication failed"
        self.session_id = self.session.cookies.get('session_id')
        return res['result']

    def call_kw(self, model, method, args=None, kwargs=None, context=None):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model,
                "method": method,
                "args": args if args else [],
                "kwargs": kwargs if kwargs else {},
                "context": context if context else {}
            },
            "id": 1
        }
        r = self.session.post(f"{self.base_url}/web/dataset/call_kw", json=payload, timeout=TIMEOUT)
        r.raise_for_status()
        res = r.json()
        if 'error' in res:
            raise Exception(f"Error calling {model}.{method}: {res['error']}")
        return res.get('result')

    def get_view(self, model, view_id, view_type="form", options=None):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model,
                "view_id": view_id,
                "view_type": view_type,
                "context": {},
                "options": options if options else {}
            },
            "id": 1
        }
        r = self.session.post(f"{self.base_url}/web/view", json=payload, timeout=TIMEOUT)
        r.raise_for_status()
        res = r.json()
        if 'error' in res:
            raise Exception(f"Error getting view: {res['error']}")
        return res.get('result')

def test_navigationmixin_form_edit_save_pattern():
    odoo = OdooSession(BASE_URL)
    # Use default database and credentials for test admin
    db = "odoo"
    login = "admin"
    password = "admin"
    odoo.login(db, login, password)

    model = "general.country"  # Using master-data form: general.country is a simple one with known presence

    # Step 1: Create a new resource to test on (country)
    country_vals = {
        "name": "Testland",
        "code": "TL"
    }
    country_id = None
    try:
        # Create new country record with create() ORM method via call_kw
        country_id = odoo.call_kw(model, "create", args=[country_vals])
        assert isinstance(country_id, int) and country_id > 0, "Failed to create country record"

        # Step 2: GET /web/view for the country form with readonly injection check
        # Need to find the form view id for general.country; typically can search, but as no ID provided,
        # we fetch a form view from server. We do a search_read on ir.ui.view for a form view of general.country
        # to find suitable view_id.
        view_search_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "ir.ui.view",
                "domain": [["model", "=", model], ["type", "=", "form"]],
                "fields": ["id", "name"],
                "limit": 1
            },
            "id": 1
        }
        r = odoo.session.post(f"{BASE_URL}/web/dataset/search_read", json=view_search_payload, timeout=TIMEOUT)
        r.raise_for_status()
        views_res = r.json()
        assert 'result' in views_res and len(views_res['result'].get('records', [])) > 0, "No form view found for model"
        view_id = views_res['result']['records'][0]['id']

        form_view = odoo.get_view(model, view_id, view_type="form")
        assert form_view and 'arch' in form_view, "Form view arch not returned"
        xml_arch = form_view['arch']

        # Parse XML and confirm readonly injected on sheet fields (NavigationMixin effect)
        root = ET.fromstring(xml_arch)
        sheet_elems = root.findall(".//sheet")
        assert len(sheet_elems) > 0, "No sheet element found in form view XML"

        # Check readonly attribute injected on fields inside sheet (excluding buttons)
        readonly_injected = False
        for sheet in sheet_elems:
            for field in sheet.findall(".//field"):
                readonly = field.attrib.get("readonly", None)
                if readonly == "1" or readonly == "true":
                    readonly_injected = True
                    break
            if readonly_injected:
                break
        assert readonly_injected, "Readonly attribute not injected on form fields in view mode"

        # Step 3: POST /web/dataset/call_kw with action_edit to switch form to edit mode for the created record
        res_edit = odoo.call_kw(model, "action_edit", args=[[country_id]])
        assert isinstance(res_edit, dict), "action_edit did not return dict result"
        # Check that the form is reopened in edit mode: XML with readonly removed

        # Step 4: POST /web/dataset/call_kw with action_save with valid data (simply resave same data)
        # For save, must use write method on the record with same or updated data
        updated_vals = {
            "name": "Testland Edited"
        }
        res_save = odoo.call_kw(model, "write", args=[[country_id], updated_vals])
        assert res_save is True, "action_save (write) returned False"

        # Step 5: Reload form view and check readonly injected (view mode) and name is updated
        form_view_after_save = odoo.get_view(model, view_id, view_type="form")
        xml_after_save = form_view_after_save['arch']
        root_after = ET.fromstring(xml_after_save)
        # Confirm readonly injection again on sheet fields
        readonly_injected_after = False
        for sheet in root_after.findall(".//sheet"):
            for field in sheet.findall(".//field"):
                readonly = field.attrib.get("readonly", None)
                if readonly == "1" or readonly == "true":
                    readonly_injected_after = True
                    break
            if readonly_injected_after:
                break
        assert readonly_injected_after, "Readonly attribute not injected on form fields after save"

        # Additionally verify the name is updated via read
        res_read = odoo.call_kw(model, "read", args=[[country_id]], kwargs={"fields": ["name"]})
        assert res_read and isinstance(res_read, list), "Read returned invalid response"
        assert res_read[0].get("name") == "Testland Edited", "Record name not updated after save"

        # Step 6: POST /web/dataset/call_kw with action_delete to delete the record
        res_delete = odoo.call_kw(model, "unlink", args=[[country_id]])
        assert res_delete is True, "Delete (unlink) operation failed"

        # Confirm deletion by search_read no longer returning the record
        search_res = odoo.call_kw(model, "search_read", args=[[["id", "=", country_id]]])
        assert isinstance(search_res, list), "search_read did not return list"
        assert len(search_res) == 0, "Record not deleted, still found on search_read"

    finally:
        # Clean up in case delete failed
        if country_id:
            try:
                odoo.call_kw(model, "unlink", args=[[country_id]])
            except Exception:
                pass

test_navigationmixin_form_edit_save_pattern()