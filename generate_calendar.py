import json
import urllib.request
from datetime import datetime, timedelta
import re


DISTRICT = "isd624"
SCHOOL = "otter-lake"
MENU_TYPE = "lunch"


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def get_week_menu(monday):
    """
    Download one week's menu from Nutrislice.
    """

    url = (
        f"https://{DISTRICT}.api.nutrislice.com/menu/api/weeks/"
        f"school/{SCHOOL}/menu-type/{MENU_TYPE}/"
        f"{monday.year}/{monday.month:02d}/{monday.day:02d}/"
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Otter-Lake-Lunch-Calendar/1.0"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=20
    ) as response:

        return json.loads(
            response.read().decode("utf-8")
        )


def get_food_name(item):
    food = item.get("food")

    if food and food.get("name"):
        return food["name"].strip()

    return None


def escape_ics(text):
    """
    Escape characters required by iCalendar.
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
    Detect Nutrislice section headings such as:

    Choice 1
    Choice 2
    Choice 3
    """

    text = (item.get("text") or "").strip()

    return (
        bool(
            re.match(
                r"^choice\s+\d+$",
                text,
                re.IGNORECASE
            )
        )
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
# Get current week AND next week
# ---------------------------------------------------------

today = datetime.now().date()

current_monday = (
    today -
    timedelta(days=today.weekday())
)

next_monday = (
    current_monday +
    timedelta(days=7)
)


print(
    f"Fetching week of {current_monday}..."
)

current_week = get_week_menu(current_monday)


print(
    f"Fetching week of {next_monday}..."
)

next_week = get_week_menu(next_monday)


# Combine both weeks
all_weeks = [
    current_week,
    next_week
]


# ---------------------------------------------------------
# Build calendar events
# ---------------------------------------------------------

events = []


for week_data in all_weeks:

    for day in week_data.get("days", []):

        date_string = day.get("date")

        if not date_string:
            continue


        menu_items = day.get("menu_items", [])


        # -------------------------------------------------
        # Organize items according to Choice headings
        # -------------------------------------------------

        choices = {}

        current_choice = None

        all_menu_lines = []


        for item in menu_items:

            text = (
                item.get("text") or ""
            ).strip()

            food_name = get_food_name(item)


            # ---------------------------------------------
            # Choice heading
            # ---------------------------------------------

            if is_choice_heading(item):

                current_choice = (
                    get_choice_number(text)
                )

                if current_choice is not None:

                    choices.setdefault(
                        current_choice,
                        []
                    )

                    all_menu_lines.append(
                        text
                    )

                continue


            # ---------------------------------------------
            # Food item
            # ---------------------------------------------

            if food_name:

                if current_choice is not None:

                    if food_name not in choices[
                        current_choice
                    ]:

                        choices[
                            current_choice
                        ].append(
                            food_name
                        )

                all_menu_lines.append(
                    food_name
                )


            # ---------------------------------------------
            # Other text such as:
            #
            # with
            # or
            # ---------------------------------------------

            elif text:

                all_menu_lines.append(
                    text
                )


        # -------------------------------------------------
        # Get actual choices
        # -------------------------------------------------

        choice_1 = choices.get(1, [])
        choice_2 = choices.get(2, [])
        choice_3 = choices.get(3, [])


        # -------------------------------------------------
        # Build calendar title
        # -------------------------------------------------

        summary_parts = []


        if choice_1:

            summary_parts.append(
                f"Choice 1: {choice_1[0]}"
            )


        if choice_2:

            summary_parts.append(
                f"Choice 2: {choice_2[0]}"
            )


        # -------------------------------------------------
        # Fallback if Nutrislice doesn't provide
        # Choice headings for a particular day
        # -------------------------------------------------

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


        # -------------------------------------------------
        # Calendar title
        # -------------------------------------------------

        if summary_parts:

            summary = " | ".join(
                summary_parts
            )

        else:

            summary = (
                "Otter Lake School Lunch"
            )


        # -------------------------------------------------
        # Event description
        # -------------------------------------------------

        description_lines = [
            "Otter Lake School Lunch",
            ""
        ]


        if choice_1:

            description_lines.append(
                "Choice 1: " +
                " | ".join(choice_1)
            )


        if choice_2:

            description_lines.append(
                "Choice 2: " +
                " | ".join(choice_2)
            )


        if choice_3:

            description_lines.append(
                "Choice 3: " +
                " | ".join(choice_3)
            )


        # Add full menu if no Choice sections exist
        if (
            not choice_1
            and not choice_2
            and not choice_3
        ):

            description_lines.append(
                "Full menu:"
            )

            for line in all_menu_lines:

                if line:

                    description_lines.append(
                        "• " + line
                    )


        description = "\\n".join(
            description_lines
        )


        # -------------------------------------------------
        # Create all-day event
        # -------------------------------------------------

        date_obj = datetime.strptime(
            date_string,
            "%Y-%m-%d"
        ).date()


        next_date = (
            date_obj +
            timedelta(days=1)
        )


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
# Sort events chronologically
# ---------------------------------------------------------

events.sort()


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


# ---------------------------------------------------------
# Write calendar file
# ---------------------------------------------------------

with open(
    "school-lunch.ics",
    "w",
    encoding="utf-8"
) as f:

    f.write(ics)


print(
    f"Created calendar with {len(events)} lunch days."
)

print(
    "Calendar includes the current week and next week."
)