from datetime import datetime
import json

# -------------------------------------------------
# Message Elements
# -------------------------------------------------
slack_buttons = {
    "positive": {
        1: "Okay :thumbsup:",
        2: "Thank you",
        3: "Thanks",
        4: "Great",
        5: "On my way",
        6: "Awesome :sunglasses:"
    },
    "negative": {
        1: "Can't right now  :thumbsdown:",
        2: "Sorry, busy",
        3: "Not me",
        4: "Currently busy",
        5: ":help:",
        6: ":sad:"
    }}

image_urls = {
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
    5: "https://static.guim.co.uk/sys-images/Guardian/Pix/pictures/2012/10/9/1349799315514/borisdave.gif"
    }}

responses = {
    "positive": {
    1: "is on it",
    2: "will handle it",
    3: "is handling it",
    4: "is dealing with it",
    5: "is taking care of it",
    6: "is working on it",
    7: "has it covered",
    8: "is managing it",
    9: "is on top of it",
    10: "is sorting it out",
    11: "is on the case",
    12: "is handling the situation",
    13: "is attending to it"
    }}

# -------------------------------------------------
# Instrument Information
# -------------------------------------------------

instrument_data = {
    "SN297B": {"name": "Peppa", "emoji": ":hamilton_star:"},
    "SN613B": {"name": "Babe", "emoji": ":hamilton_star:"},
    "SN495D": {"name": "Percy", "emoji": ":hamilton_star:"},
    "SN261B": {"name": "Hamlet", "emoji": ":hamilton_star:"},
    "SN7722": {"name": "Napoleon", "emoji": ":hamilton_star:"},
    "SN7721": {"name": "Porkins", "emoji": ":hamilton_star:"},
    "SN830H": {"name": "RSF STARlet", "emoji": ":hamilton_star:"},
    "SN0000": {"name": "Sim mode", "emoji": ":idontknow:"},
    "Unknown": {"name": "Unknown", "emoji": ":sos:"},
    }

display_name_to_key = {
    "Peppa": "SN297B",
    "Babe": "SN613B",
    "Percy": "SN495D",
    "Hamlet": "SN261B",
    "Napoleon": "SN7722",
    "Porkins": "SN7721",
    "RSF STARlet": "830H",
    "Sim mode": "SN0000",
    "Unknown": "Unknown",
}

Method_key = {
}

# -------------------------------------------------
# Helpers
# -------------------------------------------------

def time_format(time):
    if isinstance(time, str):
        dt = datetime.fromisoformat(time)
    elif time:
        dt = datetime.fromtimestamp(time)
    else:
        dt = datetime.now()
    
    suffix = "th" if 11 <= dt.day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(dt.day % 10, "th")
    formatted_time = f"{dt.strftime('%H:%M')}, {dt.day}{suffix} {dt.strftime('%b')}"
    return formatted_time

# -------------------------------------------------
# Standardised Message Structure
# -------------------------------------------------

def create_slack_message(**comp):
    message = {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"Instrument Status Update {comp.get('header')}", "emoji": True}
            },
            {"type": "divider"},
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn","text": f"*Instrument:*\n_{comp.get('instrument')}_"},
                    {"type": "mrkdwn","text": f"*Status:*\n_{comp.get('status')}_"},
                    {"type": "mrkdwn","text": f"*Method:*\n_{comp.get('method')}_"},
                    {"type": "mrkdwn","text": f"*When:*\n_{comp.get('time')}_"}
                ],
                "accessory": {
                    "type": "image",
                    "image_url": f"{comp.get('image')}",
                    "alt_text": "Funny gif, i don't know"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text","text": f"{comp.get('button_1')}","emoji": True},
                        "style": "primary",
                        "action_id": "buttonPrimary"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text","text": f"{comp.get('button_2')}","emoji": True},
                        "style": "danger",
                        "action_id": "buttonSecondary"
                    },
                    {
                        "type": "button",
                        "action_id": "buttonTertiary",
                        "text": {"type": "plain_text","text": "Feedback","emoji": True}
                    }
                ]
            }
        ]
    }
    message_json = json.dumps(message, ensure_ascii=False)
    return message_json