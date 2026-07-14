from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from src.logger import get_logger

logger = get_logger(__name__)


class LLMAgent:
    REPO_ID = "Qwen/Qwen2.5-1.5B-Instruct-GGUF"
    FILENAME = "qwen2.5-1.5b-instruct-q4_k_m.gguf"

    SYSTEM_PROMPT = (
        "Você é um revisor de texto profissional especialista em refinar transcrições de áudio. "
        "Sua tarefa é transformar a transcrição bruta em um "
        "texto fluido, coeso e gramaticalmente correto. "
        "Regras obrigatórias:\n"
        "1. Remova TODAS as repetições de palavras, gaguejos, hesitações "
        "e vícios de linguagem (ex: 'né', 'tipo', 'tá', 'então', 'eh', 'sei lá').\n"
        "2. Corrija a pontuação, acentuação e erros ortográficos.\n"
        "3. Melhore a conexão das frases (coesão), reescrevendo "
        "trechos confusos ou enrolados para que fiquem claros e diretos.\n"
        "4. Mantenha a ideia central e o significado original, mas não "
        "tenha medo de reestruturar a frase para que fique bem escrita.\n"
        "5. RETORNE APENAS O TEXTO CORRIGIDO. NUNCA converse com o "
        "usuário, não faça resumos e não adicione notas."
    )

    def __init__(self) -> None:
        self._model: Any | None = None
        self._load_lock = threading.Lock()
        self._rewrite_thread: threading.Thread | None = None

    def _ensure_model_loaded(self) -> None:
        if self._model is not None:
            return

        with self._load_lock:
            if self._model is not None:
                return

            try:
                from huggingface_hub import hf_hub_download
                from llama_cpp import Llama
            except ImportError as exc:
                raise RuntimeError(
                    "LLM rewrite is unavailable because optional dependencies are missing. "
                    "Install 'huggingface_hub' and 'llama-cpp-python' to enable it."
                ) from exc

            logger.info("Downloading/Loading LLM: %s (%s)", self.REPO_ID, self.FILENAME)
            model_path = hf_hub_download(
                repo_id=self.REPO_ID,
                filename=self.FILENAME,
            )

            logger.info("Initializing Llama CPP with model: %s", model_path)
            self._model = Llama(
                model_path=model_path,
                n_ctx=2048,
                verbose=False,
            )
            logger.info("LLM initialized successfully")

    def rewrite_text(
        self,
        text: str,
        on_chunk: Callable[[str], None],
        on_done: Callable[[], None],
        on_error: Callable[[str], None],
    ) -> None:
        if not text.strip():
            on_done()
            return

        if self._rewrite_thread is not None and self._rewrite_thread.is_alive():
            on_error("Já existe uma reescrita em andamento.")
            return

        self._rewrite_thread = threading.Thread(
            target=self._rewrite_worker,
            args=(text, on_chunk, on_done, on_error),
            daemon=True,
        )
        self._rewrite_thread.start()

    def _rewrite_worker(
        self,
        text: str,
        on_chunk: Callable[[str], None],
        on_done: Callable[[], None],
        on_error: Callable[[str], None],
    ) -> None:
        try:
            self._ensure_model_loaded()
            assert self._model is not None

            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Corrija o seguinte texto transcrito:\n\n{text}",
                },
            ]

            stream = self._model.create_chat_completion(
                messages=messages,
                stream=True,
                temperature=0.3,
                max_tokens=1024,
            )

            for chunk in stream:
                delta = chunk["choices"][0]["delta"]
                if "content" in delta:
                    on_chunk(delta["content"])

            on_done()

        except Exception as exc:
            logger.exception("Error during LLM text rewrite")
            on_error(f"Erro na reescrita: {str(exc)}")
