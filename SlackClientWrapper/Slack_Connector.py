import re
import time

from Logging_Util import get_logger
from slack_sdk.web import WebClient
from slack_bolt import App
from slack_sdk.errors import SlackApiError

logger = get_logger("Slack Connection")


class SlackClientWrapper:
    """Thin wrapper around the Slack WebClient/App with built-in retry logic."""

    def __init__(self, bot_token, retries=3, delay=2):
        self.bot_token = bot_token
        self.retries = retries
        self.delay = delay
        self.client, self.app = self._connect()

    def _connect(self):
        """
        Establish connection to Slack workspace with retry logic.

        Returns:
            tuple: (WebClient instance, App instance)

        Raises:
            ConnectionError: If connection fails after all retries
        """
        last_exc = None
        for attempt in range(1, self.retries + 1):
            logger.info(f"Connecting to Slack (attempt {attempt}/{self.retries})")
            try:
                client = WebClient(token=self.bot_token)
                app = App(token=self.bot_token)
                auth = client.auth_test()
                logger.info(f"Connected to Slack workspace: {auth.get('team')}")
                return client, app
            except SlackApiError as e:
                logger.error(f"Slack API error: {e.response['error']}")
                last_exc = e
            except Exception as e:
                logger.error(f"Unexpected error during Slack connection: {e}")
                last_exc = e

            if attempt < self.retries:
                time.sleep(self.delay)

        raise ConnectionError("Unable to connect to Slack after retries") from last_exc

    def _func_with_retries(self, func, payload):
        """Call a Slack SDK function, retrying on failure. Returns None if all attempts fail."""
        for attempt in range(1, self.retries + 1):
            try:
                logger.info(f"Slack API call {func.__name__} (attempt {attempt}/{self.retries})")
                return func(**payload)
            except SlackApiError as e:
                code = e.response.get("error", "unknown_error")
                logger.error(f"Slack API error (attempt {attempt}/{self.retries}): {code}")
            except Exception as e:
                logger.error(f"Unexpected error during Slack API call: {e}")
            time.sleep(self.delay)

        logger.error(f"Slack API call {func.__name__} failed after all retries.")
        return None

    def _iter_channel_messages(self, channel):
        """
        Generator yielding every message in a channel's history, page by page,
        so pagination logic only lives in one place.
        """
        cursor = None
        while True:
            payload = {"channel": channel, "cursor": cursor}
            response = self._func_with_retries(self.client.conversations_history, payload)
            if not response:
                logger.error("Failed to fetch conversation history")
                return

            messages = response.get("messages", [])
            if not messages:
                return

            yield from messages

            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                return

    # --- Message operations ---

    def send_message(self, channel, text="Default message", blocks=None):
        """
        Send a message to a Slack channel or user.

        Args:
            channel (str): Channel ID (e.g., 'C1234567890') or user ID for DMs
            text (str): Message text (fallback for notifications)
            blocks (list, optional): Block Kit blocks for rich formatting

        Returns:
            str: Message timestamp if successful

        Raises:
            ConnectionError: If the message could not be sent after all retries

        Example:
            >>> ts = slack.send_message(
            ...     channel="C1234567890",
            ...     text="Hello!",
            ...     blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "*Hello!*"}}]
            ... )
        """
        payload = {"channel": channel, "text": text or " "}
        if blocks is not None:
            payload["blocks"] = blocks

        response = self._func_with_retries(self.client.chat_postMessage, payload)
        if not response:
            raise ConnectionError("Unable to send message to Slack after retries")

        ts = response.get("ts") or response.get("message", {}).get("ts")
        logger.debug(f"Slack message sent to {channel} (ts={ts})")
        return ts

    def upload_image(self, channel, file_path, title=None, initial_comment=None, thread_ts=None):
        """
        Upload an image or file to a Slack channel.

        Args:
            channel (str): Channel ID or name to upload to
            file_path (str): Path to the file to upload
            title (str, optional): Title for the file
            initial_comment (str, optional): Comment to post with the file
            thread_ts (str, optional): Thread timestamp to upload to a specific thread

        Returns:
            str: File ID if successful, None otherwise

        Example:
            >>> file_id = slack.upload_image(
            ...     channel="C1234567890",
            ...     file_path="/path/to/screenshot.png",
            ...     title="Dashboard Screenshot",
            ...     initial_comment="Q4 metrics looking good!"
            ... )
        """
        with open(file_path, "rb") as file_content:
            payload = {
                "channels": channel,
                "file": file_content,
                "filename": file_path.split("/")[-1],
            }
            if title:
                payload["title"] = title
            if initial_comment:
                payload["initial_comment"] = initial_comment
            if thread_ts:
                payload["thread_ts"] = thread_ts

            response = self._func_with_retries(self.client.files_upload_v2, payload)

        if not response:
            return None

        file_id = response.get("file", {}).get("id")
        logger.debug(f"File uploaded to {channel} (file_id={file_id})")
        return file_id

    def update_message(self, message_ts, channel, text="Default message", blocks=None):
        """
        Update an existing Slack message.

        Args:
            message_ts (str): Timestamp of the message to update
            channel (str): Channel ID containing the message
            text (str): New message text
            blocks (list, optional): New Block Kit blocks

        Returns:
            Response object if successful, None if failed

        Example:
            >>> slack.update_message(
            ...     message_ts="1234567890.123456",
            ...     channel="C1234567890",
            ...     text="Updated message!"
            ... )
        """
        payload = {"channel": channel, "ts": message_ts, "text": text or " "}
        if blocks is not None:
            payload["blocks"] = blocks

        response = self._func_with_retries(self.client.chat_update, payload)
        if response:
            logger.debug(f"Slack message updated (ts={message_ts})")
        return response

    def _delete_message(self, channel, ts, delay):
        """Delete a single message and pause briefly afterward. Returns True on success."""
        response = self._func_with_retries(self.client.chat_delete, {"channel": channel, "ts": ts})
        if response:
            logger.debug(f"Slack message deleted (ts={ts})")
            time.sleep(delay)
            return True
        return False

    def delete_all_messages(self, channel, delay=0.1):
        """
        Delete all messages from a Slack channel.

        WARNING: This operation cannot be undone. Use with caution.

        Args:
            channel (str): Channel ID to delete messages from
            delay (float): Delay in seconds between delete operations (default: 0.1)

        Returns:
            int: Total number of messages deleted

        Example:
            >>> deleted = slack.delete_all_messages(channel="C1234567890")
            >>> print(f"Deleted {deleted} messages")
        """
        total_deleted = 0
        for msg in self._iter_channel_messages(channel):
            ts = msg.get("ts")
            if ts and self._delete_message(channel, ts, delay):
                total_deleted += 1

        logger.info(f"Finished deleting messages. Total deleted: {total_deleted}")
        return total_deleted

    def delete_specific_messages(self, match_text, channel, delay=0.1):
        """
        Delete messages whose second block's first field contains an underscore-wrapped
        value (e.g. "_ABC123_") matching match_text.

        Args:
            match_text (str): Value to match against the underscore-wrapped field text
            channel (str): Channel ID to search and delete from
            delay (float): Delay in seconds between delete operations (default: 0.1)

        Returns:
            int: Total number of messages deleted
        """
        pattern = re.compile(r"_(.*?)_")
        total_deleted = 0

        for msg in self._iter_channel_messages(channel):
            ts = msg.get("ts")
            blocks = msg.get("blocks")
            if not ts or not isinstance(blocks, list) or len(blocks) < 2:
                continue

            fields = blocks[1].get("fields")
            if not isinstance(fields, list) or not fields:
                continue

            match = pattern.search(fields[0].get("text", ""))
            if not match or match.group(1) != match_text:
                continue

            if self._delete_message(channel, ts, delay):
                total_deleted += 1
                logger.info(f"Deleted Slack message ts={ts}")

        logger.info(f"Finished deleting messages. Total deleted: {total_deleted}")
        return total_deleted