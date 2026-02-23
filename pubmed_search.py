"""
pubmed_search.py
"""

import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


# NCBI E-utilities base URLs
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# Max number of articles to return per search
MAX_RESULTS = 5


def extract_keywords(text: str) -> str:
    """
    Extract keywords from health claim for search query.
    Simple strategy: remove common stopwords, take first 5 meaningful words.

    Args:
        text: Health claim text.
    Returns:
        Space-separated keyword string.
    """
    # Common stopwords (simplified set)
    stopwords = {
        '的', '了', '和', '是', '在', '我', '有', '他', '这', '个',
        '们', '中', '来', '上', '大', '为', '与', '会', '对', '可',
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
        'can', 'could', 'will', 'would', 'should', 'may', 'might',
        'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from'
    }

    # Extract English words and Chinese phrases (simple tokenization)
    words = re.findall(r'[a-zA-Z]{3,}|[\u4e00-\u9fff]{2,4}', text)
    keywords = [w for w in words if w.lower() not in stopwords]

    # Take first 5 keywords
    selected = keywords[:5]
    return ' '.join(selected) if selected else text[:50]


def search_pubmed(query: str, max_results: int = MAX_RESULTS) -> list[dict]:
    """
    Search PubMed for relevant literature.

    Args:
        query: Search terms (English works better).
        max_results: Maximum number of results to return.
    Returns:
        List of articles, each with title, authors, journal, year, pmid, abstract.
    """
    # Step 1: ESearch — get PMID list
    search_params = urllib.parse.urlencode({
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance",
        # Prefer articles from last ~5 years
        "datetype": "pdat",
        "reldate": 1825,
    })

    try:
        with urllib.request.urlopen(
            f"{ESEARCH_URL}?{search_params}", timeout=10
        ) as response:
            import json
            data = json.loads(response.read().decode())
        pmid_list = data.get("esearchresult", {}).get("idlist", [])
    except Exception:
        return []

    if not pmid_list:
        return []

    # Step 2: EFetch — get article details
    # NCBI recommends no more than 3 requests per second
    time.sleep(0.4)

    fetch_params = urllib.parse.urlencode({
        "db": "pubmed",
        "id": ",".join(pmid_list),
        "retmode": "xml",
        "rettype": "abstract",
    })

    try:
        with urllib.request.urlopen(
            f"{EFETCH_URL}?{fetch_params}", timeout=15
        ) as response:
            xml_data = response.read()
    except Exception:
        return []

    return parse_pubmed_xml(xml_data)


def parse_pubmed_xml(xml_data: bytes) -> list[dict]:
    """
    Parse PubMed EFetch XML response and extract article fields.

    Args:
        xml_data: Raw bytes of PubMed XML response.
    Returns:
        List of article dicts.
    """
    results = []
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError:
        return results

    for article in root.findall(".//PubmedArticle"):
        try:
            # Extract title
            title_el = article.find(".//ArticleTitle")
            title = title_el.text if title_el is not None else "N/A"
            # Flatten inline XML text
            title = "".join(title_el.itertext()) if title_el is not None else "N/A"

            # Extract authors (up to 3)
            authors = []
            for author in article.findall(".//Author")[:3]:
                last = author.findtext("LastName", "")
                initials = author.findtext("Initials", "")
                if last:
                    authors.append(f"{last} {initials}".strip())
            if len(article.findall(".//Author")) > 3:
                authors.append("et al.")

            # Extract journal name
            journal = article.findtext(".//Journal/Title", "Unknown Journal")

            # Extract publication year
            year = (
                article.findtext(".//PubDate/Year")
                or article.findtext(".//PubDate/MedlineDate", "")[:4]
                or "N/A"
            )

            # Extract PMID
            pmid_el = article.find(".//PMID")
            pmid = pmid_el.text if pmid_el is not None else ""

            # Extract abstract (first 300 chars)
            abstract_texts = article.findall(".//AbstractText")
            abstract = " ".join(
                "".join(el.itertext()) for el in abstract_texts
            )[:300]
            if len(abstract) == 300:
                abstract += "..."

            results.append({
                "title":    title,
                "authors":  ", ".join(authors) if authors else "Unknown",
                "journal":  journal,
                "year":     year,
                "pmid":     pmid,
                "abstract": abstract,
                "url":      f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
            })
        except Exception:
            # Skip single article on parse failure
            continue

    return results


def get_evidence_for_claim(health_claim: str) -> list[dict]:
    """
    Convenience API: extract keywords from health claim and search PubMed.

    Args:
        health_claim: User-provided health claim text.
    Returns:
        List of relevant articles.
    """
    keywords = extract_keywords(health_claim)
    return search_pubmed(keywords)
