import requests
from bs4 import BeautifulSoup
from readability import Document
from markdownify import markdownify as md
import os

def get_page_content(url: str) -> str:
    """
    Fetches and extracts the main text content from a given URL using Firefox's Readability.
    
    Disables SSL verification if the APP_ENV environment variable is set to 'development' or 'local'.
    """
    app_env = os.getenv("APP_ENV", "production")
    verify_ssl = app_env not in ["development", "local"]

    if not verify_ssl:
        print(f"Warning: SSL verification is disabled for APP_ENV='{app_env}'.")

    try:
        response = requests.get(url, timeout=5, verify=verify_ssl)
        response.raise_for_status()  # Raise an exception for bad status codes

        doc = Document(response.text)
        summary_html = doc.summary()
        article_markdown = md(summary_html)
        print(f"Fetching URL Summary: {url}", article_markdown)

        return article_markdown
    except requests.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return ""