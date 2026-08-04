import logging
import time
import re
from slack_sdk.web import WebClient
from slack_bolt import App
from slack_sdk.errors import SlackApiError

class SlackClientWrapper:
    """
    General-purpose Slack client wrapper for any project.
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
        for attempt in range(1, self.retries + 1):
            try:
                self.logger.info(f"Connecting to Slack (attempt {attempt}/{self.retries})")
                client = WebClient(token=self.bot_token)
                app = App(token=self.bot_token)
                auth = client.auth_test()
                self.logger.info(f"Connected to Slack workspace: {auth.get('team')}")
                return client, app
            except SlackApiError as e:
                self.logger.error(f"Slack API error: {e.response['error']}")
            except Exception as e:
                self.logger.error(f"Unexpected error during Slack connection: {e}")
            if attempt < self.retries:
                time.sleep(self.delay)
        raise ConnectionError("Unable to connect to Slack after retries")

    def _func_with_retries(self, func, payload):
        for attempt in range(1, self.retries + 1):
            try:
                self.logger.info(f"Slack API call {func.__name__} (attempt {attempt}/{self.retries})")
                return func(**payload)
            except SlackApiError as e:
                code = e.response.get("error", "unknown_error")
                self.logger.error(f"Slack API Error (attempt {attempt}/{self.retries}): {code}")
            except Exception as e:
                self.logger.error(f"Unexpected error during Slack API call: {e}")
            time.sleep(self.delay)
        self.logger.error(f"Slack API call {func.__name__} failed after all retries.")
        return None

    # --- Message operations ---
    def send_message(self, channel, text="Default message", blocks=None):
        payload = {"channel": channel, "text": text or " "}
        if blocks is not None:
            payload["blocks"] = blocks
        response = self._func_with_retries(self.client.chat_postMessage, payload)
        ts = response.get("ts") or response.get("message", {}).get("ts") if response else None
        if ts:
            self.logger.info(f"Slack message sent to {channel} (ts={ts})")
        return ts    

    def update_message(self, message_ts, channel, text="Default message", blocks=None):
        payload = {"channel": channel, "ts": message_ts, "text": text or " "}
        if blocks is not None:
            payload["blocks"] = blocks
        response = self._func_with_retries(self.client.chat_update, payload)
        if response:
            self.logger.info(f"Slack message updated (ts={message_ts})")
        return response
    
    def delete_all_messages(self, channel, delay=0.1):
        total_deleted = 0
        cursor = None
        has_more = True
        while has_more:
            payload = {"channel": channel, "cursor": cursor}
            response = self._func_with_retries(self.client.conversations_history, payload)
            messages = response.get("messages", [])
            cursor = response.get("response_metadata", {}).get("next_cursor")
            has_more = bool(cursor)
            if not messages:
                break
            for msg in messages:
                ts = msg.get("ts")
                if ts:
                    payload = {"channel": channel, "ts": ts}
                    response = self._func_with_retries(self.client.chat_delete, payload)
                    if response:
                        self.logger.info(f"Slack message deleted (ts={ts})")
                        total_deleted += 1
                    time.sleep(delay)
        self.logger.info(f"Finished deleting messages. Total deleted: {total_deleted}")
        return total_deleted
    
    def delete_specific_messages(self, match_text, channel, delay=0.1):
        seen_ts = set()
        total_deleted = 0
        cursor = None

        while True:
            payload = {"channel": channel, "cursor": cursor}
            response = self._func_with_retries(self.client.conversations_history, payload)
            if not response:
                self.logger.error("failed to fetch conversations history")
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
                    self.logger.info(f"Deleted slack message ts={ts}")
                    time.sleep(delay)

                if not cursor:
                    break
        
        self.logger.info(f"Finished deleting messages. Total deleted: {total_deleted}")
        return total_deleted