import json
import urllib.request
from datetime import datetime, timedelta
import re


DISTRICT = "isd624"
SCHOOL = "otter-lake"
MENU_TYPE = "lunch"


# ---------------------------------------------------------
# Get this week's Nutrislice menu
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def get_food_name(item):
    food = item.get("food")

    if food and food.get("name"):
        return food["name"].strip()

    return None


def escape_ics(text):
    """
    Escape characters required by the iCalendar format.
    """
    if not text:
        return ""

    return (
        str(text)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def is_choice_heading(item):
    """
    Detect headings such as:
    Choice 1
    Choice 2
    Choice 3
    """

    text = (item.get("text") or "").strip()

    return (
        bool(re.match(r"^choice\s+\d+$", text, re.IGNORECASE))
        or (
            item.get("is_section_title") is True
            and text.lower().startswith("choice ")
        )
    )


def get_choice_number(text):
    match = re.match(
        r"^choice\s+(\d+)$",
        text.strip(),
        re.IGNORECASE
    )

    if match:
        return int(match.group(1))

    return None


# ---------------------------------------------------------
# Build calendar events
# ---------------------------------------------------------

events = []


for day in data.get("days", []):

    date_string = day.get("date")

    if not date_string:
        continue


    menu_items = day.get("menu_items", [])


    # -----------------------------------------------------
    # First, organize the menu according to Nutrislice's
    # actual Choice 1 / Choice 2 / Choice 3 headings.
    # -----------------------------------------------------

    choices = {}
    current_choice = None

    all_menu_lines = []


    for item in menu_items:

        text = (item.get("text") or "").strip()
        food_name = get_food_name(item)


        # Detect Choice 1 / Choice 2 / Choice 3
        if is_choice_heading(item):

            current_choice = get_choice_number(text)

            if current_choice is not None:
                choices.setdefault(current_choice, [])

                all_menu_lines.append(text)

            continue


        # Add food to the currently active choice
        if food_name:

            if current_choice is not None:
                if food_name not in choices[current_choice]:
                    choices[current_choice].append(food_name)

            all_menu_lines.append(food_name)

        elif text:
            # Things like "with", "or", etc.
            all_menu_lines.append(text)


    # -----------------------------------------------------
    # Determine the main choices.
    #
    # We use the FIRST food listed under each Choice.
    #
    # Example:
    #
    # Choice 1
    #   Beef Taco Meat
    #   with
    #   Tostitos Scoops
    #   Nacho Cheese
    #
    # Choice 2
    #   LOCAL Lentil Sambusa
    #
    # becomes:
    #
    # Choice 1: Beef Taco Meat
    # Choice 2: LOCAL Lentil Sambusa
    # -----------------------------------------------------

    choice_1 = choices.get(1, [])
    choice_2 = choices.get(2, [])
    choice_3 = choices.get(3, [])


    summary_parts = []


    if choice_1:
        summary_parts.append(
            f"Choice 1: {choice_1[0]}"
        )

    if choice_2:
        summary_parts.append(
            f"Choice 2: {choice_2[0]}"
        )

    # We intentionally don't put Choice 3 in the calendar
    # title because that is usually the deli/sandwich option.


    # -----------------------------------------------------
    # Fallback
    #
    # If Nutrislice doesn't provide Choice headings on a
    # particular day, use the older entrée-detection method.
    # -----------------------------------------------------

    if not summary_parts:

        food_items = []

        for item in menu_items:

            name = get_food_name(item)

            if name and name not in food_items:
                food_items.append(name)


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

            return any(
                word in lower
                for word in excluded_words
            )


        entrees = [
            item
            for item in food_items
            if not is_side_or_drink(item)
        ]


        if len(entrees) >= 2:

            summary_parts = [
                f"Choice 1: {entrees[0]}",
                f"Choice 2: {entrees[1]}"
            ]

        elif len(entrees) == 1:

            summary_parts = [
                f"Choice 1: {entrees[0]}"
            ]

        elif food_items:

            summary_parts = [
                food_items[0]
            ]


    # -----------------------------------------------------
    # Calendar title
    # -----------------------------------------------------

    if summary_parts:
        summary = " | ".join(summary_parts)
    else:
        summary = "Otter Lake School Lunch"


    # -----------------------------------------------------
    # Calendar description
    #
    # Keep the complete menu available when the event is
    # opened.
    # -----------------------------------------------------

    description_lines = [
        "Otter Lake School Lunch",
        ""
    ]

    if choice_1:
        description_lines.append(
            "Choice 1: " + " | ".join(choice_1)
        )

    if choice_2:
        description_lines.append(
            "Choice 2: " + " | ".join(choice_2)
        )

    if choice_3:
        description_lines.append(
            "Choice 3: " + " | ".join(choice_3)
        )


    # If there weren't Choice sections, show the full menu
    if not choice_1 and not choice_2 and not choice_3:

        description_lines.append("Full menu:")

        for line in all_menu_lines:

            if line:
                description_lines.append(
                    "• " + line
                )


    description = "\\n".join(description_lines)


    # -----------------------------------------------------
    # Create all-day calendar event
    # -----------------------------------------------------

    date_obj = datetime.strptime(
        date_string,
        "%Y-%m-%d"
    ).date()

    next_date = date_obj + timedelta(days=1)


    events.append(
        f"""BEGIN:VEVENT
DTSTART;VALUE=DATE:{date_obj.strftime("%Y%m%d")}
DTEND;VALUE=DATE:{next_date.strftime("%Y%m%d")}
SUMMARY:{escape_ics(summary)}
DESCRIPTION:{escape_ics(description)}
UID:{date_string}-otter-lake-lunch@github
END:VEVENT"""
    )


# ---------------------------------------------------------
# Create ICS calendar
# ---------------------------------------------------------

ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Otter Lake School Lunch//Nutrislice//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Otter Lake School Lunch
X-WR-TIMEZONE:America/Chicago
""" + "\n".join(events) + "\nEND:VCALENDAR\n"


with open(
    "school-lunch.ics",
    "w",
    encoding="utf-8"
) as f:

    f.write(ics)


print(
    f"Created calendar with {len(events)} lunch days."
)