from src.leaders_scraper import WikipediaScraper

def main():
    """Run the Wikipedia scraper to fetch leaders and save data."""
    scraper = WikipediaScraper()
    scraper.run()


if __name__ == "__main__":
    main()
