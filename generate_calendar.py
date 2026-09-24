import json
import urllib.request
from datetime import datetime, timedelta, timezone

DISTRICT = "isd624"
SCHOOL = "otter-lake"
MENU_TYPE = "lunch"

today = datetime.now().date()
monday = today - timedelta(days=today.weekday())

url = (
    f"https://{DISTRICT}.api.nutrislice.com/menu/api/weeks/"
    f"school/{SCHOOL}/menu-type/{MENU_TYPE}/"
    f"{monday.year}/{monday.month:02d}/{monday.day:02d}/"
)

request = urllib.request.Request(
    url,
    headers={"User-Agent": "Otter-Lake-Lunch-Calendar/1.0"}
)

with urllib.request.urlopen(request, timeout=20) as response:
    data = json.loads(response.read().decode("utf-8"))

events = []

for day in data.get("days", []):
    date_string = day.get("date")
    if not date_string:
        continue

    items = []

    for item in day.get("menu_items", []):
        food = item.get("food")

        if food and food.get("name"):
            name = food["name"].strip()
            if name and name not in items:
                items.append(name)

    if not items:
        continue

    description = "\\n".join(f"• {item}" for item in items)

    events.append(
        f"""BEGIN:VEVENT
DTSTART;VALUE=DATE:{date_string.replace("-", "")}
DTEND;VALUE=DATE:{(datetime.strptime(date_string, "%Y-%m-%d").date() + timedelta(days=1)).strftime("%Y%m%d")}
SUMMARY:🍎 Otter Lake School Lunch
DESCRIPTION:{description.replace(chr(10), "\\n")}
UID:{date_string}-otter-lake-lunch@github
END:VEVENT"""
    )

ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Otter Lake School Lunch//Nutrislice//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Otter Lake School Lunch
X-WR-TIMEZONE:America/Chicago
""" + "\n".join(events) + "\nEND:VCALENDAR\n"

with open("school-lunch.ics", "w", encoding="utf-8") as f:
    f.write(ics)

print(f"Created calendar with {len(events)} lunch days.")