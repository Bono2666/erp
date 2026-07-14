import requests

BASE_URL = "http://localhost:8018"
TIMEOUT = 30

def test_hcm_employee_management_full_crud_and_autofill():
    session = requests.Session()
    try:
        # Step 1: Authenticate with valid credentials
        auth_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "db": "odoo",
                "login": "admin",
                "password": "admin"
            },
            "id": 1
        }
        auth_response = session.post(
            f"{BASE_URL}/web/session/authenticate",
            json=auth_payload,
            timeout=TIMEOUT
        )
        assert auth_response.status_code == 200
        auth_json = auth_response.json()
        assert 'result' in auth_json and 'uid' in auth_json['result'] and auth_json['result']['uid'] is not None, "Authentication failed"

        # Helper function to call call_kw endpoint for various models
        def call_kw(model, method, args=None, kwargs=None):
            if args is None:
                args = []
            if kwargs is None:
                kwargs = {}
            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": model,
                    "method": method,
                    "args": args,
                    "kwargs": kwargs
                },
                "id": 2
            }
            resp = session.post(f"{BASE_URL}/web/dataset/call_kw/{model}", json=payload, timeout=TIMEOUT)
            resp.raise_for_status()
            result = resp.json()
            if "error" in result:
                raise Exception(f"RPC call error: {result['error']}")
            return result.get("result")

        # Step 2: Create necessary address hierarchy: Country, State, City, District, Village
        # Country create
        country_vals = {"name": "TestCountryTC007"}
        country_id = call_kw("general.country", "create", args=[country_vals])
        assert isinstance(country_id, int), "Failed to create country"

        # State create linked to country
        state_vals = {"name": "TestStateTC007", "country_id": country_id}
        state_id = call_kw("general.state", "create", args=[state_vals])
        assert isinstance(state_id, int), "Failed to create state"

        # City create linked to state
        city_vals = {"name": "TestCityTC007", "state_id": state_id}
        city_id = call_kw("general.city", "create", args=[city_vals])
        assert isinstance(city_id, int), "Failed to create city"

        # District create linked to city
        district_vals = {"name": "TestDistrictTC007", "city_id": city_id}
        district_id = call_kw("general.district", "create", args=[district_vals])
        assert isinstance(district_id, int), "Failed to create district"

        # Village create linked to district
        village_vals = {"name": "TestVillageTC007", "district_id": district_id}
        village_id = call_kw("general.village", "create", args=[village_vals])
        assert isinstance(village_id, int), "Failed to create village"

        # Step 3: Create Organization hierarchy: Division, Department, Position
        division_vals = {"name": "TestDivisionTC007"}
        division_id = call_kw("general.division", "create", args=[division_vals])
        assert isinstance(division_id, int), "Failed to create division"

        department_vals = {"name": "TestDepartmentTC007", "division_id": division_id}
        department_id = call_kw("general.department", "create", args=[department_vals])
        assert isinstance(department_id, int), "Failed to create department"

        position_vals = {"name": "TestPositionTC007", "department_id": department_id}
        position_id = call_kw("general.position", "create", args=[position_vals])
        assert isinstance(position_id, int), "Failed to create position"

        # Step 4: Create Employee with address/org hierarchy and test onchange autofill
        employee_vals = {
            "name": "Test Employee TC007",
            "position_id": position_id,
            "department_id": department_id,
            "division_id": division_id,
            "country_id": country_id,
            "state_id": state_id,
            "city_id": city_id,
            "district_id": district_id,
            "village_id": village_id,
            # Assuming address fields names; adjust if actual differs
            "work_email": "employee.tc007@example.com",
        }

        # Create Employee (simulate onchange auto-fill by creating with all hierarchy selected)
        employee_id = call_kw("hcm.employee", "create", args=[employee_vals])
        assert isinstance(employee_id, int), "Failed to create employee"

        try:
            # Step 5: Add Family member linked to employee
            family_vals = {
                "name": "John Doe",
                "relationship": "spouse",  # Assuming such a field exists
                "employee_id": employee_id,
                "birth_date": "1990-01-01"
            }
            family_id = call_kw("hcm.employee.family", "create", args=[family_vals])
            assert isinstance(family_id, int), "Failed to create employee family record"

            # Update family record (edit)
            updated_family_vals = {"relationship": "child"}
            updated_family = call_kw("hcm.employee.family", "write", args=[[family_id], updated_family_vals])
            assert updated_family is True, "Failed to update family record"

            # Read family record
            family_read = call_kw("hcm.employee.family", "read", args=[[family_id]], kwargs={"fields": ["name","relationship"]})
            assert family_read and family_read[0]["relationship"] == "child", "Family record update not persisted"

            # Step 6: Add Education record for employee
            education_vals = {
                "employee_id": employee_id,
                "school_name": "Test University",
                "degree": "BSc Computer Science",
                "year": 2015
            }
            education_id = call_kw("hcm.employee.education", "create", args=[education_vals])
            assert isinstance(education_id, int), "Failed to create employee education record"

            # Step 7: Add Certificate record for employee
            certificate_vals = {
                "employee_id": employee_id,
                "certificate_name": "Certified Tester",
                "date_obtained": "2016-05-01"
            }
            certificate_id = call_kw("hcm.employee.certificate", "create", args=[certificate_vals])
            assert isinstance(certificate_id, int), "Failed to create employee certificate record"

            # Step 8: Add Training record for employee
            training_vals = {
                "employee_id": employee_id,
                "training_name": "Agile Training",
                "completion_date": "2017-09-20"
            }
            training_id = call_kw("hcm.employee.training", "create", args=[training_vals])
            assert isinstance(training_id, int), "Failed to create employee training record"

            # Step 9: Read back employee with embedded related records
            employee_read = call_kw("hcm.employee", "read", args=[[employee_id]], kwargs={"fields": ["name", "position_id", "department_id", "division_id", "family_ids", "education_ids", "certificate_ids", "training_ids", "country_id", "state_id", "city_id", "district_id", "village_id"]})
            assert employee_read and employee_read[0]["name"] == employee_vals["name"], "Failed to read employee record with correct name"
            # Validate related record links
            family_ids = employee_read[0].get("family_ids", [])
            education_ids = employee_read[0].get("education_ids", [])
            certificate_ids = employee_read[0].get("certificate_ids", [])
            training_ids = employee_read[0].get("training_ids", [])
            assert family_id in family_ids, "Family record missing in employee read"
            assert education_id in education_ids, "Education record missing in employee read"
            assert certificate_id in certificate_ids, "Certificate record missing in employee read"
            assert training_id in training_ids, "Training record missing in employee read"

            # Validate auto-fill fields for address and org
            assert employee_read[0].get("country_id") == country_id, "Country ID mismatch in employee record"
            assert employee_read[0].get("state_id") == state_id, "State ID mismatch in employee record"
            assert employee_read[0].get("city_id") == city_id, "City ID mismatch in employee record"
            assert employee_read[0].get("district_id") == district_id, "District ID mismatch in employee record"
            assert employee_read[0].get("village_id") == village_id, "Village ID mismatch in employee record"
            assert employee_read[0].get("position_id") == position_id, "Position ID mismatch in employee record"
            assert employee_read[0].get("department_id") == department_id, "Department ID mismatch in employee record"
            assert employee_read[0].get("division_id") == division_id, "Division ID mismatch in employee record"

            # Step 10: Edit employee's email and save
            new_email = "changed_email_tc007@example.com"
            update_result = call_kw("hcm.employee", "write", args=[[employee_id], {"work_email": new_email}])
            assert update_result is True, "Failed to update employee email"

            # Verify update
            employee_updated = call_kw("hcm.employee", "read", args=[[employee_id]], kwargs={"fields": ["work_email"]})
            assert employee_updated[0]["work_email"] == new_email, "Employee email update not persisted"

            # Step 11: Action Delete related records family, education, certificate, training
            for model, rec_id in [("hcm.employee.family", family_id), ("hcm.employee.education", education_id), ("hcm.employee.certificate", certificate_id), ("hcm.employee.training", training_id)]:
                del_response = call_kw(model, "unlink", args=[[rec_id]])
                assert del_response is True, f"Failed to delete {model} record id {rec_id}"

            # Verify related records deletion
            for model, rec_id in [("hcm.employee.family", family_id), ("hcm.employee.education", education_id), ("hcm.employee.certificate", certificate_id), ("hcm.employee.training", training_id)]:
                search_result = call_kw(model, "search_read", kwargs={"domain": [["id", "=", rec_id]], "fields": ["id"]})
                assert len(search_result) == 0, f"{model} record {rec_id} was not deleted"

            # Step 12: Delete employee record
            emp_del = call_kw("hcm.employee", "unlink", args=[[employee_id]])
            assert emp_del is True, "Failed to delete employee record"

            # Verify employee deletion
            emp_search = call_kw("hcm.employee", "search_read", kwargs={"domain": [["id", "=", employee_id]], "fields": ["id"]})
            assert len(emp_search) == 0, "Employee record was not deleted"

        finally:
            # Cleanup: Delete address hierarchy records
            for model, rec_id in [("general.village", village_id), ("general.district", district_id), ("general.city", city_id), ("general.state", state_id), ("general.country", country_id),
                                  ("general.position", position_id), ("general.department", department_id), ("general.division", division_id)]:
                try:
                    call_kw(model, "unlink", args=[[rec_id]])
                except Exception:
                    pass

    finally:
        session.close()

test_hcm_employee_management_full_crud_and_autofill()
