import requests
from bs4 import BeautifulSoup

USER_ID = "33279125-prakhar-gupta"
BASE_URL = f"https://www.goodreads.com/review/list/{USER_ID}?shelf=read&page="
HEADERS = {"User-Agent": "Mozilla/5.0"}

page = 1
total_books = 0

while True:
    print(f"\n🔄 Scraping page {page}...")
    url = BASE_URL + str(page)
    response = requests.get(url, headers=HEADERS, timeout=10)
    print("✅ Page fetched successfully.")

    if response.status_code != 200:
        print("❌ Failed to fetch page:", response.status_code)
        break

    soup = BeautifulSoup(response.text, "html.parser")
    books = soup.select('tr[id^="review_"]')

    if not books:
        print("✅ No more books found. Stopping.")
        break

    for book in books:
        title_tag = book.select_one('td.field.title .value a')
        author_tag = book.select_one('td.field.author .value a')
        image_tag = book.select_one('td.field.cover img')
        rating_tag = book.select_one('td.field.rating .value span.staticStars')
        review_tag = book.select_one('td.field.review .value span.greyText')

        if title_tag and author_tag:
            title = title_tag.text.strip()
            author = author_tag.text.strip()
            image_url = image_tag['src'] if image_tag else None
            rating_text = rating_tag['title'] if rating_tag and rating_tag.has_attr('title') else None
            review = review_tag.text.strip() if review_tag else None

            print(f"📖 {title} by {author}")
            print(f"🖼️  Cover: {image_url}")
            print(f"⭐ Your Rating: {rating_text}")
            print(f"💬 Review: {review}\n")

    page += 1




