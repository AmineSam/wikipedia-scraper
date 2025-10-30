import requests, json, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from utils.helpers import _tqdm, _sanitize_text


class WikipediaScraper:
    """Scraper that retrieves country leaders and extracts Wikipedia intros."""

    def __init__(self):
        self.base_url = "https://country-leaders.onrender.com"
        self.country_endpoint = "/countries"
        self.leaders_endpoint = "/leaders"
        self.cookies_endpoint = "/cookie"
        self.leaders_data = {}
        self.cookie = self.refresh_cookie()
        self.session = requests.Session()

    def refresh_cookie(self):
        """Fetch a new cookie from the API."""
        return requests.get(self.base_url + self.cookies_endpoint).cookies

    def get_countries(self):
        """Return a list of country codes from the API."""
        resp = requests.get(self.base_url + self.country_endpoint, cookies=self.cookie)
        return resp.json() if resp.status_code == 200 else []

    def get_first_paragraph(self, wikipedia_url: str) -> str:
        """Extract and sanitize the first relevant paragraph from a Wikipedia page."""
        try:
            resp = self.session.get(
                wikipedia_url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=20,
            )
            if resp.status_code != 200:
                time.sleep(1)
                resp = self.session.get(
                    wikipedia_url,
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=20,
                )

            soup = BeautifulSoup(resp.text, "html.parser")

            # Iterate through <p> tags and pick the first valid paragraph
            for p in soup.find_all("p"):
                text = p.get_text(" ", strip=True)
                if len(text) > 40 and not any(
                    x in text.lower() for x in ["disambiguation", "refer to"]
                ):
                    return _sanitize_text(text)
        except Exception:
            pass
        return None

    def get_leaders(self, country: str):
        """Fetch leaders for a given country and add their Wikipedia intros."""
        try:
            url = self.base_url + self.leaders_endpoint
            resp = requests.get(url, cookies=self.cookie, params={"country": country})

            # Handle expired cookie
            if resp.status_code != 200:
                self.cookie = self.refresh_cookie()
                resp = requests.get(url, cookies=self.cookie, params={"country": country})

            leaders = resp.json()

            # Parallel fetching of Wikipedia intros
            with ThreadPoolExecutor(max_workers=8) as ex:
                futures = {
                    ex.submit(
                        self.get_first_paragraph, l.get("wikipedia_url")
                    ): l for l in leaders if l.get("wikipedia_url")
                }
                for fut in _tqdm(as_completed(futures), total=len(futures), desc=f"{country}"):
                    leader = futures[fut]
                    try:
                        leader["first_paragraph"] = fut.result()
                    except Exception:
                        leader["first_paragraph"] = None

            self.leaders_data[country] = leaders
        except Exception as e:
            print(f"Error processing {country}: {e}")

    def to_json_file(self, filepath="leaders.json"):
        """Save all collected data to a JSON file."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.leaders_data, f, ensure_ascii=False, indent=2)

    def to_csv_file(self, filepath="leaders.csv"):
        """Save all collected data to a CSV file."""
        import pandas as pd
        rows = [
            {"country": c, **l}
            for c, leaders in self.leaders_data.items()
            for l in leaders
        ]
        pd.DataFrame(rows).to_csv(filepath, index=False, encoding="utf-8")

    def run(self):
        """Fetch leaders for all countries and save results."""
        countries = self.get_countries()
        for country in _tqdm(countries, desc="Fetching leaders"):
            self.get_leaders(country)
        self.to_json_file()
        self.to_csv_file()
