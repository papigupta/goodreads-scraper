from flask import Flask, render_template_string
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

USER_ID = "33279125-prakhar-gupta"
BASE_URL = f"https://www.goodreads.com/review/list/{USER_ID}?shelf=read&page="
HEADERS = {"User-Agent": "Mozilla/5.0"}

def scrape_books():
    page = 1
    books = []

    while True:
        url = BASE_URL + str(page)
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.select('tr[id^="review_"]')

        if not rows:
            break

        for row in rows:
            title_tag = row.select_one('td.field.title .value a')
            author_tag = row.select_one('td.field.author .value a')
            image_tag = row.select_one('td.field.cover img')
            rating_tag = row.select_one('td.field.rating .value span.staticStars')
            review_tag = row.select_one('td.field.review .value span.greyText')

            books.append({
                "title": title_tag.text.strip() if title_tag else None,
                "author": author_tag.text.strip() if author_tag else None,
                "image": image_tag["src"] if image_tag else None,
                "rating": rating_tag["title"] if rating_tag and rating_tag.has_attr("title") else None,
                "review": review_tag.text.strip() if review_tag else None
            })

        page += 1

    return books

@app.route('/')
def home():
    books = scrape_books()
    return render_template_string("""
    <h1>📚 My Goodreads Shelf</h1>
    {% for book in books %}
        <div style="margin-bottom: 2rem;">
            <img src="{{ book.image }}" alt="Cover" style="float:left; margin-right: 1rem; height:100px;">
            <strong>{{ book.title }}</strong><br>
            <em>{{ book.author }}</em><br>
            ⭐ {{ book.rating }}<br>
            <p>{{ book.review }}</p>
            <div style="clear: both;"></div>
        </div>
    {% endfor %}
    """, books=books)

if __name__ == '__main__':
    app.run(debug=True)
