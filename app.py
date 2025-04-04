from flask import Flask, request, render_template_string, send_file, make_response, jsonify
import requests
from bs4 import BeautifulSoup
import os
from generate_html import generate_html
import threading

app = Flask(__name__)

# Simplified template with proper Jinja2 syntax
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Goodreads Bookshelf</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: auto; padding: 40px; }
        input[type="text"] { width: 100%; padding: 10px; font-size: 16px; }
        button { padding: 10px 20px; font-size: 16px; margin-top: 10px; }
        .message { margin-top: 20px; padding: 10px; border-radius: 4px; }
        .error { background-color: #ffe6e6; color: #cc0000; }
        .success { background-color: #e6ffe6; color: #006600; }
        .button-group { margin-top: 20px; }
        .button-group a { 
            text-decoration: none;
            padding: 10px 20px;
            margin-right: 10px;
            border-radius: 4px;
            color: white;
            background-color: #4CAF50;
        }
        #loader { display: none; margin-top: 20px; }
        #progress { font-family: monospace; margin-top: 10px; }
    </style>
</head>
<body>
    <h1>📚 Create Your Goodreads Bookshelf</h1>
    <form id="shelfForm" action="/shelf" method="get">
        <input type="text" name="url" required 
               placeholder="https://www.goodreads.com/review/list/12345678-username?shelf=read">
        <button type="submit">Generate Bookshelf</button>
    </form>
    
    <div id="loader">
        <div id="progress"></div>
        <div id="status"></div>
    </div>
    
    {% if content %}
    <div class="message {% if 'Error' in content %}error{% else %}success{% endif %}">
        {{ content|safe }}
        {% if not 'Error' in content %}
        <div class="button-group">
            <a href="/preview" target="_blank">Preview Bookshelf</a>
            <a href="/download" download="bookshelf.html">Download Bookshelf</a>
        </div>
        {% endif %}
    </div>
    {% endif %}
    
    <script>
        const form = document.getElementById('shelfForm');
        const loader = document.getElementById('loader');
        const progress = document.getElementById('progress');
        const status = document.getElementById('status');
        
        function generateProgressBar(percent) {
            const filled = '█'.repeat(Math.floor(percent / 10));
            const empty = '▒'.repeat(10 - Math.floor(percent / 10));
            return `${filled}${empty} ${percent}%`;
        }
        
        form.addEventListener('submit', (e) => {
            form.classList.add('loading');
            loader.style.display = 'block';
            
            // Start polling for progress
            const progressCheck = setInterval(() => {
                fetch('/progress')
                    .then(response => response.json())
                    .then(data => {
                        progress.textContent = generateProgressBar(data.progress);
                        status.textContent = `Scraping books (${data.books_processed}/${data.total_books})...`;
                        
                        if (data.complete) {
                            clearInterval(progressCheck);
                        }
                    });
            }, 500);
        });
    </script>
</body>
</html>
"""

# Global variables for progress tracking
progress_data = {
    "total_books": 0,
    "books_processed": 0,
    "complete": False
}

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/preview")
def preview():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "No bookshelf generated yet. Please generate one first."

@app.route("/download")
def download():
    if os.path.exists("index.html"):
        return send_file(
            "index.html",
            mimetype="text/html",
            as_attachment=True,
            download_name="bookshelf.html"
        )
    return "No bookshelf generated yet. Please generate one first."

@app.route("/progress")
def get_progress():
    return jsonify({
        "progress": int((progress_data["books_processed"] / progress_data["total_books"]) * 100) if progress_data["total_books"] > 0 else 0,
        "books_processed": progress_data["books_processed"],
        "total_books": progress_data["total_books"],
        "complete": progress_data["complete"]
    })

@app.route("/shelf")
def shelf():
    url = request.args.get("url", "").strip()
    
    if not url or "goodreads.com/review/list/" not in url:
        return render_template_string(HTML_TEMPLATE, 
            content="❌ Please enter a valid Goodreads shelf URL")
    
    try:
        # First, get total number of books
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        total_books_text = soup.select_one('.selectedShelf')
        if not total_books_text:
            return render_template_string(HTML_TEMPLATE, 
                content="❌ Could not find book count on shelf")
                
        total_books = int(''.join(filter(str.isdigit, total_books_text.text)))
        progress_data["total_books"] = total_books
        books = []
        page = 1
        books_processed = 0
        
        user_id = url.split("goodreads.com/review/list/")[1].split("?")[0]
        base_url = f"https://www.goodreads.com/review/list/{user_id}"
        
        while True:
            print(f"Scraping page {page}...")
            current_url = f"{base_url}?shelf=read&page={page}"
            response = requests.get(current_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            
            if response.status_code != 200:
                break
                
            soup = BeautifulSoup(response.text, "html.parser")
            rows = soup.select('tr[id^="review_"]')
            
            if not rows:
                break
                
            for row in rows:
                title_elem = row.select_one('td.field.title .value a')
                author_elem = row.select_one('td.field.author .value a')
                image_elem = row.select_one('td.field.cover img')
                rating_elem = row.select_one('td.field.rating .value span.staticStars')
                review_elem = row.select_one('td.field.review .value span.greyText')
                
                rating = None
                if rating_elem:
                    if rating_elem.has_attr('title'):
                        rating = rating_elem['title']
                    elif 'staticStar' in rating_elem.get('class', []):
                        # Alternative way to get rating from class names
                        rating_class = [c for c in rating_elem['class'] if c.startswith('p')]
                        if rating_class:
                            stars = rating_class[0][1]  # Gets number from 'p10', 'p20', etc.
                            rating = f"{int(stars)//10} of 5 stars"
                
                if title_elem and author_elem:
                    books.append({
                        "title": title_elem.text.strip(),
                        "author": author_elem.text.strip(),
                        "image": image_elem["src"] if image_elem else None,
                        "rating": rating,
                        "review": review_elem.text.strip() if review_elem else ""
                    })
                    books_processed += 1
                    progress_data["books_processed"] = books_processed
                    # Send SSE update
                    progress = int((books_processed / total_books) * 100)
                    print(f"Progress: {progress}%")
            
            page += 1
            
        if not books:
            return render_template_string(HTML_TEMPLATE, 
                content="❌ No books found on this shelf")
            
        generate_html(books)
        progress_data["complete"] = True
        return render_template_string(HTML_TEMPLATE,
            content="✅ Bookshelf generated successfully!")
        
    except Exception as e:
        return render_template_string(HTML_TEMPLATE, 
            content=f"❌ Error: {str(e)}")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
