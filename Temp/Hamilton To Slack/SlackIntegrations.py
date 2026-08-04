import random
from datetime import datetime
import config
from config import slack_app_token
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Initialize the Slack app
slack_app, slack_client, logger = config.initalise_slack_app()

## Function to find user information
def retrieve_user_info(user_id):
    try:
        user_info = slack_client.users_info(user=user_id)
        if user_info["ok"]:
            return user_info["user"]
        else:
            logger.error("Could not identify user")
            return None
    except Exception as e:
        logger.error(f"Failed to retrieve user information: {e}")
        return None

## Function to create slack payload
def handle_button_action(action_id, body, user_info):
    timestamp = datetime.now().strftime('%H:%M')  # Fixed to a string instead of a set
    
    ## Button1 Pressed
    if action_id == "Button1":
        response = random.choice(list(config.responses['positive'].values()))  # Correct response format
        users_slack_name = user_info["enterprise_user"]["id"]
        update = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"({timestamp}) *<@{users_slack_name}>* {response}"}}
        header, instrument, state, *_ = config.body_details(body)
        mrkdwn_texts = [
            {"type": "mrkdwn", "text": f"{instrument}"},
            {"type": "mrkdwn", "text": f"{state}"}]
        return config.create_slack_message(header, None, None, None, update, mrkdwn_texts)
    
    ## Button2 Pressed
    elif action_id == "Button2":
        header, instrument, state, method, time, image, _, slack_button1, slack_button2 = config.body_details(body)
        mrkdwn_texts = [
            {"type": "mrkdwn", "text": f"{instrument}"},
            {"type": "mrkdwn", "text": f"{state}"},
            {"type": "mrkdwn", "text": f"{method}"},
            {"type": "mrkdwn", "text": f"{time}"}]
        base_message = config.create_slack_message(header, image, slack_button1, slack_button2, None, mrkdwn_texts)
        
        ## Handle if the button has already been pressed by this user
        context_block = next((block for block in body["message"]["blocks"] if block.get("type") == "context"), None)
        if context_block:
            username = user_info["profile"]["first_name"]
            user_present = any(
                element.get("type") == "image" and username in element.get("alt_text", "")
                for element in context_block.get("elements", []))
        else:
            user_present = False
        
        if not context_block:
            profile_picture_url = user_info["profile"]["image_24"]
            username = user_info["profile"]["first_name"]
            base_message["blocks"].extend([
                {"type": "context", "elements": [
                    {"type": "image", "image_url": profile_picture_url, "alt_text": username},
                    {"type": "plain_text", "text": "1 person is unavailable"}]},
                {"type": "divider"}])
            return base_message
        elif not user_present:
            profile_picture_url = user_info["profile"]["image_24"]
            username = user_info["profile"]["first_name"]
            num_elements = len(context_block["elements"])
            context_block["elements"][-1]["text"] = f"{num_elements} people are unavailable"
            if num_elements < 10:
                context_block["elements"].insert(0, {
                    "type": "image",
                    "image_url": profile_picture_url,
                    "alt_text": username})
            base_message["blocks"].append(context_block)
            base_message["blocks"].append({"type": "divider"})
            return base_message

    return None  # One return for cases where no message is generated

# Define action event listener
@slack_app.action("Button1")
@slack_app.action("Button2")
@slack_app.action("Button3")
def handle_button_click(ack, body):
    # Acknowledge the message from Slack
    try:
        ack()
    except Exception as e:
        logger.error(f"Failed to acknowledge message from Slack: {e}")
        return  # Early exit if acknowledgment fails

    # Get message details
    user_id = body["user"]["id"]
    channel_id = body.get("channel", {}).get("id", body["container"]["channel_id"])
    message_ts = body.get("message", {}).get("ts", body["container"]["message_ts"])

    # Retrieve user info
    user_info = retrieve_user_info(user_id)
    if not user_info:
        return  # Early exit if user info cannot be retrieved

    # Handle button actions
    action_id = body["actions"][0]["action_id"]
    message = handle_button_action(action_id, body, user_info)

    # Send update to Slack if a message was created
    if message:
        config.send_update_slack_message(message["blocks"], channel_id, message_ts)
    else:
        logger.info(f"No update needed for action: {action_id}")

# Run the SocketMode Handler
SocketModeHandler(slack_app, slack_app_token).start()
