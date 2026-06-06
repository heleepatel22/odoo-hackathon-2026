import requests
import json
import os

BASE_URL = "http://127.0.0.1:5000/api"
session = requests.Session()

def print_result(name, res):
    print(f"[{res.status_code}] {name}")
    try:
        print("   ", res.json())
    except:
        print("   ", res.text[:200])

def test_all():
    print("--- STARTING API TESTS ---")
    # 1. Register
    res = session.post(f"{BASE_URL}/auth/register", json={
        "name": "Test User",
        "email": "test@vendorbridge.com",
        "password": "password123",
        "role": "procurement_officer"
    })
    # Might return 400 if already exists, that's fine
    print_result("Register", res)
    
    # 2. Login
    res = session.post(f"{BASE_URL}/auth/login", json={
        "email": "test@vendorbridge.com",
        "password": "password123"
    })
    print_result("Login", res)
    if res.status_code != 200:
        print("Cannot continue without login")
        return
        
    token = res.json().get('access_token')
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Auth Me
    res = session.get(f"{BASE_URL}/auth/me", headers=headers)
    print_result("Auth Me GET", res)
    
    # 4. Auth Me PUT
    res = session.put(f"{BASE_URL}/auth/me", headers=headers, json={"name": "Updated Test User"})
    print_result("Auth Me PUT", res)

    # 5. Dashboard Summary
    res = session.get(f"{BASE_URL}/dashboard/summary", headers=headers)
    print_result("Dashboard Summary", res)

    # 6. Reports (with and without month/year)
    res = session.get(f"{BASE_URL}/reports/", headers=headers)
    print_result("Reports", res)
    
    res = session.get(f"{BASE_URL}/reports/?month=6&year=2026", headers=headers)
    print_result("Reports (Filtered)", res)

    # 7. Vendors GET
    res = session.get(f"{BASE_URL}/vendors/", headers=headers)
    print_result("Vendors GET", res)

    # 8. Vendors POST
    res = session.post(f"{BASE_URL}/vendors/", headers=headers, json={
        "company_name": "Test Vendor",
        "category_name": "IT Hardware",
        "gst_number": "GST12345678",
        "phone": "9999999999",
        "email": "vendor@test.com"
    })
    print_result("Vendors POST", res)
    vendor_id = None
    if res.status_code in [200, 201]:
        # Usually vendors list returns ID, let's fetch list
        v_list = session.get(f"{BASE_URL}/vendors/", headers=headers).json()
        if len(v_list) > 0:
            vendor_id = v_list[-1]['id']

    # 9. RFQ POST
    res = session.post(f"{BASE_URL}/rfqs/", headers=headers, json={
        "title": "Test RFQ",
        "deadline": "2026-12-31",
        "description": "A test RFQ",
        "items": [
            {"product_name": "Laptop", "quantity": 10, "unit": "NOS"}
        ]
    })
    print_result("RFQ POST", res)
    
    # 10. Settings PUT
    res = session.put(f"{BASE_URL}/settings/", headers=headers, json={
        "email_notifications": True
    })
    print_result("Settings PUT", res)
    
    # 11. Activity GET
    res = session.get(f"{BASE_URL}/activity/", headers=headers)
    print_result("Activity GET", res)
    
    print("--- API TESTS FINISHED ---")

if __name__ == "__main__":
    test_all()
