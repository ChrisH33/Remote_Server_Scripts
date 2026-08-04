"""
message_builder.py
------------------
Static data tables and Slack Block Kit builder for instrument-state messages.

Provides:
  - Image URL pools keyed by instrument state
  - Randomised button label pools
  - Instrument serial-number → display-name mapping
  - create_slack_message()  — returns a Block Kit blocks list (not JSON)
  - get_random_choice()     — picks a random value from a nested dict
  - time_format()           — formats an ISO timestamp for display
"""

# std modules
import random
from datetime import datetime


# ---------------------------------------------------------------------------
# Image pools  (keyed by lowercase state string)
# ---------------------------------------------------------------------------

image_urls: dict[str, dict[int, str]] = {
    "completed": {
        1: "https://i.pinimg.com/originals/12/85/f9/1285f940365ae756e7ad8627511ff82c.gif",
        2: "https://projectpokemon.org/home/uploads/monthly_2018_05/large.5aeb1fd71ff3d_DittoDancing.gif.08cc659ac16780c7a07d44534a019d22.gif",
        3: "https://media.tenor.com/V014gNOZgYwAAAAM/toothless-dance-discord-toothless.gif",
        4: "https://64.media.tumblr.com/b7ee86f13b9641872e7eab537a7a2660/tumblr_mwa2f73MpA1rtbl5vo1_400.gif",
        5: "https://i.pinimg.com/originals/bf/12/6b/bf126bd27294464c8f959056468dbb9f.gif",
        6: "https://i.imgur.com/xXDr5Rc.gif",
        7: "https://media.tenor.com/QHVKHujeWYcAAAAi/bread-dance.gif",
    },
    "aborted": {
        1: "https://i.pinimg.com/originals/4f/1c/9f/4f1c9f413d5337c24be62b3367f8db55.gif",
        2: "https://em-content.zobj.net/source/joypixels-animations/368/loudly-crying-face_1f62d.gif",
        3: "https://media.tenor.com/ttxeT_y_k1gAAAAj/mocha.gif",
        4: "https://images.squarespace-cdn.com/content/v1/57cc635d46c3c4013750884a/1538076124779-L7I7ME0639BQESR7DXHU/image-asset.gif",
    },
    "tip reload": {
        1: "https://www.easypdfcloud.com/Images/loading-256-0001.gif",
    },
    "scheduled user intervention": {
        1: "https://www.easypdfcloud.com/Images/loading-256-0001.gif",
    },
    "other": {
        1: "https://media.licdn.com/dms/image/D4D22AQHHY5BeyOoTVA/feedshare-shrink_2048_1536/0/1701626647287?e=2147483647&v=beta&t=PWVi9f5yjU7EqWGycVNzzWjYmH6GmGn50jPG56hBkjA",
        2: "https://i.pinimg.com/originals/65/61/9a/65619ac0003599587580de72e96d9441.gif",
        3: "https://media3.giphy.com/avatars/andy_goodstein/CL4cBPNM6eyJ.GIF",
        4: "https://uniformesgarys.com/WebRoot/Store/Shops/UniformesGarys/MediaGallery/Icons/vaya.gif",
        5: "https://static.guim.co.uk/sys-images/Guardian/Pix/pictures/2012/10/9/1349799315514/borisdave.gif",
    },
}

# ---------------------------------------------------------------------------
# Button label pools
# ---------------------------------------------------------------------------

slack_buttons: dict[str, dict[int, str]] = {
    "positive": {
        1: "Okay :thumbsup:",
        2: "Thank you",
        3: "Thanks",
        4: "Great",
        5: "On my way",
        6: "Awesome :sunglasses:",
    },
    "negative": {
        1: "Can't right now :thumbsdown:",
        2: "Sorry, busy",
        3: "Not me",
        4: "Currently busy",
        5: ":help:",
        6: ":sad:",
    },
}

# ---------------------------------------------------------------------------
# Acknowledgement response pool
# ---------------------------------------------------------------------------

responses: dict[str, dict[int, str]] = {
    "positive": {
        1:  "is on it",
        2:  "will handle it",
        3:  "is handling it",
        4:  "is dealing with it",
        5:  "is taking care of it",
        6:  "is working on it",
        7:  "has it covered",
        8:  "is managing it",
        9:  "is on top of it",
        10: "is sorting it out",
        11: "is on the case",
        12: "is handling the situation",
        13: "is attending to it",
    },
}

# ---------------------------------------------------------------------------
# Instrument data  (serial number → display name + emoji)
# ---------------------------------------------------------------------------

instrument_data: dict[str, dict[str, str]] = {
    "SN297B": {"name": "Peppa",       "emoji": ":hamilton_star:"},
    "SN613B": {"name": "Babe",        "emoji": ":hamilton_star:"},
    "SN495D": {"name": "Percy",       "emoji": ":hamilton_star:"},
    "SN261B": {"name": "Hamlet",      "emoji": ":hamilton_star:"},
    "SN7722": {"name": "Napoleon",    "emoji": ":hamilton_star:"},
    "SN7721": {"name": "Porkins",     "emoji": ":hamilton_star:"},
    "SN830H": {"name": "RSF STARlet", "emoji": ":hamilton_star:"},
    "SN0000": {"name": "Sim mode",    "emoji": ":hamilton_star:"},
    "Unknown": {"name": "Unknown",    "emoji": ":idontknow:"},
}

display_name_to_key: dict[str, str] = {
    "Peppa":       "SN297B",
    "Babe":        "SN613B",
    "Percy":       "SN495D",
    "Hamlet":      "SN261B",
    "Napoleon":    "SN7722",
    "Porkins":     "SN7721",
    "RSF STARlet": "SN830H",
    "Sim mode":    "SN0000",
    "Unknown":     "Unknown",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_random_choice(mapping: dict, key: str) -> str | None:
    """
    Return a random value from `mapping[key.lower()]`, or None if the key
    is missing or the inner dict is empty.
    """
    inner = mapping.get((key or "").strip().lower(), {})
    return random.choice(list(inner.values())) if inner else None


def time_format(time_value) -> str:
    """
    Format an ISO timestamp string or a Unix timestamp float into a
    human-readable string like "14:32, 3rd Apr".
    """
    if isinstance(time_value, str):
        dt = datetime.fromisoformat(time_value)
    elif time_value:
        dt = datetime.fromtimestamp(time_value)
    else:
        dt = datetime.now()

    suffix = (
        "th" if 11 <= dt.day <= 13
        else {1: "st", 2: "nd", 3: "rd"}.get(dt.day % 10, "th")
    )
    return f"{dt.strftime('%H:%M')}, {dt.day}{suffix} {dt.strftime('%b')}"


# ---------------------------------------------------------------------------
# Block builder
# ---------------------------------------------------------------------------

def create_slack_message(
    header:     str,
    instrument: str,
    status:     str,
    method:     str,
    when:       str,
    image:      str,
    button_1:   str,
    button_2:   str,
) -> list:
    """
    Build and return a Slack Block Kit blocks list for an instrument-state
    update.

    Returns a list (not a JSON string) ready to pass directly to
    SlackClientWrapper.send_message(blocks=...).
    """
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Instrument Status Update {header}",
                "emoji": True,
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Instrument:*\n_{instrument}_"},
                {"type": "mrkdwn", "text": f"*Status:*\n_{status}_"},
                {"type": "mrkdwn", "text": f"*Method:*\n_{method}_"},
                {"type": "mrkdwn", "text": f"*When:*\n_{when}_"},
            ],
            "accessory": {
                "type": "image",
                "image_url": image,
                "alt_text": "Status gif",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": button_1, "emoji": True},
                    "style": "primary",
                    "action_id": "buttonPrimary",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": button_2, "emoji": True},
                    "style": "danger",
                    "action_id": "buttonSecondary",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Feedback", "emoji": True},
                    "action_id": "buttonTertiary",
                },
            ],
        },
    ]
