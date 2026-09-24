import json
import urllib.request
from datetime import datetime, timedelta

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


def get_food_name(item):
    food = item.get("food")
    if food and food.get("name"):
        return food["name"].strip()
    return None


def is_side_or_drink(name):
    lower = name.lower()

    excluded_words = [
        "milk",
        "juice",
        "water",
        "fruit",
        "vegetable",
        "veggie",
        "salad",
        "side",
        "cookie",
        "dessert",
        "bread",
        "roll",
        "naan",
        "chips",
        "tostitos",
        "applesauce",
        "condiment",
        "ketchup",
        "mustard",
        "ranch",
        "dressing",
    ]

    return any(word in lower for word in excluded_words)

print("\n===== DEBUG MENU =====")

for day in data.get("days", []):
    if day.get("date"):
        print(f"\nDATE: {day['date']}")

        for i, item in enumerate(day.get("menu_items", [])):
            print(
                f"ITEM {i}: "
                f"position={item.get('position')} | "
                f"text={item.get('text')!r} | "
                f"category={item.get('category')!r} | "
                f"is_section_title={item.get('is_section_title')!r} | "
                f"food={item.get('food', {}).get('name')!r}"
            )

events = []

for day in data.get("days", []):
    date_string = day.get("date")

    if not date_string:
        continue

    items = []

    for item in day.get("menu_items", []):
        name = get_food_name(item)

        if name and name not in items:
            items.append(name)

    if not items:
        continue

    # Identify the main entrée choices.
    entrees = [
        item for item in items
        if not is_side_or_drink(item)
    ]

    # Use up to the first two entrée choices.
    choices = entrees[:2]

    if len(choices) >= 2:
        summary = (
            f"Choice 1: {choices[0]} | "
            f"Choice 2: {choices[1]}"
        )
    elif len(choices) == 1:
        summary = f"Choice 1: {choices[0]}"
    else:
        summary = items[0]

    # Complete menu remains in the event description.
    description = "\\n".join(
        f"• {item}" for item in items
    )

    date_obj = datetime.strptime(
        date_string, "%Y-%m-%d"
    ).date()

    next_date = date_obj + timedelta(days=1)

    events.append(
        f"""BEGIN:VEVENT
DTSTART;VALUE=DATE:{date_obj.strftime("%Y%m%d")}
DTEND;VALUE=DATE:{next_date.strftime("%Y%m%d")}
SUMMARY:{summary}
DESCRIPTION:Otter Lake School Lunch\\n\\n{description}
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