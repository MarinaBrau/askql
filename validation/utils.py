"""Utilitários compartilhados para os runners de validação."""

import time


def call_with_retry(fn, *args, max_retries=3, base_wait=60, **kwargs):
    """
    Executa fn(*args, **kwargs) com retry automático em caso de rate limiting (429).

    Args:
        fn: Função a executar (ex: generate_query)
        *args: Argumentos posicionais para fn
        max_retries: Número máximo de tentativas após a primeira falha (padrão: 3)
        base_wait: Segundos de espera na primeira tentativa; dobra a cada retry (padrão: 60)
        **kwargs: Argumentos nomeados para fn

    Returns:
        O retorno de fn(*args, **kwargs)

    Raises:
        Exception: Qualquer erro que não seja 429, ou 429 após esgotar as tentativas.
    """
    attempt = 0
    wait = base_wait
    while True:
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            err = str(e)
            is_rate_limit = "429" in err or "rate_limit" in err or "rate limit" in err.lower()
            is_insufficient_credits = "credit balance" in err.lower() or "402" in err

            if is_insufficient_credits:
                raise  # Crédito esgotado — não adianta retry

            if is_rate_limit and attempt < max_retries:
                attempt += 1
                print(f"\n  [RETRY {attempt}/{max_retries}] Rate limit — aguardando {wait}s...", flush=True)
                time.sleep(wait)
                wait *= 2  # backoff exponencial
            else:
                raise
