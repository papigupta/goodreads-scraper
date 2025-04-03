from flask import Flask, render_template_string, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route('/')
def index():
    return render_template_string("""
        <h1>📚 Create Your Goodreads Bookshelf</h1>
        <form action="/shelf" method="get">
            <label>Paste your Goodreads shelf URL:</label><br>
            <input type="text" name="url" style="width: 400px;">
            <button type="submit">Build Bookshelf</button>
        </form>
    """)

@app.route('/shelf')
def shelf():
    url = request.args.get('url')
    if not url or "goodreads.com/review/list/" not in url:
        return "❌ Invalid Goodreads URL"

    try:
        user_id = url.split("goodreads.com/review/list/")[1].split("?")[0]
    except IndexError:
        return "❌ Could not extract user ID"

    def scrape_books(user_id):
        BASE_URL = f"https://www.goodreads.com/review/list/{user_id}?shelf=read&page="
        HEADERS = {"User-Agent": "Mozilla/5.0"}

        page = 1
        books = []

        while True:
            full_url = BASE_URL + str(page)
            response = requests.get(full_url, headers=HEADERS, timeout=10)
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

    books = scrape_books(user_id)

    return render_template_string("""
        <h1>📚 Goodreads Shelf for {{ user_id }}</h1>
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
    """, books=books, user_id=user_id)

if __name__ == '__main__':
    app.run(debug=True)

