import logging
import time
import re
from slack_sdk.web import WebClient
from slack_bolt import App
from slack_sdk.errors import SlackApiError

class SlackClientWrapper:
    """
    General-purpose Slack client wrapper for any project.
    
    Provides a robust interface for Slack operations with automatic retry logic,
    error handling, and logging. Supports message operations, file uploads, and
    message management.
    
    Attributes:
        bot_token (str): Slack bot token for authentication
        retries (int): Number of retry attempts for failed API calls
        delay (int): Delay in seconds between retry attempts
        logger (logging.Logger): Logger instance for tracking operations
        client (WebClient): Slack SDK WebClient instance
        app (App): Slack Bolt App instance
    
    Example:
        >>> slack = SlackClientWrapper(bot_token="xoxb-your-token")
        >>> slack.send_message(channel="C1234567890", text="Hello!")
        >>> slack.upload_image(channel="C1234567890", file_path="chart.png")
    """
    def __init__(self, bot_token=None, retries=3, delay=2, logger=None):
        self.bot_token = bot_token
        self.retries = retries
        self.delay = delay
        self.logger = logger or logging.getLogger(__name__)

        if not self.bot_token:
            raise ValueError("Slack token is missing")

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
            self.logger.debug(f"Connecting to Slack (attempt {attempt}/{self.retries})")
            try:
                client = WebClient(token=self.bot_token)
                app    = App(token=self.bot_token)
                auth   = client.auth_test()
                self.logger.info(f"Connected to Slack workspace: {auth.get('team')}")
                return client, app
            
            except SlackApiError as e:
                self.logger.error(f"Slack API error: {e.response['error']}")
                last_exc = e  
            except Exception as e:
                self.logger.error(f"Unexpected error during Slack connection: {e}")
                last_exc = e

            if attempt < self.retries:
                time.sleep(self.delay)
        raise ConnectionError("Unable to connect to Slack after retries") from last_exc

    def _func_with_retries(self, func, payload):
        """
        Execute a Slack API function with automatic retry logic.
        
        Args:
            func: Slack API function to execute
            payload (dict): Parameters to pass to the function
            
        Returns:
            API response object if successful, None if all retries failed
        """
        for attempt in range(1, self.retries + 1):
            try:
                self.logger.debug(f"Slack API call {func.__name__} (attempt {attempt}/{self.retries})")
                return func(**payload)
            
            except SlackApiError as e:
                code = e.response.get("error", "unknown_error")
                self.logger.error(f"Slack API Error (attempt {attempt}/{self.retries}): {code}")
                last_exc = e
            except Exception as e:
                self.logger.error(f"Unexpected error during Slack API call: {e}")
                last_exc = e
            if attempt < self.retries:
                time.sleep(self.delay)
        self.logger.error(f"Slack API call {func.__name__} failed after all retries.")
        return None

    # --- Message operations ---
    def send_message(self, channel, text="Default message", blocks=None):
        """
        Send a message to a Slack channel or user.
        
        Args:
            channel (str): Channel ID (e.g., 'C1234567890') or user ID for DMs
            text (str): Message text (fallback for notifications)
            blocks (list, optional): Block Kit blocks for rich formatting
            
        Returns:
            str: Message timestamp if successful, None if failed
            
        Example:
            >>> ts = slack.send_message(
            ...     channel="C1234567890",
            ...     text="Hello!",
            ...     blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "*Hello!*"}}]
            ... )
        """
        if not channel:
            self.logger.error("Channel parameter is required")
            return None
            
        payload = {"channel": channel, "text": text or " "}
        if blocks is not None:
            payload["blocks"] = blocks
        response = self._func_with_retries(self.client.chat_postMessage, payload)
        if response:
            ts = response.get("ts") or response.get("message", {}).get("ts")
            self.logger.debug(f"Slack message sent to {channel} (ts={ts})")
            return ts
        else:
            raise ConnectionError("Unable to send message to Slack after retries")
    
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
        if not channel:
            self.logger.error("Channel parameter is required")
            return None
            
        if not file_path:
            self.logger.error("File path parameter is required")
            return None
            
        try:
            with open(file_path, 'rb') as file_content:
                payload = {
                    "channels": channel,
                    "file": file_content,
                    "filename": file_path.split('/')[-1]
                }
                if title:
                    payload["title"] = title
                if initial_comment:
                    payload["initial_comment"] = initial_comment
                if thread_ts:
                    payload["thread_ts"] = thread_ts
                    
                response = self._func_with_retries(self.client.files_upload_v2, payload)
                if response:
                    file_id = response.get("file", {}).get("id")
                    self.logger.debug(f"File uploaded to {channel} (file_id={file_id})")
                    return file_id
                return None
        except FileNotFoundError:
            self.logger.error(f"File not found: {file_path}")
            return None
        except PermissionError:
            self.logger.error(f"Permission denied reading file: {file_path}")
            return None
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            return None

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
        if not message_ts or not channel:
            self.logger.error("Both message_ts and channel parameters are required")
            return None
            
        payload = {"channel": channel, "ts": message_ts, "text": text or " "}
        if blocks is not None:
            payload["blocks"] = blocks
        response = self._func_with_retries(self.client.chat_update, payload)
        if response:
            self.logger.debug(f"Slack message updated (ts={message_ts})")
        return response
    
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
        if not channel:
            self.logger.error("Channel parameter is required")
            return 0
            
        total_deleted = 0
        cursor = None
        has_more = True
        while has_more:
            payload = {"channel": channel, "cursor": cursor}
            response = self._func_with_retries(self.client.conversations_history, payload)

            # Guard clause - if history fetch failed, stop
            if not response:
                self.logger.error("Failed to fetch conversation history")
                break

            messages = response.get("messages", [])
            cursor = response.get("response_metadata", {}).get("next_cursor")
            has_more = bool(cursor)

            if not messages:
                break

            for msg in messages:
                ts = msg.get("ts")
                if ts:
                    delete_payload = {"channel": channel, "ts": ts}
                    delete_response = self._func_with_retries(self.client.chat_delete, delete_payload)
                    if delete_response:
                        self.logger.debug(f"Slack message deleted (ts={ts})")
                        total_deleted += 1
                    time.sleep(delay)

        self.logger.info(f"Finished deleting messages. Total deleted: {total_deleted}")
        return total_deleted
    
    def delete_specific_messages(self, match_text, channel, delay=0.1):
        """
        Delete messages that match specific text pattern in their blocks.
        
        Searches for messages where the first field in the second block contains
        text matching the pattern _{match_text}_ (underscore-wrapped).
        
        Args:
            match_text (str): Text pattern to match (without underscores)
            channel (str): Channel ID to search in
            delay (float): Delay in seconds between delete operations (default: 0.1)
            
        Returns:
            int: Total number of messages deleted
            
        Example:
            >>> deleted = slack.delete_specific_messages(
            ...     match_text="order-12345",
            ...     channel="C1234567890"
            ... )
        """
        if not match_text or not channel:
            self.logger.error("Both match_text and channel parameters are required")
            return 0
            
        seen_ts = set()
        total_deleted = 0
        cursor = None

        while True:
            payload = {"channel": channel, "cursor": cursor}
            response = self._func_with_retries(self.client.conversations_history, payload)
            if not response:
                self.logger.error("Failed to fetch conversations history")
                break

            messages = response.get("messages", [])
            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not messages:
                break

            for msg in messages:
                ts = msg.get("ts")
                if not ts or ts in seen_ts:
                    continue
                seen_ts.add(ts)

                blocks = msg.get("blocks")
                if not isinstance(blocks, list) or len(blocks) < 2:
                    continue

                fields = blocks[1].get("fields")
                if not isinstance(fields, list) or not fields:
                    continue

                msg_text = fields[0].get("text", "")
                match = re.search(r"_(.*?)_", msg_text)
                if not match:
                    continue

                msg_sn = match.group(1)
                if msg_sn != match_text:
                    continue
            
                delete_payload = {"channel": channel, "ts": ts}
                delete_response = self._func_with_retries(self.client.chat_delete, delete_payload)
                if delete_response:
                    total_deleted += 1
                    self.logger.debug(f"Deleted slack message ts={ts}")
                    time.sleep(delay)

            if not cursor:
                break
        
        self.logger.info(f"Finished deleting messages. Total deleted: {total_deleted}")
        return total_deleted
        """
        List all channels the bot has access to.
        
        Args:
            types (str): Comma-separated channel types (default: "public_channel,private_channel")
            limit (int): Maximum number of channels to return per page (default: 100)
            
        Returns:
            list: List of channel dictionaries if successful, empty list if failed
            
        Example:
            >>> channels = slack.list_channels()
            >>> for channel in channels:
            ...     print(f"{channel['name']}: {channel['id']}")
        """
        all_channels = []
        cursor = None
        
        while True:
            payload = {"types": types, "limit": limit}
            if cursor:
                payload["cursor"] = cursor
                
            response = self._func_with_retries(self.client.conversations_list, payload)
            
            if not response:
                self.logger.error("Failed to fetch channels list")
                break
                
            channels = response.get("channels", [])
            all_channels.extend(channels)
            
            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
        
        self.logger.info(f"Retrieved {len(all_channels)} channels")
        return all_channels