import stat
import os
import shutil
import re
import csv
import random
import time
from slack_sdk.errors import SlackApiError
import config
from config import public_channel_id, upload_directory, sleep_time, delete_old_message, log_file, instrument_data, image_urls, slack_buttons, private_channel_id

## Pause before repeating an action
def wait_before_retry(sleep_time=45):
    logger.debug(f"Waiting for {sleep_time} seconds before retrying...")
    time.sleep(sleep_time)

## Retrieves the update from the instrument-generated report file
def parse_report_file(report_path):
    instrument, state, method, method_start_time, user = ["Unknown"] * 5
    try:
        with open(report_path, 'r', newline='') as file:
            reader = csv.reader(file)
            next(reader)
            row = next(reader, None)
            if row is None:
                logger.error("CSV file is empty after the header.")
            elif len(row) == 5:
                instrument, state, method, method_start_time, user = row
            elif len(row) == 4:
                instrument, state, method, method_start_time = row
            elif len(row) == 3:
                instrument, state, method = row
            else:
                logger.error("Unexpected number of values in the CSV file.")
    except FileNotFoundError:
        logger.error(f"File not found: {report_path}")
    except Exception as e:
        logger.error(f"Error occurred while parsing the report: {e}")
    return instrument, state, method, method_start_time, user

## Attempts to delete a message in a given Slack channel. Retries if deletion fails.
def delete_or_update_message(channel_id, message_ts, retries=3, delay=2):
    """
    Args:
        channel_id (str): The ID of the Slack channel.
        message_ts (str): The timestamp of the Slack message to delete.
        retries (int): Number of times to retry if an error occurs (default: 3).
        delay (int): Delay in seconds between retries (default: 2 seconds).
    """
    for attempt in range(retries):
        try:
            slack_client.chat_delete(channel=channel_id, ts=message_ts)
            logger.info(f"Successfully deleted message with ts {message_ts} in channel {channel_id}.")
            return True  # Exit if successful
        except SlackApiError as delete_error:
            error_code = delete_error.response.get("error", "unknown_error")
            if error_code == "cant_delete_message":
                logger.error(f"Cannot delete message (ts: {message_ts}) due to permission issues.")
                return False  # Exit without retrying since it's a permission issue
            else:
                logger.error(f"cannot delete message due to SlackAPIError: {error_code}")
        except Exception as e:
            logger.error(f"Unexpected error occurred while deleting message (ts: {message_ts}): {e}")
        
        # Wait before retrying
        if attempt < retries - 1:
            time.sleep(delay)

    logger.error(f"Failed to delete message with ts {message_ts} after {retries} attempts.")
    return False

def create_slack_payload(instrument, state, method, time):
    # Prepare markdown texts
    instrument_info = instrument_data.get(instrument, instrument_data["Unknown"])
    mrkdwn_texts = [
        {"type": "mrkdwn", "text": f"*Instrument:*\n_{instrument_info['name']}_"},
        {"type": "mrkdwn", "text": f"*Status:*\n_{state}_"},
        {"type": "mrkdwn", "text": f"*Method:*\n_{method}_"},
        {"type": "mrkdwn", "text": f"*When:*\n_{time}_"}]

    # Select a random image and buttons based on state
    header = {'type': 'plain_text', 'text': f"Status Update {instrument_info['emoji']}", 'emoji': True}
    image = random.choice(list(image_urls.get(state.lower(), image_urls["other"]).values()))
    slack_button1 = random.choice(list(slack_buttons["positive"].values()))
    slack_button2 = random.choice(list(slack_buttons["negative"].values()))

    # Create the full Slack message
    return config.create_slack_message(header, image, slack_button1, slack_button2, None, mrkdwn_texts)

## >>>>>>>>>> Connect to Slack <<<<<<<<<<
slack_app, slack_client, logger = config.initalise_slack_app()
every_message = []
while True:
    # Check if directory is accessible
    if not os.path.isdir(upload_directory):
        logger.error(f"Cannot access the upload directory: {upload_directory}")
        wait_before_retry()
        continue

    # Get update file path
    files = [f for f in os.listdir(upload_directory) if f.endswith(".txt")]
    if not files:
        logger.info("No update file found.")
        wait_before_retry()
        continue
    
    # Parse the report file
    report_path = os.path.join(upload_directory, files[0])   
    instrument, state, method, method_start_time, user = parse_report_file(report_path)
    file_creation_time = os.path.getmtime(report_path)
    logger.info(f"instrument, state, method, method_start_time, file_creation_time: {instrument}, {state}, {method}, {method_start_time}, {file_creation_time}")
    if not instrument:
        logger.error("Problem parsing instrument report")
        broken_uploads_dir = os.path.join(os.path.dirname(os.path.dirname(upload_directory)), "Broken Uploads")
        os.makedirs(broken_uploads_dir, exist_ok=True)
        file_count = sum(1 for name in os.listdir(broken_uploads_dir) if os.path.isfile(os.path.join(broken_uploads_dir, name)))
        shutil.move(report_path, os.path.join(broken_uploads_dir, f"{file_count + 1}.txt"))
        continue

    # Fetch Slack messages (separate function if needed)
    more_messages = True
    cursor = None
    all_messages = []
    while more_messages:
        try:
            response = slack_client.conversations_history(channel=public_channel_id, cursor=cursor)
            all_messages.extend(response.get('messages', []))
            more_messages = response.get('has_more', False)
            cursor = response.get('response_metadata', {}).get('next_cursor', None)
        except SlackApiError as e:
            logger.error(f"Error fetching conversations: {e.response['error']}")
            break
        except Exception as e:
            logger.error(f"Unexpected error occurred: {e}")
            break

    # Process each Slack message
    for slack_message in all_messages:
        try:
            message_ts = slack_message.get('ts')

            # Skip processing if necessary
            if not message_ts or message_ts in every_message:
                continue

            blocks = slack_message.get("blocks", [])
            if len(blocks) <= 1:
                logger.info("Insufficient blocks in the Slack message")
                every_message.append(message_ts)
                continue

            # Extract the instrument section and check if it's valid
            block = blocks[1]
            fields = block.get("fields", [])
            if not fields or not isinstance(fields, list):
                logger.info("Invalid or missing fields in the second block")
                every_message.append(message_ts)
                continue

            slack_message_instrument_text = fields[0].get("text", "")
            match = re.search(r"_(.*?)_", slack_message_instrument_text)

            # If no match, skip processing
            if not match:
                every_message.append(message_ts)
                continue

            slack_message_instrument = match.group(1)
            instrument_SN = config.display_name_to_key.get(slack_message_instrument)
            logger.debug(f"Instrument SN: '{instrument_SN}',  Instrument Name: '{slack_message_instrument}'")
            if not instrument_SN:
                every_message.append(message_ts)
                continue

            # If conditions are met, delete or update the message
            try:
                if delete_old_message and instrument == instrument_SN:
                    response = delete_or_update_message(public_channel_id, message_ts)
                    every_message.append(message_ts)
                elif public_channel_id == private_channel_id:
                    response = delete_or_update_message(public_channel_id, message_ts)
                    every_message.append(message_ts)
            except Exception as e:
                logger.error(f"Error processing instrument information: {e}")
        except Exception as e:
            logger.error(f"Error processing Slack message {slack_message}: {e}")

    # Send Slack update and remove report
    try:
        if instrument:
            if state:
                if method:
                    file_creation_time_formatted = config.time_stamp(file_creation_time)
                    message = create_slack_payload(instrument, state, method, file_creation_time_formatted)
                    config.send_update_slack_message(message["blocks"], public_channel_id, "")
                    os.chmod(report_path, stat.S_IWRITE)
                    os.remove(report_path)
    except Exception as e:
        logger.error(f"Error when sending message to Slack: {e}")

    # Log update
    if instrument != "SN0000" or public_channel_id == private_channel_id:
        with open(log_file, mode='a+', newline='') as file:
            writer = csv.writer(file)
            file.seek(0)
            if file.read(1) == '':
                writer.writerow(['Instrument', 'Method', 'Start Time', 'End Time'])
            writer.writerow([instrument, method, method_start_time, file_creation_time])

    time.sleep(sleep_time)