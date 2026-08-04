import time
import psutil
import InstrumentToSlack.config as config
from collections import defaultdict
from InstrumentToSlack.config import private_channel_id, update_frequency

known_scripts = defaultdict(dict)

## Function to get active Python scripts
def get_active_python_scripts():
    active_scripts = {}
    for process in psutil.process_iter(['pid', 'name', 'cmdline']):
        if process.info['name'] in ['python', 'python3'] and len(process.info['cmdline']) > 1:
            script_name = process.info['cmdline'][1]
            active_scripts[script_name] = process.info['pid']
    return active_scripts

slack_app, slack_client, logger = config.initalise_slack_app()
payload = [{'type': 'divider'}]
private_message_ts = config.send_update_slack_message(payload, private_channel_id, "")

while True:
    update_blocks_text = ""  # Reset Slack message text
    active_python_scripts = get_active_python_scripts()  # Get currently active Python scripts
    
    # Process active scripts
    for script, pid in active_python_scripts.items():
        if script not in known_scripts or known_scripts[script]['pid'] != pid:
            known_scripts[script] = {'pid': pid, 'state': 'Live', 'alerted': False}
        if known_scripts[script]['state'] != 'Live':
            known_scripts[script]['state'] = 'Live'
            known_scripts[script]['alerted'] = False
        update_blocks_text += f"{script}: *Live* (PID: {pid})\n"

    # Process offline scripts
    for script in list(known_scripts.keys()):
        if script not in active_python_scripts:
            if known_scripts[script]['state'] != 'Offline':
                known_scripts[script]['state'] = 'Offline'
                if not known_scripts[script]['alerted']:
                    try:
                        config.send_update_slack_message(
                            {"blocks": [{
                                "type": "header",
                                "text": {"type": "plain_text", "text": f"Alert: {script} stopped", "emoji": True}
                            }]},
                            private_channel_id,
                            slack_client)
                        known_scripts[script]['alerted'] = True
                    except Exception as e:
                        logger.error(f"Failed to send Slack alert for {script}: {e}")
            update_blocks_text += f"{script}: *Offline*\n"

    if update_blocks_text == "":
        update_blocks_text = "temp"
    slack_message = {"blocks": [
    {
        'type': 'header',
        'text': {
            'type': 'plain_text',
            'text': 'Python Script Watcher',
            'emoji': True
        }
    },
    {
        'type': 'section',
        'text': {
            'type': 'mrkdwn',
            'text': f"{update_blocks_text}"
        }
    },
    {
        'type': 'context',
        'elements': [
            {
                'type': 'mrkdwn',
                'text': f"date of last update: {config.time_stamp(None)}"
            }
        ]
    },
    {
        'type': 'divider'
    }]}


    try:
        config.send_update_slack_message(slack_message['blocks'], private_channel_id, private_message_ts)
    except Exception as e:
        logger.error(f"Failed to send Slack update: {e}")
    time.sleep(update_frequency)  # Sleep before the next check
