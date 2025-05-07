import requests
import frappe
from datetime import datetime
import pytz

local_tz = pytz.timezone('Africa/Cairo')

def log(msg, title="✅ Jibble Sync"):
    msg = str(msg)
    if len(msg) > 1000:
        msg = msg[:997] + '...'
    if len(title) > 140:
        title = title[:137] + '...'
    frappe.log_error(msg, title)

def get_access_token():
    settings = frappe.get_single("Jibble API Settings")
    client_id = settings.client_id
    client_secret = settings.get_password('client_secret')
    url = 'https://identity.prod.jibble.io/connect/token'
    headers = {'Accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    }
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json().get('access_token')
    else:
        log(f"Failed to get access token: {response.text}", "Jibble Auth Error")
        return None

def fetch_time_entries(date, token):
    url = f"https://time-tracking.prod.jibble.io/v1/TimeEntries?$count=true&$expand=person($select=id,fullName)&$filter=(belongsToDate eq {date} and status ne 'Archived')&$orderby=time asc"
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get('value', [])
    else:
        log(f"Failed to fetch time entries: {response.text[:300]}", "Jibble API Error")
        return []

def fetch_user_profiles(token):
    url = "https://workspace.prod.jibble.io/v1/People"
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("value", [])
    else:
        log(f"Failed to fetch user profiles: {response.text[:300]}", "Jibble API Error")
        return []

def fetch_attendance_data(date):
    token = get_access_token()
    if not token:
        return []

    profiles = fetch_user_profiles(token)
    time_entries = fetch_time_entries(date, token)

    person_email_map = {person.get("id"): person.get("email") for person in profiles if person.get("id")}
    person_name_map = {person.get("id"): person.get("fullName") for person in profiles if person.get("id")}

    for entry in time_entries:
        pid = entry.get("personId")
        entry["email"] = person_email_map.get(pid)
        entry["fallback_name"] = person_name_map.get(pid).strip().lower() if person_name_map.get(pid) else None

    return time_entries

def fetch_employee_map():
    employees = frappe.get_all("Employee", fields=["name", "user_id", "employee_name"])
    email_map = {emp["user_id"]: emp["name"] for emp in employees if emp.get("user_id")}
    name_map = {emp["employee_name"].strip().lower(): emp["name"] for emp in employees if emp.get("employee_name")}
    user_email_map = {emp["name"]: emp["user_id"] for emp in employees if emp.get("name") and emp.get("user_id")}
    return email_map, name_map, user_email_map

def parse_timestamp(ts):
    try:
        ts = ts.split('.')[0].replace('Z', '')
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=pytz.UTC)
    except Exception as e:
        log(f"Timestamp error: {ts} | {e}", "Jibble Timestamp Error")
        return None

def create_checkin(employee_id, email, timestamp, log_type, working_hours, location, user_email_map):
    dt_utc = parse_timestamp(timestamp)
    if not dt_utc:
        return

    dt_local = dt_utc.astimezone(local_tz)
    time_str = dt_local.strftime("%Y-%m-%d %H:%M:%S")

    if not location:
        location = {"latitude": 29.967764, "longitude": 31.250816}

    exists = frappe.get_all("Employee Checkin", filters={
        "employee": employee_id,
        "time": time_str,
        "log_type": log_type.upper()
    })

    if exists:
        return

    final_email = email or user_email_map.get(employee_id)

    doc = frappe.get_doc({
        "doctype": "Employee Checkin",
        "employee": employee_id,
        "time": time_str,
        "log_type": log_type.upper(),
        "working_hour": working_hours,
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
        "employee_email": final_email
    })

    doc.insert(ignore_permissions=True)
    frappe.db.commit()

def process_and_store_data():
    date_today = datetime.today().strftime("%Y-%m-%d")
    entries = fetch_attendance_data(date_today)
    if not entries:
        log("No entries fetched from Jibble.", "Fetched 0 entries")
        return

    email_map, name_map, user_email_map = fetch_employee_map()
    checkin_map = {}

    for entry in entries:
        email = entry.get("email")
        fallback_name = entry.get("fallback_name")

        employee_id = email_map.get(email)
        if not employee_id and fallback_name:
            employee_id = name_map.get(fallback_name)

        if not employee_id:
            log(f"No employee match for: Email={email}, Name={fallback_name}", "Missing Employee")
            continue

        log_type = entry.get("type")
        timestamp = entry.get("time")
        location = entry.get("coordinates", {})

        working_hour = 0
        person_id = entry.get("personId")

        if log_type == "In":
            checkin_map[person_id] = timestamp
        elif log_type == "Out" and person_id in checkin_map:
            check_in_time = parse_timestamp(checkin_map[person_id])
            check_out_time = parse_timestamp(timestamp)
            if check_in_time and check_out_time:
                working_hour = (check_out_time - check_in_time).total_seconds() / 3600

        create_checkin(employee_id, email, timestamp, log_type, working_hour, location, user_email_map)

    log("✅ Jibble Sync completed successfully", "Success")
