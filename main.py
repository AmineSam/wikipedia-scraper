from src.leaders_scraper import WikipediaScraper

if __name__ == "__main__":
    scraper = WikipediaScraper()
    data = scraper.scrape_all(
        countries=None,
        parallel=True,
        parallel_mode="threads",
        max_workers=12,
        show_progress=True,
    )
    scraper.save_all("leaders.json", "leaders.csv")
    print("Saved leaders.json and leaders.csv")