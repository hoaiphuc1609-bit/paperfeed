#!/usr/bin/env python3
"""Fetch daily papers from PubMed and write data/papers.json."""

from __future__ import annotations

import datetime as dt
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

TOPIC_QUERIES = [
    "maxillofacial surgery",
    "oral surgery",
    "facial reconstruction surgery",
    "orthognathic surgery",
    "facial trauma",
    "oral and maxillofacial infections",
    "cleft lip and palate surgery",
]

MAX_RESULTS_PER_TOPIC = 40
MAX_AGE_DAYS = 7

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
OUT_FILE = Path("data/papers.json")

MONTH_MAP = {
    "jan": "01",
    "feb": "02",
    "mar": "03",
    "apr": "04",
    "may": "05",
    "jun": "06",
    "jul": "07",
    "aug": "08",
    "sep": "09",
    "oct": "10",
    "nov": "11",
    "dec": "12",
}


def request_text(url: str, params: dict[str, str]) -> str:
    query = urllib.parse.urlencode(params)
    request_url = f"{url}?{query}"
    last_error: Exception | None = None

    headers = {
        "User-Agent": "paperfeed-bot/1.0 (https://pubmed.ncbi.nlm.nih.gov/)",
        "Accept": "text/html,application/xml,application/json;q=0.9,*/*;q=0.8",
    }

    for attempt in range(3):
        try:
            req = urllib.request.Request(request_url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read().decode("utf-8", errors="replace")
        except Exception as err:  # noqa: BLE001
            last_error = err
            if attempt < 2:
                time.sleep(1 + attempt)

    raise RuntimeError(f"Failed request after retries: {request_url}") from last_error


def normalize_pub_date(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""

    tokens = re.findall(r"[A-Za-z]+|\d+", value)
    year = next((t for t in tokens if re.fullmatch(r"\d{4}", t)), "")
    if not year:
        return value

    month = "01"
    day = "01"

    for token in tokens:
        key = token[:3].lower()
        if key in MONTH_MAP:
            month = MONTH_MAP[key]
            break

    numeric_tokens = [t for t in tokens if t.isdigit() and len(t) <= 2]
    if numeric_tokens:
        maybe_day = int(numeric_tokens[0])
        if 1 <= maybe_day <= 31:
            day = f"{maybe_day:02d}"

    return f"{year}-{month}-{day}"


def to_iso_date(value: str) -> dt.date | None:
    if not value:
        return None

    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y-%b-%d", "%Y-%B-%d", "%Y-%b", "%Y-%B", "%Y"):
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    year_match = re.match(r"^(\d{4})", value)
    if year_match:
        return dt.date(int(year_match.group(1)), 1, 1)

    return None


def extract_abstract_sections(article: ET.Element) -> tuple[str, str, str]:
    abstract_elems = article.findall(".//Abstract/AbstractText")
    full_abstract_parts: list[str] = []
    methods_parts: list[str] = []
    limitations_parts: list[str] = []

    for elem in abstract_elems:
        label = (elem.attrib.get("Label") or "").strip().lower()
        text = " ".join("".join(elem.itertext()).split())
        if not text:
            continue

        full_abstract_parts.append(text)

        if "method" in label or re.match(r"^methods?$", label):
            methods_parts.append(text)
        if "limitation" in label:
            limitations_parts.append(text)

    full_abstract = " ".join(full_abstract_parts).strip()

    if not methods_parts and full_abstract:
        method_match = re.search(r"(methods?:.*?)(results?:|conclusions?:|$)", full_abstract, flags=re.IGNORECASE | re.DOTALL)
        if method_match:
            methods_parts.append(method_match.group(1).strip())

    if not limitations_parts and full_abstract:
        limit_match = re.search(r"(limitations?:.*?)(conclusions?:|$)", full_abstract, flags=re.IGNORECASE | re.DOTALL)
        if limit_match:
            limitations_parts.append(limit_match.group(1).strip())

    return full_abstract, " ".join(methods_parts).strip(), " ".join(limitations_parts).strip()




def extract_core_sections(abstract_text: str) -> tuple[str, str, str]:
    text = " ".join((abstract_text or "").split())
    if not text:
        return "", "", ""

    def find(patterns: list[str]) -> str:
        for pat in patterns:
            match = re.search(pat, text, flags=re.IGNORECASE | re.DOTALL)
            if match:
                return " ".join(match.group(1).split()).strip()
        return ""

    objective = find([
        r"(?:^|\b)(?:objectives?|aims?|purpose)\b\s*[:.-]?\s*(.*?)(?=\b(?:methods?|materials? and methods?|results?|conclusions?)\b|$)",
    ])

    results = find([
        r"\bresults?\s*[:.-]?\s*(.*?)(?=\b(?:conclusions?)\b|$)",
    ])

    conclusion = find([
        r"\bconclusions?\s*[:.-]?\s*(.*)$",
    ])

    return objective, results, conclusion

def parse_pub_date(article: ET.Element) -> str:
    pub_date = article.find(".//Journal/JournalIssue/PubDate")
    if pub_date is None:
        return ""

    year = (pub_date.findtext("Year") or "").strip()
    month = (pub_date.findtext("Month") or "").strip()
    day = (pub_date.findtext("Day") or "").strip()
    medline_date = (pub_date.findtext("MedlineDate") or "").strip()

    if year:
        parts = [year]
        if month:
            parts.append(month)
        if day:
            parts.append(day)
        return "-".join(parts)

    return medline_date




def extract_pmcid(pubmed_article: ET.Element) -> str:
    for elem in pubmed_article.findall('.//PubmedData/ArticleIdList/ArticleId'):
        if (elem.attrib.get('IdType') or '').lower() == 'pmc':
            return (elem.text or '').strip()
    return ''


def fetch_pmc_figure_urls(pmcid: str, max_figures: int = 4) -> list[str]:
    if not pmcid:
        return []

    xml_url = f'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML'
    try:
        fulltext_xml = request_text(xml_url, {})
    except Exception:  # noqa: BLE001
        return []

    hrefs = re.findall(r'<graphic[^>]+xlink:href="([^"]+)"', fulltext_xml, flags=re.IGNORECASE)
    figure_urls: list[str] = []

    for href in hrefs:
        cleaned = href.strip()
        if not re.search(r'\.(jpg|jpeg|png|gif|webp)$', cleaned, flags=re.IGNORECASE):
            continue

        if cleaned.lower().startswith('http://') or cleaned.lower().startswith('https://'):
            url = cleaned
        else:
            url = f'https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/bin/{cleaned}'

        if url not in figure_urls:
            figure_urls.append(url)

        if len(figure_urls) >= max_figures:
            break

    return figure_urls

def fetch_pmids_by_topic() -> dict[str, list[str]]:
    results: dict[str, list[str]] = {}
    for topic in TOPIC_QUERIES:
        params = {
            "db": "pubmed",
            "term": f'"{topic}"',
            "retmax": str(MAX_RESULTS_PER_TOPIC),
            "retmode": "json",
            "sort": "pub date",
        }
        raw = request_text(ESEARCH_URL, params)
        data = json.loads(raw)
        results[topic] = data.get("esearchresult", {}).get("idlist", [])

    return results


def fetch_details(pmids: list[str], pmid_topics: dict[str, set[str]]) -> list[dict]:
    if not pmids:
        return []

    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
    }
    raw_xml = request_text(EFETCH_URL, params)
    root = ET.fromstring(raw_xml)

    today = dt.date.today()
    cutoff = today - dt.timedelta(days=MAX_AGE_DAYS)

    papers: list[dict] = []

    for pubmed_article in root.findall(".//PubmedArticle"):
        article = pubmed_article.find(".//Article")
        if article is None:
            continue

        pmid = (pubmed_article.findtext(".//PMID") or "").strip()
        if not pmid:
            continue

        pub_date_raw = parse_pub_date(article)
        publication_date_iso = normalize_pub_date(pub_date_raw)
        publication_date = to_iso_date(publication_date_iso)
        if publication_date and publication_date < cutoff:
            continue

        title = " ".join((article.findtext("ArticleTitle") or "").split())

        authors: list[str] = []
        for author in article.findall(".//AuthorList/Author"):
            last = (author.findtext("LastName") or "").strip()
            fore = (author.findtext("ForeName") or "").strip()
            collective = (author.findtext("CollectiveName") or "").strip()
            if collective:
                authors.append(collective)
            elif last or fore:
                authors.append(f"{fore} {last}".strip())

        abstract, methods, limitations = extract_abstract_sections(article)
        objective, results, conclusion = extract_core_sections(abstract)
        pmcid = extract_pmcid(pubmed_article)
        figure_urls = fetch_pmc_figure_urls(pmcid)

        papers.append(
            {
                "pmid": pmid,
                "title": title,
                "authors": authors,
                "publication_date": pub_date_raw,
                "publication_date_iso": publication_date_iso,
                "abstract": abstract,
                "objective": objective,
                "study_methods": methods,
                "methods": methods,
                "results": results,
                "conclusion": conclusion,
                "limitations": limitations,
                "topics": sorted(pmid_topics.get(pmid, [])),
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "pmcid": pmcid,
                "figure_urls": figure_urls,
            }
        )

    deduped: list[dict] = []
    seen: set[str] = set()
    for paper in papers:
        pmid = paper["pmid"]
        if pmid in seen:
            continue
        seen.add(pmid)
        deduped.append(paper)

    deduped.sort(key=lambda p: (p.get("publication_date_iso") or "", p.get("pmid") or ""), reverse=True)
    return deduped


def main() -> None:
    topic_pmids = fetch_pmids_by_topic()

    ordered_pmids: list[str] = []
    ordered_seen: set[str] = set()
    pmid_topics: dict[str, set[str]] = {}

    for topic, pmids in topic_pmids.items():
        for pmid in pmids:
            if pmid not in ordered_seen:
                ordered_seen.add(pmid)
                ordered_pmids.append(pmid)
            pmid_topics.setdefault(pmid, set()).add(topic)

    papers = fetch_details(ordered_pmids, pmid_topics)

    payload = {
        "updated_at": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "topics": TOPIC_QUERIES,
        "papers": papers,
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Saved {len(papers)} recent papers to {OUT_FILE}")


if __name__ == "__main__":
    main()
