"""
core/multi_provider_llm.py — JARVIS OMEGA V4 Multi-Provider Free LLM Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tries multiple FREE API providers IN PARALLEL until one succeeds.
All providers listed have a free tier (API key required but $0 cost).

Providers:
  1. Google Gemini (1,500 req/day free) — gemini-1.5-flash
  2. OpenRouter (free models with :free suffix) — Llama, Mistral, Falcon
  3. NVIDIA NIM (free tier) — Llama-3.1, Mixtral, etc.
  4. SambaNova (free tier) — very fast Llama inference
  5. Cerebras (free tier) — Llama-3.1-8b

Usage: provider = MultiProviderLLM(settings); response = provider.chat_parallel(messages)
"""

import logging
import time
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict

logger = logging.getLogger("JARVIS.LLM")


class MultiProviderLLM:
    """
    Parallel round-robin across free LLM providers.
    Each provider has its own rate-limit tracking.
    """

    def __init__(self, settings: dict):
        self.settings = settings
        self._clients: Dict[str, object] = {}
        self._last_used: Dict[str, float] = {}
        self._cooldowns: Dict[str, float] = {}
        self._lock = threading.Lock()

        self._provider_names = ["gemini", "openrouter", "nvidia", "sambanova", "cerebras"]
        self._init_clients()

    # ── Init ───────────────────────────────────────────────────────────────────

    def _init_clients(self):
        # Gemini
        gemini_key = self._get_key("google_api_key", "GOOGLE_API_KEY")
        if gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                self._clients["gemini"] = genai
                logger.info("Gemini client ready.")
            except Exception as exc:
                logger.warning("Gemini init failed: %s", exc)

        # OpenRouter
        or_key = self._get_key("openrouter_api_key", "OPENROUTER_API_KEY")
        if or_key:
            try:
                import openai
                client = openai.OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=or_key,
                    timeout=20.0,
                )
                self._clients["openrouter"] = client
                logger.info("OpenRouter client ready.")
            except Exception as exc:
                logger.warning("OpenRouter init failed: %s", exc)

        # NVIDIA NIM
        nv_key = self._get_key("nvidia_api_key", "NVIDIA_API_KEY")
        if nv_key:
            try:
                import openai
                client = openai.OpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key=nv_key,
                    timeout=25.0,
                )
                self._clients["nvidia"] = client
                logger.info("NVIDIA NIM client ready.")
            except Exception as exc:
                logger.warning("NVIDIA init failed: %s", exc)

        # SambaNova
        sb_key = self._get_key("sambanova_api_key", "SAMBANOVA_API_KEY")
        if sb_key:
            try:
                import openai
                client = openai.OpenAI(
                    base_url="https://api.sambanova.ai/v1",
                    api_key=sb_key,
                    timeout=20.0,
                )
                self._clients["sambanova"] = client
                logger.info("SambaNova client ready.")
            except Exception as exc:
                logger.warning("SambaNova init failed: %s", exc)

        # Cerebras
        cb_key = self._get_key("cerebras_api_key", "CEREBRAS_API_KEY")
        if cb_key:
            try:
                import openai
                client = openai.OpenAI(
                    base_url="https://api.cerebras.ai/v1",
                    api_key=cb_key,
                    timeout=20.0,
                )
                self._clients["cerebras"] = client
                logger.info("Cerebras client ready.")
            except Exception as exc:
                logger.warning("Cerebras init failed: %s", exc)

    def _get_key(self, settings_key: str, env_key: str) -> str:
        val = self.settings.get(settings_key, "").strip()
        if not val:
            val = os.environ.get(env_key, "").strip()
        return val

    # ── Public API ────────────────────────────────────────────────────────────

    def chat_parallel(self, messages, temperature=0.7, max_tokens=2048) -> str:
        """Try EVERY available provider in parallel. Return the first successful response."""
        with self._lock:
            # Build list of callable providers that are not on cooldown
            active = []
            for name in self._provider_names:
                if name not in self._clients:
                    continue
                cooldown_end = self._cooldowns.get(name, 0)
                if time.time() < cooldown_end:
                    logger.debug("%s on cooldown (%.1f s left)", name, cooldown_end - time.time())
                    continue
                active.append(name)

        if not active:
            logger.warning("All multi-provider clients on cooldown or missing.")
            return ""

        # Warm-up rate-limit spacing
        for name in active:
            with self._lock:
                last = self._last_used.get(name, 0)
                wait = 0.4 - (time.time() - last)
                if wait > 0:
                    time.sleep(wait)
                self._last_used[name] = time.time()

        def _try(name: str) -> Optional[str]:
            try:
                return getattr(self, f"_call_{name}")(messages, temperature, max_tokens)
            except Exception as exc:
                err = str(exc)
                logger.warning("Provider %s failed: %s", name, err[:200])
                if self._is_rate_limit(exc):
                    with self._lock:
                        self._cooldowns[name] = time.time() + 8.0
                return None

        # Race all providers
        first_result = None
        with ThreadPoolExecutor(max_workers=len(active)) as executor:
            futures = {executor.submit(_try, name): name for name in active}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    result = future.result()
                    if result:
                        logger.info("Provider %s won the race (%d total).", name, len(active))
                        first_result = result
                        # Cancel remaining futures (best-effort)
                        for f in futures:
                            f.cancel()
                        break
                except Exception as exc:
                    logger.warning("Provider %s crashed: %s", name, exc)

        return first_result or ""

    def call_individual(self, name: str, messages, temperature=0.7, max_tokens=2048) -> Optional[str]:
        """Call a single provider by name."""
        method = getattr(self, f"_call_{name}", None)
        if not method:
            return None
        try:
            return method(messages, temperature, max_tokens)
        except Exception as exc:
            logger.warning("Individual call %s failed: %s", name, exc)
            return None

    def chat_all(self, messages, temperature=0.7, max_tokens=2048, timeout=10.0) -> dict:
        """
        Query EVERY available provider in parallel and return ALL responses.
        Returns: {provider_name: response_text}  (missing = failed).
        Waits up to `timeout` seconds for the slowest provider.
        """
        with self._lock:
            active = []
            for name in self._provider_names:
                if name not in self._clients:
                    continue
                cooldown_end = self._cooldowns.get(name, 0)
                if time.time() < cooldown_end:
                    logger.debug("%s on cooldown (%.1f s left)", name, cooldown_end - time.time())
                    continue
                active.append(name)

        if not active:
            logger.warning("All multi-provider clients on cooldown or missing.")
            return {}

        # Rate-limit warm-up spacing
        for name in active:
            with self._lock:
                last = self._last_used.get(name, 0)
                wait = 0.4 - (time.time() - last)
                if wait > 0:
                    time.sleep(wait)
                self._last_used[name] = time.time()

        results = {}
        def _try(name: str):
            try:
                return name, self.call_individual(name, messages, temperature, max_tokens)
            except Exception as exc:
                err = str(exc)
                logger.warning("Provider %s failed in chat_all: %s", name, err[:200])
                if self._is_rate_limit(exc):
                    with self._lock:
                        self._cooldowns[name] = time.time() + 8.0
                return name, None

        with ThreadPoolExecutor(max_workers=len(active)) as executor:
            futures = {executor.submit(_try, name): name for name in active}
            start = time.time()
            for future in as_completed(futures):
                if time.time() - start > timeout:
                    # Cancel remaining (best-effort) and break
                    for f in futures:
                        f.cancel()
                    break
                try:
                    name, result = future.result(timeout=2)
                    if result:
                        results[name] = result
                        logger.info("Provider '%s' returned %d chars in chat_all.", name, len(result))
                except Exception as exc:
                    logger.warning("Provider '%s' future error: %s", futures[future], exc)
        return results

    def any_available(self) -> bool:
        return len(self._clients) > 0

    # ── Rate-limit detection ──────────────────────────────────────────────────

    def _is_rate_limit(self, exc: Exception) -> bool:
        err = str(exc).lower()
        return any(k in err for k in (
            "429", "rate limit", "too many requests", "throttled",
            "quota exceeded", "limit exceeded", "capacity",
        ))

    # ── Provider: Google Gemini ───────────────────────────────────────────────

    def _call_gemini(self, messages, temperature, max_tokens) -> str:
        client = self._clients.get("gemini")
        if not client:
            return ""
        # Convert OpenAI-style messages to Gemini prompt
        system_parts = []
        user_parts = []
        for m in messages:
            role = m.get("role", "")
            content = m.get("content", "")
            if role == "system":
                system_parts.append(content)
            elif role == "user":
                user_parts.append(content)
            elif role == "assistant":
                user_parts.append(f"[Previous AI response]: {content}")
        prompt = "\n".join(system_parts + user_parts)
        model = client.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(
            prompt,
            generation_config=client.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        return resp.text or ""

    # ── Provider: OpenRouter ──────────────────────────────────────────────────

    def _call_openrouter(self, messages, temperature, max_tokens) -> str:
        client = self._clients.get("openrouter")
        if not client:
            return ""
        # Free models ( :free suffix means $0 )
        free_models = [
            "meta-llama/llama-3.1-8b-instruct:free",
            "meta-llama/llama-3.2-3b-instruct:free",
            "mistralai/mistral-7b-instruct:free",
            "google/gemini-flash-1.5:free",
            "huggingfaceh4/zephyr-7b-beta:free",
            "nousresearch/hermes-3-llama-3.1-405b:free",
        ]
        for model in free_models:
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=min(max_tokens, 1024),
                    extra_headers={"HTTP-Referer": "https://jarvis-omega.local", "X-Title": "JARVIS OMEGA"},
                )
                return resp.choices[0].message.content or ""
            except Exception:
                continue
        return ""

    # ── Provider: NVIDIA NIM ──────────────────────────────────────────────────

    def _call_nvidia(self, messages, temperature, max_tokens) -> str:
        client = self._clients.get("nvidia")
        if not client:
            return ""
        models = [
            "nvidia/nemotron-3-ultra-550b-a55b",  # NEW: massive 550B MoE, free tier
            "meta/llama-3.1-8b-instruct",
            "meta/llama-3.1-70b-instruct",
            "mistralai/mistral-7b-instruct-v0.3",
            "google/gemma-2-9b-it",
        ]
        for model in models:
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=min(max_tokens, 1024),
                )
                return resp.choices[0].message.content or ""
            except Exception:
                continue
        return ""

    # ── Provider: SambaNova ───────────────────────────────────────────────────

    def _call_sambanova(self, messages, temperature, max_tokens) -> str:
        client = self._clients.get("sambanova")
        if not client:
            return ""
        models = [
            "Meta-Llama-3.1-8B-Instruct",
            "Meta-Llama-3.1-70B-Instruct",
            "Meta-Llama-3.2-1B-Instruct",
            "Llama-3.2-90B-Vision-Instruct",
        ]
        for model in models:
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=min(max_tokens, 1024),
                )
                return resp.choices[0].message.content or ""
            except Exception:
                continue
        return ""

    # ── Provider: Cerebras ────────────────────────────────────────────────────

    def _call_cerebras(self, messages, temperature, max_tokens) -> str:
        client = self._clients.get("cerebras")
        if not client:
            return ""
        models = [
            "llama3.1-8b",
            "llama-3.3-70b",
        ]
        for model in models:
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=min(max_tokens, 1024),
                )
                return resp.choices[0].message.content or ""
            except Exception:
                continue
        return ""
