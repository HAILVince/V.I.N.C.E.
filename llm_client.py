"""
VINCE llm_client.py
LLM connection + agentic task loop.
All settings are read from data.py at call time (no restart needed for changes).
"""

import json
import re
import threading
from typing import Callable, Optional
from config import get_system_prompt
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

import data as D
from config import TOOL_CALL_TAG, FINISH_TAG
from logger import (log_user, log_vince, log_tool_call, log_tool_result,
                    log_error, log_system, get_log_context)
from tools import execute_tool, get_tools_for_prompt


class VINCEClient:
    """
    Wraps the OpenAI-compatible llama.cpp API.
    All LLM / model settings are loaded from data.json on every call,
    so changes in Settings take effect immediately without restart.
    """

    def __init__(self):
        if not OPENAI_AVAILABLE:
            raise RuntimeError("openai not installed. Run: pip install openai")
        self._history: list[dict] = []
        self._make_client()
        log_system("VINCEClient initialised.")

    def _make_client(self) -> OpenAI:
        cfg = D.get_llm()
        self.client = OpenAI(
            base_url=cfg.get("base_url", "http://localhost:8080/v1"),
            api_key="not-needed",
        )
        return self.client

    # ─── Public API ──────────────────────────────────────────────────────────

    def chat(
        self,
        user_message: str,
        on_token:       Optional[Callable[[str], None]] = None,
        on_tool_call:   Optional[Callable[[str, dict], None]] = None,
        on_tool_result: Optional[Callable[[str, str], None]] = None,
        on_done:        Optional[Callable[[str], None]] = None,
        on_error:       Optional[Callable[[str], None]] = None,
    ) -> None:
        """Non-blocking. Runs task loop in a background thread."""
        log_user(user_message)
        self._history.append({"role": "user", "content": user_message})
        threading.Thread(
            target=self._task_loop,
            args=(on_token, on_tool_call, on_tool_result, on_done, on_error),
            daemon=True,
        ).start()

    def clear_history(self) -> None:
        self._history.clear()
        log_system("History cleared.")

    @property
    def history(self) -> list[dict]:
        return list(self._history)

    # ─── Task Loop ───────────────────────────────────────────────────────────

    def _task_loop(self, on_token, on_tool_call, on_tool_result, on_done, on_error):
        cfg = D.get_llm()
        max_iters = cfg.get("max_tool_iters", 8)
        try:
            for _ in range(max_iters + 1):
                messages  = self._build_messages()
                raw       = self._call_llm(messages, on_token)
                self._history.append({"role": "assistant", "content": raw})

                # Check for tool call
                tool_match = self._parse_tool_call(raw)
                if tool_match:
                    action, params = tool_match
                    if on_tool_call:
                        on_tool_call(action, params)
                    result = execute_tool(action, params)
                    if on_tool_result:
                        on_tool_result(action, result)
                    self._history.append({
                        "role": "user",
                        "content": f"TOOL_RESULT: [{action}]\n{result}"
                    })
                    continue

                # Check for FINAL_ANSWER
                final = self._parse_final(raw)
                if final:
                    log_vince(final)
                    if on_done:
                        on_done(final)
                    return

                # Plain response
                log_vince(raw)
                if on_done:
                    on_done(raw)
                return

            # Hit iteration cap
            cap_msg = ("I appear to have reached my tool-call budget for this turn. "
                       "Shall I continue, or would you prefer to rephrase?")
            log_vince(cap_msg)
            self._history.append({"role": "assistant", "content": cap_msg})
            if on_done:
                on_done(cap_msg)

        except Exception as exc:
            err = f"[LLM error] {exc}"
            log_error(err)
            if on_error:
                on_error(err)

    # ─── Message Builder ─────────────────────────────────────────────────────

    def _build_messages(self) -> list[dict]:
        profile = D.get_current_profile()
        extra   = profile.get("system_extra", "").strip()
        backstory = profile.get("user_backstory", "").strip()
        profile_block = (
            f"## User Profile\nName: {profile.get('name', 'User')}\n"
            + (f"Additional context: {extra}" if extra else "")
            + (f"\n\nUser backstory/information:\n{backstory}" if backstory else "")
        )

        tools_block = get_tools_for_prompt()
        # 1. Get raw prompt from the text file
        raw_system = get_system_prompt()
        
        # 2. Safely replace the exact placeholders (ignores brackets elsewhere)
        system = raw_system.replace("{profile_extra}", profile_block)
        system = system.replace("{tools_list}", tools_block)
        
        # 3. Clean up any double braces {{ }} leftover from old format strings
        system = system.replace("{{", "{").replace("}}", "}")

        log_ctx = get_log_context()
        if log_ctx:
            system += (
                "\n\n## Recent Session Log\n```\n" + log_ctx + "\n```"
            )
            
        msgs = [{"role": "system", "content": system}]
        cfg = D.get_llm()
        trimmed = self._history[-cfg.get("max_ctx_messages", 60):]
        msgs.extend(trimmed)
        #debug print(json.dumps(msgs,indent=4))
        return msgs

    # ─── LLM Caller ──────────────────────────────────────────────────────────

    def _call_llm(self, messages: list[dict],
                  on_token: Optional[Callable[[str], None]]) -> str:
        cfg   = D.get_llm()
        model = D.get("current_model") or "local-model"
        self._make_client()  # re-init in case base_url changed

        kwargs = dict(
            model       = model,
            messages    = messages,
            max_tokens  = cfg.get("max_tokens", 4096),
            temperature = cfg.get("temperature", 0.7),
        )
        # optional params — only send if server might support them
        if cfg.get("top_p", 0) not in (0, 1):
            kwargs["top_p"] = cfg["top_p"]

        full = ""
        if cfg.get("stream", True) and on_token:
            stream = self.client.chat.completions.create(stream=True, **kwargs)
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    full += delta.content
                    on_token(delta.content)
        else:
            resp = self.client.chat.completions.create(stream=False, **kwargs)
            full = resp.choices[0].message.content or ""
        return full.strip()

    # ─── Parsers ─────────────────────────────────────────────────────────────

    def _parse_tool_call(self, text: str) -> Optional[tuple[str, dict]]:
        import json
        
        # 1. Find where the TOOL_CALL starts
        start_idx = text.find("TOOL_CALL:")
        if start_idx == -1:
            return None
            
        text_after = text[start_idx:]
        
        # 2. Find the first opening brace
        first_brace = text_after.find('{')
        if first_brace == -1:
            return None
            
        # 3. Brace balancing to find the EXACT matching closing brace
        brace_count = 0
        last_brace = -1
        
        for i, char in enumerate(text_after[first_brace:]):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    last_brace = first_brace + i
                    break
                    
        if last_brace == -1: # Unclosed JSON
            return None
            
        # 4. Extract ONLY the clean JSON dictionary
        json_str = text_after[first_brace:last_brace+1]
        
        # 5. Safely parse
        try:
            payload = json.loads(json_str)
            action  = payload.get("action", "")
            params  = payload.get("parameters", {})
            return (action, params) if action else None
        except json.JSONDecodeError as e:
            from logger import log_error
            log_error(f"Bad tool call JSON: {e} | Extracted: {json_str}")
            return None

    def _parse_final(self, text: str) -> Optional[str]:
        s = text.strip()
        return s[len(FINISH_TAG):].strip() if s.startswith(FINISH_TAG) else None
