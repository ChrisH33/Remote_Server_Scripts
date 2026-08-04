## >>>>>>>>>> Dictionaries containing Slack message options <<<<<<<<<<
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

## >>>>>>>>>> Variables <<<<<<<<<<
import platform
import os
import logging
update_frequency = 15
sleep_time = 6
delete_old_message = True

## >>>>>>>>>> Define folder locations based on environment <<<<<<<<<<

if platform.system() == "Linux":
    # Script is running in a production environment
    directory_prefix = "/mnt/dna_pipelines"
    directory_suffix = "/Upload"
else:
    # Script is running in a development/testing environment
    public_channel_id = private_channel_id
    directory_suffix = "/Scripts"
    directory_prefix = "W:"
upload_directory = f"{directory_prefix}{instrument_upload_directory}{directory_suffix}"
log_file = f"{directory_prefix}{log_file_path}"

# Start the logging trace
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')     # NOTSET, DEBUG, INFO, WARNING, ERROR, Critical
logger = logging.getLogger(__name__)

## >>>>>>>>>> Functions <<<<<<<<<<

## Function to create a standard time stamp
def time_stamp(unix_timestamp):
    from datetime import datetime
    if unix_timestamp:
        dt = datetime.fromtimestamp(unix_timestamp)
    else:
        dt = datetime.now()
    suffix = "th" if 11 <= dt.day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(dt.day % 10, "th")
    formatted_time = f"{dt.strftime('%H:%M')}, {dt.day}{suffix} {dt.strftime('%b')}"
    logger.debug("Generated timestamp: {formatted_time}")
    return formatted_time

# Function to create the slack_app & slack_client
def initalise_slack_app():
    global slack_bot_token
    import sys
    from slack_bolt import App
    from slack_sdk.web import WebClient

    # Start the bolt app
    try:
        if slack_bot_token is None:
            logger.error("slack_bot_token (xoxb) is not set")
            sys.exit(1)
        slack_client = WebClient(token=slack_bot_token)
        slack_app = App(token=slack_bot_token)
        logger.debug("Bolt app initialised successfully")
        return slack_app, slack_client, logger
    except Exception as e:
        logger.error(f"Error initialising Bolt app: {str(e)}")
        sys.exit(1)

## Function to message Slack or update a Slack message
def send_update_slack_message(message_payload, channel, message_ts=None):
    import time
    from slack_sdk.errors import SlackApiError

    # Initialize Slack app and loggers
    slack_app, slack_client, logger = initalise_slack_app()

    # Log the start of the operation
    logger.info(f"Sending message to {channel} with timestamp: {message_ts}")

    #Loop to handle retries
    while True:
        try:
            if not message_ts:    # If message_ts is None, send a new message
                response = slack_client.chat_postMessage(channel=channel, text=("Default message"), blocks=message_payload)
                return response['message']['ts']
            else:
                slack_client.chat_update(channel=channel, ts=message_ts, text=("Default message"), blocks=message_payload)
                break
        except SlackApiError as e:
            error_code = e.response['error']
            logger.error(f"Slack API Error: {error_code}")
            
            if error_code == 'rate_limited':
                time.sleep(20)  # Adjust based on API's retry-after headers if possible
            else:
                time.sleep(10)  # Retry for other errors
        except Exception as e:
            logger.error(f"Failed to update message on Slack: {e}")
            time.sleep(10)
  
# Create a pre-formatted slack message
def create_slack_message(header, image, slack_button1, slack_button2, update, mrkdwn_texts):
    global monday_feedback_URL
    message = {"blocks": []}
    section_block = {"type": "section", "fields": []}
    actions_block = {"type": "actions", "elements": []}

    if header:
        header_msg = {"type": "header","text": header}
        message["blocks"].append(header_msg)
    
    if mrkdwn_texts or image:
        if image:
            section_block["accessory"] = {"type": "image","image_url": image,"alt_text": "UseFeedbackToSuggestOther.gif"}
        for item in mrkdwn_texts:
            if isinstance(item, dict) and item.get("type") == "mrkdwn" and "text" in item:
                section_block["fields"].append({"type": "mrkdwn", "text": item["text"]})
        message["blocks"].append(section_block)
   
    if slack_button1 or slack_button2:
        actions_block["elements"].append({
            "type": "button",
            "text": {"type": "plain_text","emoji": True,"text": slack_button1},
            "style": "primary","action_id": "Button1",})
        actions_block["elements"].append({
            "type": "button",
            "text": {"type": "plain_text","emoji": True,"text": slack_button2},
            "style": "danger", "action_id": "Button2",})
        actions_block["elements"].append({
            "type": "button",
            "text": {"type": "plain_text","emoji": True,"text": "Feedback"},
            "url": monday_feedback_URL,"action_id": "Button3",})
        message["blocks"].append(actions_block)

    if update:
        message["blocks"].append(update)

    message["blocks"].append({"type": "divider"})
    return message

## necessary for the slack_payloads
def body_details(body):
    try:
        blocks = body["message"]["blocks"]
        header = blocks[0]["text"]
        fields = blocks[1]["fields"]
        elements = blocks[2]["elements"]
        return (
            header, 
            fields[0]["text"],                                          # instrument
            fields[1]["text"],                                          # state
            fields[2]["text"],                                          # method
            fields[3]["text"],                                          # time
            body["message"]["blocks"][1]["accessory"]["image_url"],     # image
            body["user"]["name"],                                       # username
            elements[0]["text"]["text"],                                # slack_button1
            elements[1]["text"]["text"],                                # slack_button2
        )
    except KeyError as e:
        logger.error(f"Error: Missing key in body: {e}")
        return None