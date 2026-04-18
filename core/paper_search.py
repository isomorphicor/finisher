"""
独立模块：论文搜索。供方案阶段 S2 证据与文献、审阅人补充检索等使用。

支持源：
- Semantic Scholar（默认）：免费，无需 key；100 次/5 分钟；可选 SEMANTIC_SCHOLAR_API_KEY 提高限额。
- arXiv：免费，无 key；适合预印本。

用法:
  from core.paper_search import search_papers, format_papers_for_prompt

  results = search_papers("factor model stock return", limit=10, source="semantic_scholar")
  text = format_papers_for_prompt(results, max_chars=8000)
"""
from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

import requests


# Semantic Scholar 文档: https://api.semanticscholar.org/
SEMANTIC_SCHOLAR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_FIELDS = "paperId,title,abstract,year,authors,url,citationCount"
ARXIV_QUERY_URL = "http://export.arxiv.org/api/query"


@dataclass
class PaperHit:
    """单条论文命中，各源统一格式。"""
    title: str
    authors: str  # 已拼成 "Author1, Author2, ..."
    abstract: str
    url: str
    year: int | None = None
    citation_count: int | None = None
    source: str = "semantic_scholar"  # semantic_scholar | arxiv


def _semantic_scholar_search(
    query: str,
    limit: int = 10,
    timeout: int = 15,
    api_key: str | None = None,
) -> list[PaperHit]:
    """调用 Semantic Scholar 搜索 API。"""
    params: dict[str, Any] = {
        "query": query,
        "limit": min(limit, 100),
        "fields": SEMANTIC_SCHOLAR_FIELDS,
    }
    headers: dict[str, str] = {}
    if api_key:
        headers["x-api-key"] = api_key
    try:
        r = requests.get(
            SEMANTIC_SCHOLAR_SEARCH_URL,
            params=params,
            headers=headers or None,
            timeout=timeout,
        )
        r.raise_for_status()
        data = r.json()
    except requests.RequestException:
        return []  # 调用方可根据需要打 log
    items = data.get("data") or []
    out: list[PaperHit] = []
    for it in items:
        authors_list = it.get("authors") or []
        authors_str = ", ".join(
            a.get("name") or "" for a in authors_list if isinstance(a, dict)
        )
        out.append(
            PaperHit(
                title=(it.get("title") or "").strip(),
                authors=authors_str.strip(),
                abstract=(it.get("abstract") or "").strip(),
                url=it.get("url") or "",
                year=it.get("year"),
                citation_count=it.get("citationCount"),
                source="semantic_scholar",
            )
        )
    return out


def _arxiv_search(
    query: str,
    limit: int = 10,
    timeout: int = 15,
) -> list[PaperHit]:
    """调用 arXiv API 搜索（XML）。"""
    # arXiv 的 search_query 格式: all:keyword, ti:title, au:author 等
    search_query = f"all:{query}"
    params = {"search_query": search_query, "start": 0, "max_results": min(limit, 30)}
    try:
        r = requests.get(
            ARXIV_QUERY_URL,
            params=params,
            timeout=timeout,
        )
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except (requests.RequestException, ET.ParseError):
        return []
    # 命名空间
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    out: list[PaperHit] = []
    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        title = (title_el.text or "").replace("\n", " ").strip()
        summary_el = entry.find("atom:summary", ns)
        abstract = (summary_el.text or "").replace("\n", " ").strip()
        id_el = entry.find("atom:id", ns)
        url = (id_el.text or "").strip()
        authors = []
        for author in entry.findall("atom:author", ns):
            name_el = author.find("atom:name", ns)
            if name_el is not None and name_el.text:
                authors.append(name_el.text.strip())
        # 年份从 published 取
        pub_el = entry.find("atom:published", ns)
        year = None
        if pub_el is not None and pub_el.text:
            m = re.match(r"(\d{4})", pub_el.text)
            if m:
                year = int(m.group(1))
        out.append(
            PaperHit(
                title=title,
                authors=", ".join(authors),
                abstract=abstract,
                url=url,
                year=year,
                citation_count=None,
                source="arxiv",
            )
        )
    return out


def search_papers(
    query: str,
    limit: int = 10,
    source: str = "semantic_scholar",
    timeout: int = 15,
    api_key: str | None = None,
) -> list[PaperHit]:
    """
    搜索论文。返回统一格式的 PaperHit 列表。

    :param query: 检索词（短语或关键词）。
    :param limit: 最多返回条数（Semantic Scholar 单次最多 100，arXiv 单次最多 30）。
    :param source: "semantic_scholar" | "arxiv"。
    :param timeout: 单源请求超时秒数。
    :param api_key: Semantic Scholar API key（可选，提高限额）；也可设环境变量 SEMANTIC_SCHOLAR_API_KEY。
    """
    key = api_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if source == "arxiv":
        return _arxiv_search(query, limit=limit, timeout=timeout)
    return _semantic_scholar_search(
        query, limit=limit, timeout=timeout, api_key=key
    )


def search_papers_multi_source(
    query: str,
    limit_per_source: int = 5,
    timeout: int = 15,
    api_key: str | None = None,
) -> list[PaperHit]:
    """
    多源搜索：先 Semantic Scholar，再 arXiv，合并去重（按 title 简单归一化后去重）。
    """
    seen: set[str] = set()
    out: list[PaperHit] = []
    def _title_key(title: str) -> str:
        return (title or "").strip().lower()[:100]
    for hit in _semantic_scholar_search(
        query, limit=limit_per_source, timeout=timeout, api_key=api_key
    ):
        key = _title_key(hit.title)
        if key and key not in seen:
            seen.add(key)
            out.append(hit)
    for hit in _arxiv_search(query, limit=limit_per_source, timeout=timeout):
        key = _title_key(hit.title)
        if key and key not in seen:
            seen.add(key)
            out.append(hit)
    return out


def format_papers_for_prompt(
    papers: list[PaperHit],
    max_chars: int = 12000,
    include_abstract: bool = True,
) -> str:
    """
    将 PaperHit 列表格式化为可拼进 LLM prompt 的文本（如 S2 文献或审阅补充）。
    超过 max_chars 会截断并注明。
    """
    lines: list[str] = []
    for i, p in enumerate(papers, 1):
        block = [
            f"[{i}] {p.title}",
            f"    Authors: {p.authors or '(unknown)'}",
        ]
        if p.year is not None:
            block.append(f"    Year: {p.year}")
        if p.citation_count is not None:
            block.append(f"    Citations: {p.citation_count}")
        if include_abstract and p.abstract:
            block.append(f"    Abstract: {p.abstract[:800]}{'...' if len(p.abstract) > 800 else ''}")
        block.append(f"    URL: {p.url}")
        lines.append("\n".join(block))
    text = "\n\n".join(lines)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[已截断...]"
    return text
