import requests
from bs4 import BeautifulSoup
import sys

def format_rating(rating):
    if not rating:
        return "N/R"  # Not Rated
    try:
        # Example rating string: "4 of 5 stars" or "liked it"
        if "stars" in rating:
            stars = rating.split()[0]  # Get first number
            return f"⭐ {stars}/5"
        elif "liked it" in rating:
            return "⭐ 3/5"
        elif "really liked it" in rating:
            return "⭐ 4/5"
        elif "it was amazing" in rating:
            return "⭐ 5/5"
        elif "it was ok" in rating:
            return "⭐ 2/5"
        elif "did not like it" in rating:
            return "⭐ 1/5"
        else:
            return "N/R"
    except:
        return "N/F"  # Not Found

def generate_html(books, output_path="index.html"):
    # Start building the HTML string
    html_parts = [
        '<!DOCTYPE html>',
        '<html>',
        '<head>',
        '    <meta charset="UTF-8">',
        '    <title>My Reading Journey</title>',
        '    <style>',
        '        body {',
        '            font-family: system-ui, -apple-system, sans-serif;',
        '            background-color: #f8f9fa;',
        '            margin: 0;',
        '            padding: 0;',
        '            min-height: 100vh;',
        '        }',
        '        .content {',
        '            position: relative;',
        '            z-index: 1;',
        '            max-width: 800px;',
        '            margin: 0 auto;',
        '            padding: 40px 20px;',
        '            background: rgba(255, 255, 255, 0.9);',
        '            backdrop-filter: blur(10px);',
        '            border-radius: 12px;',
        '            box-shadow: 0 8px 32px rgba(0,0,0,0.1);',
        '        }',
        '        .book {',
        '            background: white;',
        '            padding: 20px;',
        '            margin-bottom: 20px;',
        '            border-radius: 8px;',
        '            box-shadow: 0 2px 8px rgba(0,0,0,0.05);',
        '            transition: transform 0.2s;',
        '        }',
        '        .book:hover {',
        '            transform: translateY(-2px);',
        '        }',
        '        .book img {',
        '            height: 120px;',
        '            margin-right: 20px;',
        '            border-radius: 4px;',
        '            box-shadow: 0 2px 4px rgba(0,0,0,0.1);',
        '            float: left;',
        '        }',
        '        .stats {',
        '            font-size: 1.2em;',
        '            margin-bottom: 30px;',
        '            color: #1a1f36;',
        '        }',
        '        h1 {',
        '            margin: 0 0 30px 0;',
        '            color: #1a1f36;',
        '            font-size: 2.5em;',
        '        }',
        '        h2 {',
        '            margin: 0;',
        '            color: #1a1f36;',
        '            font-size: 1.2em;',
        '        }',
        '        .rating {',
        '            color: #6772e5;',
        '            font-weight: 500;',
        '        }',
        '    </style>',
        '</head>',
        '<body>',
        '    <div class="content">',
        '        <h1>📚 My Reading Journey</h1>',
        f'        <div class="stats"><strong>{len(books)}</strong> books read</div>',
    ]

    # Add each book to the HTML
    for book in books:
        book_html = [
            '        <div class="book">',
            f'            <img src="{book["image"] or ""}" alt="Cover">',
            f'            <h2>{book["title"]}</h2>',
            f'            <p><em>by {book["author"]}</em></p>',
            f'            <p class="rating">{format_rating(book["rating"])}</p>',
            f'            <p>{book["review"] or ""}</p>',
            '            <div style="clear: both;"></div>',
            '        </div>'
        ]
        html_parts.extend(book_html)

    # Close the HTML structure
    html_parts.extend([
        '    </div>',
        '</body>',
        '</html>'
    ])

    # Combine all parts into a single HTML string
    final_html = '\n'.join(html_parts)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_html)

    print(f"✅ HTML bookshelf saved to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("❌ Usage: python3 generate_html.py <Goodreads shelf URL>")
        sys.exit(1)

    base_url = sys.argv[1]
    headers = {"User-Agent": "Mozilla/5.0"}
    books = []
    page = 1

    while True:
        print(f"\n🔄 Scraping page {page}...")
        url = f"{base_url}&page={page}"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            print("❌ Failed to fetch page:", response.status_code)
            break

        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.select('tr[id^="review_"]')

        if not rows:
            print("✅ No more books found. Stopping.")
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

    generate_html(books)
