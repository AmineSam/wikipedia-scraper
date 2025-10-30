import json
import re
import pandas as pd
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Iterable


def _has_tqdm():
    try:
        import tqdm  # noqa: F401
        return True
    except Exception:
        return False


def _tqdm(iterable: Iterable, **kwargs):
    if _has_tqdm():
        from tqdm import tqdm
        return tqdm(iterable, **kwargs)
    return iterable


class WikipediaScraper:
    def __init__(self):
        self.base_url = "https://country-leaders.onrender.com"
        self.country_endpoint = "/countries"
        self.leaders_endpoint = "/leaders"
        self.cookies_endpoint = "/cookie"
        self.leaders_data: Dict[str, List[Dict[str, Any]]] = {}
        self.cookie: Optional[requests.cookies.RequestsCookieJar] = None
        self.session: Optional[requests.Session] = None

    # -----------------------------
    # Cookie / Session
    # -----------------------------
    def _ensure_session(self) -> requests.Session:
        if self.session is None:
            self.session = requests.Session()
        return self.session

    def refresh_cookie(self) -> requests.cookies.RequestsCookieJar:
        url = f"{self.base_url}{self.cookies_endpoint}"
        resp = requests.get(url)
        resp.raise_for_status()
        self.cookie = resp.cookies
        return self.cookie

    # -----------------------------
    # API Access
    # -----------------------------
    def get_countries(self) -> List[str]:
        if self.cookie is None:
            self.refresh_cookie()
        url = f"{self.base_url}{self.country_endpoint}"
        resp = requests.get(url, cookies=self.cookie)
        if resp.status_code != 200:
            self.refresh_cookie()
            resp = requests.get(url, cookies=self.cookie)
        resp.raise_for_status()
        return resp.json()

    def _get_leaders_raw(self, country: str) -> List[Dict[str, Any]]:
        if self.cookie is None:
            self.refresh_cookie()
        url = f"{self.base_url}{self.leaders_endpoint}"
        params = {"country": country}
        resp = requests.get(url, cookies=self.cookie, params=params, timeout=20)

        if resp.status_code != 200 or (resp.text and "cookie" in resp.text.lower()):
            self.refresh_cookie()
            resp = requests.get(url, cookies=self.cookie, params=params, timeout=20)

        resp.raise_for_status()
        return resp.json()

    # -----------------------------
    # Wikipedia helpers
    # -----------------------------
    @staticmethod
    def _sanitize_text(raw: str) -> str:
        text = raw
        text = re.sub(r"\[[^\]]*\]", "", text)
        text = re.sub(r"\((?:citation needed|clarification needed|who\?)\)", "", text, flags=re.IGNORECASE)
        text = text.replace("\xa0", " ")
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"\s+([,.;:])", r"\1", text)
        return text

    def get_first_paragraph(self, wikipedia_url: Optional[str]) -> Optional[str]:
        if not wikipedia_url:
            return None
        s = self._ensure_session()
        try:
            resp = s.get(wikipedia_url, headers={'User-Agent': 'Mozilla/5.0'})
            resp.raise_for_status()
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")
            for p in soup.find_all("p"):
                text = p.get_text(" ", strip=True)
                if len(text) >= 60:
                    return self._sanitize_text(text)
            return None
        except Exception:
            return None

    # -----------------------------
    # Enrichment
    # -----------------------------
    def enrich_country(
        self,
        country: str,
        parallel: bool = True,
        parallel_mode: str = "threads",
        max_workers: int = 8,
        show_progress: bool = True,
    ) -> None:
        leaders = self._get_leaders_raw(country)

        def _fetch_enriched(leader: Dict[str, Any]) -> Dict[str, Any]:
            wiki_url = leader.get("wikipedia_url")
            leader = dict(leader)
            leader["first_paragraph"] = self.get_first_paragraph(wiki_url) if wiki_url else None
            return leader

        if not parallel or parallel_mode == "sequential":
            it = leaders
            if show_progress:
                it = _tqdm(it, total=len(leaders), desc=f"{country}: enrich")
            enriched = [_fetch_enriched(ld) for ld in it]
        else:
            Executor = ThreadPoolExecutor
            if parallel_mode == "processes":
                Executor = ProcessPoolExecutor

            enriched = []
            with Executor(max_workers=max_workers) as ex:
                futures = {ex.submit(_fetch_enriched, ld): ld for ld in leaders}
                iterator = as_completed(futures)
                if show_progress:
                    iterator = _tqdm(iterator, total=len(futures), desc=f"{country}: enrich")
                for fut in iterator:
                    try:
                        res = fut.result()
                        enriched.append(res)
                    except Exception:
                        pass

        self.leaders_data[country] = enriched

    def scrape_all(
        self,
        countries: Optional[List[str]] = None,
        parallel: bool = True,
        parallel_mode: str = "threads",
        max_workers: int = 8,
        show_progress: bool = True,
    ) -> Dict[str, List[Dict[str, Any]]]:
        if countries is None:
            countries = self.get_countries()

        for c in _tqdm(countries, desc="Countries", total=len(countries)) if show_progress else countries:
            try:
                self.enrich_country(
                    c,
                    parallel=parallel,
                    parallel_mode=parallel_mode,
                    max_workers=max_workers,
                    show_progress=show_progress,
                )
            except Exception:
                continue

        return self.leaders_data

    # -----------------------------
    # Exports
    # -----------------------------
    def to_json_file(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.leaders_data, f, ensure_ascii=False, indent=2)

    def to_csv_file(self, filepath: str) -> None:
        rows: List[Dict[str, Any]] = []
        for country, leaders in self.leaders_data.items():
            for leader in leaders:
                row = {"country": country}
                row.update(leader)
                rows.append(row)
        pd.DataFrame(rows).to_csv(filepath, index=False, encoding="utf-8")

    def save_all(self, json_path: str = "leaders.json", csv_path: str = "leaders.csv") -> None:
        self.to_json_file(json_path)
        self.to_csv_file(csv_path)