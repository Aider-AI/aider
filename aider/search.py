import httpx

CONTEXT_SEARCH_URL = "https://api.context.dev/v1/web/search"


def search_web(query, api_key, verify_ssl=True):
    if len(query) > 500:
        raise ValueError("Search queries must be 500 characters or fewer.")

    try:
        with httpx.Client(timeout=30, verify=verify_ssl) as client:
            response = client.post(
                CONTEXT_SEARCH_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json={"query": query, "numResults": 10},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as error:
        raise RuntimeError(
            f"Context.dev search failed with HTTP {error.response.status_code}."
        ) from error
    except (httpx.HTTPError, ValueError) as error:
        raise RuntimeError(f"Context.dev search failed: {error}") from error

    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list):
        raise RuntimeError("Context.dev returned an invalid search response.")

    formatted_results = []
    for result in results:
        if not isinstance(result, dict) or not result.get("url"):
            continue

        title = str(result.get("title") or result["url"])[:500]
        description = str(result.get("description") or "")[:1000]
        relevance = result.get("relevance")
        heading = f"- [{title}]({result['url']})"
        if relevance:
            heading += f" ({relevance} relevance)"
        formatted_results.append(f"{heading}\n  {description}" if description else heading)

    if not formatted_results:
        raise RuntimeError("Context.dev returned no search results.")

    return "\n\n".join(formatted_results)
