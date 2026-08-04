"""
SendToSlack.py
--------------
Sends desk allocation data to Slack.
"""

from utils.config import logger

def send_desk_allocations(slack_wrapper,file_path:str, channel_id: str) -> str:
    """
    Send desk allocations to Slack.

    Args:
        slack_wrapper: SlackClientWrapper instance
        channel_id: Slack channel ID to send to
        allocations: List of allocation dicts
        summary_only: If True, send compact summary instead of full details

    Returns:
        Message timestamp if successful, None if failed
    """

    comment = "hey look at me"

    try:
        ts = slack_wrapper.upload_image(
            channel=channel_id,
            file_path =file_path,
            title ="Desk Allocations Update",
            initial_comment=comment,
        )

        if ts:
            logger.info(f"Desk allocations sent to Slack (ts={ts})")
        else:
            logger.error("Failed to send desk allocations to Slack")

        return ts

    except Exception as e:
        logger.error(f"Error sending desk allocations to Slack: {e}")
        return None