#!/usr/bin/env python3
"""
IEEE Official Website Crawler for IEEE AI Assistant RAG Knowledge Base.

Crawls official IEEE web pages with:
- Polite 1-second delay between requests
- robots.txt compliance
- URL deduplication and normalization
- HTML content extraction (stripping headers, footers, navbars, scripts, cookie banners)
- Markdown file storage in backend/data/web/
- Recording restricted / paywalled / WAF-gated links into backend/data/restricted_links.json
"""

import os
import re
import time
import json
import logging
from urllib.parse import urlparse, urljoin, urldefrag
from urllib.robotparser import RobotFileParser
from typing import Set, Dict, List, Any, Optional

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("IEEECrawler")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
WEB_DIR = os.path.join(DATA_DIR, "web")
RESTRICTED_LINKS_FILE = os.path.join(DATA_DIR, "restricted_links.json")

os.makedirs(WEB_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Primary seed URLs covering core IEEE topics
SEED_URLS = [
    "https://www.ieee.org/",
    "https://www.ieee.org/about/index.html",
    "https://www.ieee.org/about/ieee-history.html",
    "https://www.ieee.org/about/ethics/code-of-ethics.html",
    "https://www.ieee.org/membership/index.html",
    "https://www.ieee.org/membership/join/index.html",
    "https://www.ieee.org/membership/students/index.html",
    "https://www.ieee.org/membership/students/branches.html",
    "https://www.ieee.org/communities/societies/index.html",
    "https://www.ieee.org/communities/affinity-groups/index.html",
    "https://www.ieee.org/conferences/index.html",
    "https://standards.ieee.org/",
    "https://www.ieee.org/about/awards/index.html",
    "https://www.ieee.org/about/help/faqs.html",
    "https://students.ieee.org/",
    "https://students.ieee.org/student-branches/",
    "https://students.ieee.org/benefits/",
    "https://students.ieee.org/competitions/",
    "https://students.ieee.org/scholarships-and-awards/",
    "https://yp.ieee.org/",
    "https://yp.ieee.org/about/",
    "https://wie.ieee.org/",
    "https://wie.ieee.org/about/",
    "https://wie.ieee.org/membership/",
    "https://ethw.org/IEEE_History",
    "https://ethw.org/American_Institute_of_Electrical_Engineers_(AIEE)",
    "https://ethw.org/Institute_of_Radio_Engineers_(IRE)",
    "https://ethw.org/IEEE_Milestones_Program",
    "https://ethw.org/IEEE_Code_of_Ethics",
    "https://spectrum.ieee.org/about-us",
    "https://spectrum.ieee.org/ieee-fellows"
]

# Known restricted portals that should always be indexed as restricted links
KNOWN_RESTRICTED = [
    {
        "title": "IEEE Xplore Digital Library",
        "url": "https://ieeexplore.ieee.org/Xplore/home.jsp",
        "short_description": "IEEE Xplore provides discovery of and access to more than 6 million full-text research papers, journals, conference proceedings, technical standards, and educational courses.",
        "topic_keywords": ["research papers", "ieeexplore", "xplore", "journals", "conference proceedings", "transactions", "publications", "articles", "search papers", "download paper"]
    },
    {
        "title": "IEEE Standards Association (IEEE-SA)",
        "url": "https://standards.ieee.org/",
        "short_description": "The official consensus building organization that develops globally recognized market-driven IEEE standards including IEEE 802.3 (Ethernet) and IEEE 802.11 (Wi-Fi).",
        "topic_keywords": ["standards", "ieee standards", "802.3", "802.11", "ethernet", "wifi", "wi-fi", "ieee-sa", "standardization"]
    },
    {
        "title": "IEEE Collabratec",
        "url": "https://ieee-collabratec.ieee.org/",
        "short_description": "IEEE Collabratec is an integrated online community platform that connects global technology and engineering professionals by networking, authoring, and sharing research.",
        "topic_keywords": ["collabratec", "professional network", "community", "collaboration", "networking", "authoring"]
    },
    {
        "title": "IEEE Member Account Portal (Join & Renew)",
        "url": "https://www.ieee.org/membership/join/index.html",
        "short_description": "Official IEEE membership portal for creating accounts, joining IEEE, selecting societies, and renewing annual memberships.",
        "topic_keywords": ["join ieee", "renew membership", "account", "dues", "membership application", "sign up"]
    },
    {
        "title": "IEEE ResumeLab (Career Portal)",
        "url": "https://www.ieee.org/membership/resumelab.html",
        "short_description": "Exclusive member benefit providing resume builders, mock interviews, and career portfolio creation for IEEE students and professionals.",
        "topic_keywords": ["resumelab", "resume builder", "career tools", "mock interview", "job search"]
    }
]

# Priority keywords in URLs
PRIORITY_KEYWORDS = [
    "about", "history", "membership", "student", "branch", "society",
    "societies", "chapter", "wie", "young-professionals", "yp", "lmag",
    "conference", "standard", "scholarship", "award", "competition",
    "volunteer", "career", "benefit", "faq", "ethics", "aiee", "ire", "fellow"
]

ALLOWED_DOMAINS = {
    "ieee.org", "www.ieee.org", "students.ieee.org", "yp.ieee.org",
    "wie.ieee.org", "ethw.org", "spectrum.ieee.org", "standards.ieee.org"
}

class IEEECrawler:
    def __init__(self, max_pages: int = 300, max_depth: int = 2, delay_sec: float = 1.0):
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.delay_sec = delay_sec
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        })
        self.robot_parsers: Dict[str, RobotFileParser] = {}
        self.visited_urls: Set[str] = set()
        self.pages_crawled = 0
        self.pages_skipped = 0
        self.restricted_links: List[Dict[str, Any]] = list(KNOWN_RESTRICTED)
        self.restricted_urls: Set[str] = {item["url"] for item in KNOWN_RESTRICTED}

    def _can_fetch(self, url: str) -> bool:
        """Check robots.txt for domain."""
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain not in self.robot_parsers:
            rp = RobotFileParser()
            robots_url = f"{parsed.scheme}://{domain}/robots.txt"
            try:
                resp = self.session.get(robots_url, timeout=4)
                if resp.status_code == 200:
                    rp.parse(resp.text.splitlines())
                else:
                    rp.allow_all = True
            except Exception:
                rp.allow_all = True
            self.robot_parsers[domain] = rp

        rp = self.robot_parsers[domain]
        try:
            return rp.can_fetch("*", url)
        except Exception:
            return True

    def _normalize_url(self, url: str) -> str:
        """Strip fragment and normalize URL."""
        clean_url, _ = urldefrag(url)
        parsed = urlparse(clean_url)
        path = parsed.path or "/"
        return f"{parsed.scheme}://{parsed.netloc}{path}"

    def _is_priority_url(self, url: str) -> bool:
        lower = url.lower()
        return any(k in lower for k in PRIORITY_KEYWORDS)

    def _extract_main_text(self, soup: BeautifulSoup) -> str:
        """Remove unwanted elements and return clean prose."""
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "noscript", "svg", "form"]):
            tag.decompose()

        # Remove elements with banner, cookie, or navigation classes
        for tag in soup.find_all(True, {"class": re.compile(r"(cookie|nav|header|footer|menu|breadcrumb|social|share|modal)", re.I)}):
            tag.decompose()
        for tag in soup.find_all(True, {"id": re.compile(r"(cookie|nav|header|footer|menu|breadcrumb|social|share|modal)", re.I)}):
            tag.decompose()

        # Try to locate main content area
        main_content = (
            soup.find("main") or
            soup.find("article") or
            soup.find(id=re.compile(r"(content|main|article|body-content)", re.I)) or
            soup.find(class_=re.compile(r"(content|main|article|body-content)", re.I)) or
            soup.body
        )

        if not main_content:
            return ""

        text = main_content.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines()]
        clean_lines = [l for l in lines if l and len(l) > 3]
        return "\n\n".join(clean_lines)

    def _generate_slug(self, url: str) -> str:
        parsed = urlparse(url)
        slug = f"{parsed.netloc}_{parsed.path}".strip("/").replace("/", "_").replace(".", "_")
        slug = re.sub(r"[^a-zA-Z0-9_-]", "", slug)
        return slug[:100] or "index"

    def record_restricted_page(self, url: str, title: str, description: str, keywords: List[str]):
        if url in self.restricted_urls:
            return
        self.restricted_urls.add(url)
        self.restricted_links.append({
            "title": title or "IEEE Restricted Resource",
            "url": url,
            "short_description": description or "This IEEE page requires authentication, subscription, or has access restrictions.",
            "topic_keywords": keywords or ["ieee", "restricted", "official link"]
        })

    def crawl(self):
        logger.info(f"Starting IEEE crawl. Cap: {self.max_pages} pages, Max depth: {self.max_depth}")
        
        # Queue entries: (url, depth)
        queue: List[tuple] = [(u, 0) for u in SEED_URLS]

        while queue and self.pages_crawled < self.max_pages:
            url, depth = queue.pop(0)
            norm_url = self._normalize_url(url)

            if norm_url in self.visited_urls:
                continue
            self.visited_urls.add(norm_url)

            # Check domain
            parsed = urlparse(norm_url)
            domain = parsed.netloc.lower()
            if not any(d in domain for d in ALLOWED_DOMAINS):
                self.pages_skipped += 1
                continue

            # Respect robots.txt
            if not self._can_fetch(norm_url):
                logger.info(f"Robots.txt disallowed: {norm_url}")
                self.pages_skipped += 1
                continue

            # Rate limiting
            time.sleep(self.delay_sec)

            try:
                resp = self.session.get(norm_url, timeout=8, allow_redirects=True)
                final_url = resp.url

                # Check for paywalls / WAF / logins / client challenges
                if resp.status_code in [202, 401, 403, 429] or "x-amzn-waf-action" in resp.headers:
                    logger.warning(f"Restricted/WAF gated page ({resp.status_code}): {norm_url}")
                    self.record_restricted_page(
                        url=norm_url,
                        title=norm_url.split("/")[-1].replace(".html", "").replace("-", " ").title() or "IEEE Resource",
                        description="Official IEEE resource requiring direct browser viewing or IEEE authentication.",
                        keywords=[w for w in norm_url.split("/") if w]
                    )
                    self.pages_skipped += 1
                    continue

                if resp.status_code != 200:
                    logger.warning(f"HTTP {resp.status_code} for {norm_url}")
                    self.pages_skipped += 1
                    continue

                content_type = resp.headers.get("Content-Type", "").lower()
                if "text/html" not in content_type:
                    self.pages_skipped += 1
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                title = soup.title.string.strip() if soup.title and soup.title.string else "IEEE Web Page"
                title = re.sub(r"\s+", " ", title)

                # Check if page is login / gate page
                if "login" in norm_url.lower() or "signin" in norm_url.lower() or "cart" in norm_url.lower():
                    self.record_restricted_page(norm_url, title, "IEEE Member Login/Service Portal", ["login", "account", "membership"])
                    self.pages_skipped += 1
                    continue

                main_text = self._extract_main_text(soup)

                if len(main_text) < 150:
                    # Too short or empty content
                    self.pages_skipped += 1
                    continue

                # Save markdown file
                slug = self._generate_slug(norm_url)
                md_path = os.path.join(WEB_DIR, f"{slug}.md")
                md_content = f"# {title}\nSource URL: {norm_url}\n\n{main_text}\n"

                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(md_content)

                self.pages_crawled += 1
                logger.info(f"[{self.pages_crawled}/{self.max_pages}] Saved: {title[:40]} -> {md_path}")

                # Discover new links if depth allows
                if depth < self.max_depth:
                    new_links = []
                    for a in soup.find_all("a", href=True):
                        link = urljoin(final_url, a["href"])
                        clean_link = self._normalize_url(link)
                        p_link = urlparse(clean_link)
                        link_domain = p_link.netloc.lower()

                        if any(d in link_domain for d in ALLOWED_DOMAINS):
                            if clean_link not in self.visited_urls:
                                new_links.append(clean_link)

                    # Prioritize links matching IEEE keywords
                    priority_links = [l for l in new_links if self._is_priority_url(l)]
                    other_links = [l for l in new_links if not self._is_priority_url(l)]
                    
                    for pl in priority_links[:20]:
                        queue.append((pl, depth + 1))
                    for ol in other_links[:5]:
                        queue.append((ol, depth + 1))

            except Exception as e:
                logger.error(f"Error crawling {norm_url}: {e}")
                self.pages_skipped += 1

        # Write restricted links catalog
        with open(RESTRICTED_LINKS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.restricted_links, f, indent=2)

        print("\n================ CRAWL COMPLETE ================")
        print(f"Pages successfully crawled & saved: {self.pages_crawled}")
        print(f"Pages skipped: {self.pages_skipped}")
        print(f"Restricted / protected links saved: {len(self.restricted_links)}")
        print(f"Restricted links file: {RESTRICTED_LINKS_FILE}")
        print(f"Web documents directory: {WEB_DIR}")
        print("================================================\n")

if __name__ == "__main__":
    crawler = IEEECrawler(max_pages=150, max_depth=2, delay_sec=1.0)
    crawler.crawl()
