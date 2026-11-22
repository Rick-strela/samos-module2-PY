import csv
import re
from pathlib import Path
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup


def check_robots_permission(robots_url: str, target_url: str, agent: str = "*") -> bool:
    if not robots_url.startswith(("http://", "https://")):
        return True

    parser = RobotFileParser()
    parser.set_url(robots_url)
    try:
        parser.read()
        return parser.can_fetch(agent, target_url)
    except Exception:
        return True


def parse_price(raw_price: str) -> float:
    cleaned = re.sub(r"[^\d.,]", "", raw_price).replace(",", ".").strip()
    return float(cleaned) if cleaned else 0.0


def scrape_catalog(html_path: Path) -> tuple[list[dict[str, str | float]], list[str]]:
    html_content = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html_content, "lxml")

    products: list[dict[str, str | float]] = []
    cards = soup.select(".product-card")

    for card in cards:
        product_id = str(card.get("data-id", "")).strip()

        title_el = card.select_one(".product-title")
        author_el = card.select_one(".product-author")
        price_el = card.select_one(".price-value")
        stock_el = card.select_one(".stock-status")
        link_el = card.select_one("a.product-link")

        title = title_el.get_text(strip=True) if title_el else ""
        author = author_el.get_text(strip=True) if author_el else ""
        price_uah = parse_price(price_el.get_text(strip=True)) if price_el else 0.0
        stock_status = stock_el.get_text(strip=True) if stock_el else ""
        relative_url = str(link_el.get("href", "")).strip() if link_el else ""

        products.append(
            {
                "product_id": product_id,
                "title": title,
                "author": author,
                "price_uah": price_uah,
                "stock_status": stock_status,
                "relative_url": relative_url,
            }
        )

    visited_urls: set[str] = set()
    pagination_links: list[str] = []
    max_depth: int = 3

    for idx, link in enumerate(soup.select(".pagination a.page-link"), start=1):
        if len(visited_urls) >= max_depth:
            break
        href = str(link.get("href", "")).strip()
        if href and href not in visited_urls:
            visited_urls.add(href)
            pagination_links.append(href)

    return products, pagination_links


def save_to_csv(records: list[dict[str, str | float]], output_csv: Path) -> None:
    fieldnames = [
        "product_id",
        "title",
        "author",
        "price_uah",
        "stock_status",
        "relative_url",
    ]
    with output_csv.open(mode="w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    html_file = base_dir / "module2_mock_catalog.html"
    csv_file = base_dir / "catalog_scraped.csv"
    report_file = base_dir / "report_scraped.txt"

    allowed = check_robots_permission(
        robots_url="local://robots.txt",
        target_url=str(html_file),
    )

    if not allowed:
        print("Парсинг заборонено правилами robots.txt")
        return

    products, pagination_links = scrape_catalog(html_file)
    save_to_csv(products, csv_file)

    report_lines = [
        "=== ЗВІТ ПРО ПАРСИНГ КАТАЛОГУ ===",
        f"Дозвіл robots.txt (fallback): {allowed}",
        f"Кількість зібраних позицій: {len(products)}",
        f"Виявлені унікальні лінки пагінації ({len(pagination_links)}): {pagination_links}",
        "",
        "Зібрані товари:",
    ]
    for item in products:
        report_lines.append(
            f"- [{item['product_id']}] {item['title']} ({item['author']}) — "
            f"{item['price_uah']:.2f} грн | {item['stock_status']} | {item['relative_url']}"
        )

    report_text = "\n".join(report_lines)
    print(report_text)
    report_file.write_text(report_text, encoding="utf-8")


if __name__ == "__main__":
    main()