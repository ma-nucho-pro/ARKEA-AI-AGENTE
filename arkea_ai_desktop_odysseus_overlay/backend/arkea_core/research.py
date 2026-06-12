"""Conectores legales para investigación académica.
No incluye Sci-Hub. Sci-Hub se bloquea porque facilita acceder a copias no autorizadas de artículos con copyright.
"""
import requests, urllib.parse

LEGAL_SOURCES = ["OpenAlex", "Crossref", "arXiv", "PubMed", "CORE", "DOAJ", "Unpaywall", "Semantic Scholar"]

def scihub_blocked(*args, **kwargs):
    return {
        "blocked": True,
        "reason": "No se integra Sci-Hub por riesgo de infracción de copyright. Usa fuentes open access y repositorios institucionales.",
        "legal_alternatives": LEGAL_SOURCES,
    }

def search_openalex(query: str, limit: int = 10):
    url = "https://api.openalex.org/works?search=" + urllib.parse.quote(query) + f"&per-page={limit}"
    try:
        data = requests.get(url, timeout=20).json()
        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title"),
                "year": item.get("publication_year"),
                "doi": item.get("doi"),
                "open_access": item.get("open_access", {}),
                "cited_by_count": item.get("cited_by_count"),
                "source": "OpenAlex",
            })
        return results
    except Exception as e:
        return [{"source": "OpenAlex", "error": str(e)}]

def search_crossref(query: str, limit: int = 10):
    url = "https://api.crossref.org/works?query=" + urllib.parse.quote(query) + f"&rows={limit}"
    try:
        data = requests.get(url, timeout=20).json()
        results = []
        for item in data.get("message", {}).get("items", []):
            results.append({
                "title": (item.get("title") or [""])[0],
                "year": (item.get("published-print") or item.get("published-online") or {}).get("date-parts", [[None]])[0][0],
                "doi": item.get("DOI"),
                "url": item.get("URL"),
                "source": "Crossref",
            })
        return results
    except Exception as e:
        return [{"source": "Crossref", "error": str(e)}]

def research_query(query: str, limit: int = 10):
    return {
        "query": query,
        "legal_sources": LEGAL_SOURCES,
        "openalex": search_openalex(query, limit),
        "crossref": search_crossref(query, limit),
    }
