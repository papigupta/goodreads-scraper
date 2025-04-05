# app.py - Final Code with Corrected Scroll Logic & Loader
# --- Imports ---
from flask import Flask, request, render_template_string, jsonify
import requests
from bs4 import BeautifulSoup
import os
import threading
import re
from urllib.parse import quote_plus
import io
import traceback

# --- Pillow Check ---
try:
    from PIL import Image, ImageStat
    print("Pillow loaded.")
except ImportError:
    print("WARNING: Pillow not found...")
    Image = None
    ImageStat = None

# --- Global Data ---
progress_data = {
    "total_books": 0, "books_processed": 0, "complete": False, "error": None
}

# --- Helper Functions (Copied from user code) ---
def get_edge_color(image_url, edge_width_percent=10):
    if not Image or not ImageStat or not io: return "#808080"
    try:
        response = requests.get(image_url, stream=True, timeout=10); response.raise_for_status()
        img = Image.open(io.BytesIO(response.content))
        if img.mode not in ('RGB', 'L'): img = img.convert('RGB')
        width = max(1, int(img.width * (edge_width_percent / 100))); edge = img.crop((0, 0, width, img.height))
        stat = ImageStat.Stat(edge); avg_color = (128,128,128)
        if hasattr(stat, 'mean') and stat.mean:
             avg_color_float = stat.mean
             if isinstance(avg_color_float, (list, tuple)) and len(avg_color_float) >= 1:
                 avg_color = tuple(int(c) for c in avg_color_float[:3])
                 if len(avg_color) == 1: avg_color = (avg_color[0],)*3
             elif isinstance(avg_color_float, (int, float)):
                 gray_val = int(avg_color_float); avg_color = (gray_val,)*3
        if len(avg_color) < 3: avg_color = (avg_color[0],)*3 if len(avg_color)>0 else (128,)*3
        hex_color = "#{:02x}{:02x}{:02x}".format(*avg_color[:3])
        return hex_color
    except Exception as e: print(f"Warn: Img process fail {image_url.split('/')[-1]} {e}"); return "#808080"

def get_books_from_shelf(url):
    # Copied from user code - assumed correct by user
    global progress_data; progress_data = {"total_books":0,"books_processed":0,"complete":False,"error":None}; books=[]; headers={"User-Agent":"Mozilla/5.0"}
    try:
        page = 1
        # Add initial total book count estimate here if desired
        # Fetch initial page outside loop to get total?
        initial_response = requests.get(f"{url}&page=1", headers=headers, timeout=15); initial_response.raise_for_status()
        initial_soup = BeautifulSoup(initial_response.text, "html.parser"); count_elem = initial_soup.select_one('#shelfHeader .greyText'); total_books = 0
        if count_elem and 'books)' in count_elem.text: match = re.search(r'of (\d+) books', count_elem.text); total_books = int(match.group(1)) if match else 0
        if total_books == 0: count_elem_fallback = initial_soup.select_one('.selectedShelf'); total_books = int(''.join(filter(str.isdigit, count_elem_fallback.text))) if count_elem_fallback else 0
        if total_books == 0: print("Warning: Could not determine total book count."); total_books = 1 # Avoid zero division later
        progress_data["total_books"] = total_books # Set total for progress %

        while True:
            current_url = f"{url}&page={page}";
            print(f"Scraping page {page}: ...{current_url[-60:]}")
            if page == 1: # Use already fetched response for page 1
                response = initial_response
                soup = initial_soup
            else: # Fetch subsequent pages
                try: response = requests.get(current_url, headers=headers, timeout=10); response.raise_for_status()
                except requests.exceptions.RequestException as page_err: print(f"Error fetching page {page}: {page_err}."); progress_data["error"] = f"Warn: Failed page {page}."; break
                soup = BeautifulSoup(response.text, "html.parser")

            rows = soup.select('tr[id^="review_"]')
            if not rows:
                 # Check if it was the first page and still no rows
                 if page == 1: print("No book rows found on first page. Shelf empty or selectors wrong?")
                 else: print(f"No more rows found on page {page}.")
                 break # Stop if no rows

            for row in rows:
                title_elem=row.select_one('td.field.title .value a'); author_elem=row.select_one('td.field.author .value a'); image_elem=row.select_one('td.field.cover img'); rating_elem=row.select_one('td.field.rating .value span.staticStars'); review_elem=row.select_one('td.field.review .value span.greyText')
                if title_elem and author_elem:
                    raw_image_url = image_elem.get("src") if image_elem else ""; high_res_image_url = raw_image_url
                    if raw_image_url: high_res_image_url = re.sub(r'\._S[XY]?\d+_?\.', '.', raw_image_url)
                    spine_color = get_edge_color(high_res_image_url) if image_elem and high_res_image_url and Image else "#808080"
                    # Add rating/review back if needed
                    books.append({ "title": title_elem.text.strip(), "author": author_elem.text.strip(), "image": high_res_image_url, "spine_color": spine_color })
                    progress_data["books_processed"] = len(books) # Update count inside loop
            page += 1
        if not books and not progress_data.get("error"): progress_data["error"] = "No books found."
        progress_data["total_books"] = progress_data.get("books_processed", 0) # Ensure total matches processed if scrape ends early
        progress_data["complete"] = True; print(f"Scraping finished. Found: {len(books)}"); return books
    except Exception as e: print(f"Scraping error: {e}"); traceback.print_exc(); progress_data["error"] = str(e); progress_data["complete"] = True; return None


# --- Flask App ---
app = Flask(__name__)

# --- HTML Template ---
THREE_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"> <meta name="viewport" content="width=device-width, initial-scale=1.0"> <title>My 3D Bookshelf</title>
    <style> body { margin: 0; background-color: #090909; color: #eee; font-family: system-ui, sans-serif; overflow-y: scroll; } #info { display: none; } #loading-message, #input-container { position: fixed; top: 50%; left: 50%; transform: translate(-50%,-50%); background: #fff; color: #333; padding: 30px; border-radius: 8px; box-shadow: 0 5px 15px rgba(0,0,0,.2); text-align: center; z-index: 200; min-width: 250px; } #input-container h2 { margin-top: 0; color: #333; } #input-container input[type=text] { width: calc(100% - 22px); padding: 10px; margin-bottom: 15px; border: 1px solid #ccc; border-radius: 4px; font-size: 1em;} #input-container button { padding: 10px 20px; background-color: #4CAF50; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 1em;} #input-container button:hover { background-color: #45a049; } #canvas-container { width: 100%; height: 100%; position: fixed; top: 0; left: 0; z-index: 1; } canvas { display: block; } /* Loader Styles */ #progress-bar { width: 80%; background-color: #e0e0e0; border-radius: 4px; overflow: hidden; margin: 10px auto 5px auto;} #progress-fill { height: 15px; background-color: #4CAF50; width: 0%; transition: width 0.3s ease; text-align: center; color: white; line-height: 15px; font-size: 0.8em;} #status-text { font-family: monospace; margin-top: 10px; font-size: 0.9em; color: #555;} </style>
</head>
<body>
    <div id="info"> <h1>My 3D Reading Journey</h1> <div id="stats"></div> </div>
    <div id="input-container"> <h2>Enter Goodreads Shelf URL</h2> <form id="shelfForm"> <input type="text" id="shelfUrl" name="url" required placeholder="https://www.goodreads.com/review/list/..."> <button type="submit">Load Bookshelf</button> </form> </div>
    <div id="loading-message" style="display:none">
         <div id="status-text">Fetching data...</div>
         <div id="progress-bar"><div id="progress-fill">0%</div></div>
    </div>
    <div id="canvas-container"></div>
    <script type="importmap"> { "imports": { "three": "https://unpkg.com/three@0.163.0/build/three.module.js", "three/addons/": "https://unpkg.com/three@0.163.0/examples/jsm/" } } </script>

    <script type="module">
        import * as THREE from 'three';
        // No OrbitControls

        // --- Constants ---
        const BOOK_DEFAULTS = { HEIGHT: 2.0, WIDTH: 1.35, THICKNESS: 0.25 }; const PAGE_COLOR = 0xf5f5dc;
        const BOOK_SPACING = -1; // User's overlap value
        const TARGET_ROTATION_X = THREE.MathUtils.degToRad(-90); const TARGET_ROTATION_Y = THREE.MathUtils.degToRad(88);
        const CAMERA_Z = 10; const CAMERA_Y = 1; const CAMERA_FOV = 35;

        // --- DOM Elements ---
        const inputContainer = document.getElementById('input-container'); const loadingMessage = document.getElementById('loading-message'); const shelfForm = document.getElementById('shelfForm'); const shelfUrlInput = document.getElementById('shelfUrl'); const statsDiv = document.getElementById('stats'); const canvasContainer = document.getElementById('canvas-container');
        const progressBarFill = document.getElementById('progress-fill'); const statusText = document.getElementById('status-text');

        // --- Three.js Variables ---
        let scene, camera, renderer; let bookData = []; const textureLoader = new THREE.TextureLoader(); const booksGroup = new THREE.Group();
        let currentScrollY = window.scrollY; let targetGroupY = 0; let animationFrameId = null;
        let progressIntervalId = null;

        // --- Init ---
        function main() { setupEventHandlers(); showInputForm(); }
        function setupEventHandlers() { shelfForm.addEventListener('submit', handleUrlSubmit); window.addEventListener('resize', onWindowResize); window.addEventListener('scroll', onWindowScroll); }

        // --- Handle Form Submit ---
        async function handleUrlSubmit(event) {
             event.preventDefault(); const shelfUrl = shelfUrlInput.value.trim(); if (!shelfUrl || !shelfUrl.includes('goodreads.com/review/list/')) { alert('Error: Invalid URL.'); return; } console.log("Shelf URL:", shelfUrl); inputContainer.style.display = 'none'; loadingMessage.style.display = 'block';
             statusText.textContent = "Fetching data..."; progressBarFill.style.width = '0%'; progressBarFill.textContent = '0%';
             if (progressIntervalId) clearInterval(progressIntervalId);
             progressIntervalId = setInterval(updateProgress, 1000); // Start polling
             try { const apiUrl = `/get_books?url=${encodeURIComponent(shelfUrl)}`; console.log("Fetching from:", apiUrl); const response = await fetch(apiUrl); let errorMsg = `HTTP error ${response.status}`; if (!response.ok) { try { const d=await response.json(); errorMsg = d.error||errorMsg; } catch (e) {} throw new Error(errorMsg); } const data = await response.json(); console.log("Received data:", data);
                if (progressIntervalId) clearInterval(progressIntervalId); progressIntervalId = null;// Stop polling
                if (data.error && (!data.books || data.books.length === 0)) { throw new Error(data.error); } bookData = data.books || [];
                statusText.textContent = `${bookData.length} books found. Building scene...`; progressBarFill.style.width = '100%'; progressBarFill.textContent = '100%';
                if (!scene) { initThreeJS(); } populateScene();
             } catch (error) { console.error("Fetch error:", error); alert(`Error: ${error.message}`); statusText.textContent = `Error: ${error.message}`;
                if (progressIntervalId) clearInterval(progressIntervalId); progressIntervalId = null; // Stop polling on error
                loadingMessage.style.display = 'block';
             }
        }

        // --- updateProgress Function ---
        async function updateProgress() { /* ... (Identical to last correct version) ... */
             try { const response = await fetch('/progress'); if (!response.ok) { console.warn("Progress check failed:", response.status); return; } const data = await response.json(); const percent = data.progress || 0; if(progressBarFill){ progressBarFill.style.width = percent + '%'; progressBarFill.textContent = percent + '%'; } if(statusText){ if (!data.complete && !data.error) { statusText.textContent = `Processing... (${data.books_processed}/${data.total_books})`; } } if (data.complete || data.error) { console.log("Progress poll end."); if (progressIntervalId) clearInterval(progressIntervalId); progressIntervalId = null; if(progressBarFill){ progressBarFill.style.width = '100%'; progressBarFill.textContent = '100%';} if(statusText && data.error){ statusText.textContent = `Error: ${data.error}`; } else if(statusText && data.complete) { statusText.textContent = "Processing complete."; } } } catch (error) { console.warn("Error fetching progress:", error); }
        }

        // --- Three.js Scene Initialization ---
        function initThreeJS() { /* ... (Identical) ... */
            console.log("Initializing Three.js scene..."); scene = new THREE.Scene(); scene.background = new THREE.Color(0x090909); const aspect = window.innerWidth / window.innerHeight; camera = new THREE.PerspectiveCamera(CAMERA_FOV, aspect, 0.1, 1000); camera.position.set(0, CAMERA_Y, CAMERA_Z); camera.lookAt(0, 0, 0); renderer = new THREE.WebGLRenderer({ antialias: true }); renderer.setSize(window.innerWidth, window.innerHeight); renderer.setPixelRatio(window.devicePixelRatio); canvasContainer.appendChild(renderer.domElement); const ambientLight = new THREE.AmbientLight(0xffffff, 0.7); scene.add(ambientLight); const keyLight = new THREE.DirectionalLight(0xffffff, 0.8); keyLight.position.set(-8, 10, 8); scene.add(keyLight); const fillLight = new THREE.DirectionalLight(0xffffff, 0.3); fillLight.position.set(8, 2, 6); scene.add(fillLight); scene.add(booksGroup); window.addEventListener('resize', onWindowResize); if (!animationFrameId) { animate(); console.log("Animation loop started."); }
        }

        // --- Populate Scene with Books (Corrected Scroll Init) ---
        function populateScene() {
             while(booksGroup.children.length > 0){ booksGroup.remove(booksGroup.children[0]); } console.log(`Creating ${bookData.length} book meshes...`);
             const totalStackHeight = bookData.length * (BOOK_DEFAULTS.HEIGHT + BOOK_SPACING) - BOOK_SPACING;
             const startY = totalStackHeight / 2 - BOOK_DEFAULTS.HEIGHT / 2; // Top book's center relative to group origin
             const initialGroupY = -startY; // Group offset to bring top book near y=0 world space
             bookData.forEach((book, index) => { const bookMesh = createBookMesh(book); bookMesh.position.y = startY - index * (BOOK_DEFAULTS.HEIGHT + BOOK_SPACING); booksGroup.add(bookMesh); });
             console.log("Finished adding meshes."); loadingMessage.style.display = 'none';
             document.body.style.height = `${totalStackHeight * 50}px`;
             // --- Apply Corrected Initial Scroll Position ---
             targetGroupY = initialGroupY; // Set target
             booksGroup.position.y = initialGroupY; // Set position directly
             // ---
             onWindowScroll(); // Call once to potentially adjust based on initial scrollY
         }

        // --- Create Single Book Mesh ---
        function createBookMesh(book) { /* ... (Identical) ... */
             const geometry = new THREE.BoxGeometry(BOOK_DEFAULTS.WIDTH, BOOK_DEFAULTS.HEIGHT, BOOK_DEFAULTS.THICKNESS); const pageMaterial = new THREE.MeshStandardMaterial({ color: PAGE_COLOR, roughness: 0.95, metalness: 0.05 }); const spineMaterial = new THREE.MeshStandardMaterial({ color: book.spine_color || 0x808080, roughness: 0.8, metalness: 0.1 }); const coverMaterial = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.8, metalness: 0.1 }); if (book.image) { textureLoader.load( book.image, (texture) => { texture.colorSpace = THREE.SRGBColorSpace; const imgAspect = texture.image.naturalWidth / texture.image.naturalHeight; const geomAspect = BOOK_DEFAULTS.WIDTH / BOOK_DEFAULTS.HEIGHT; texture.repeat.set(1, geomAspect / imgAspect); texture.offset.set(0, (1 - texture.repeat.y) / 2); coverMaterial.map = texture; coverMaterial.needsUpdate = true; }, undefined, (err) => { console.error(`Err texture ${book.title}:`, err); } ); } const materials = [ pageMaterial, spineMaterial, pageMaterial, pageMaterial, coverMaterial, pageMaterial ]; const mesh = new THREE.Mesh(geometry, materials); mesh.rotation.order = 'YXZ'; mesh.rotation.x = TARGET_ROTATION_X; mesh.rotation.y = TARGET_ROTATION_Y; return mesh;
         }

        // --- Handle Scrolling (Corrected Logic) ---
        function onWindowScroll() {
             currentScrollY = window.scrollY;
             const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
             const scrollRatio = maxScroll > 0 ? currentScrollY / maxScroll : 0;
             // Recalculate total height and starting offset
             const totalStackHeight = bookData.length * (BOOK_DEFAULTS.HEIGHT + BOOK_SPACING) - BOOK_SPACING;
             const startY = totalStackHeight / 2 - BOOK_DEFAULTS.HEIGHT / 2;
             const initialGroupY = -startY; // Group Y when scroll=0
             // Define total travel distance
             const totalTravelDistance = Math.max(0, bookData.length - 1) * (BOOK_DEFAULTS.HEIGHT + BOOK_SPACING);
             // Set target: start offset + upward movement based on scroll
             targetGroupY = initialGroupY + (scrollRatio * totalTravelDistance);
         }
        // --- Render Loop ---
        function animate() {
             animationFrameId = requestAnimationFrame(animate);
             booksGroup.position.y += (targetGroupY - booksGroup.position.y) * 0.1; // Lerp scroll
             renderer.render(scene, camera);
         }
        // --- Resize Handler ---
        function onWindowResize() {
            if (!camera || !renderer) return; // Safety check
             camera.aspect = window.innerWidth / window.innerHeight; camera.updateProjectionMatrix();
             renderer.setSize(window.innerWidth, window.innerHeight);
             onWindowScroll(); // Recalculate scroll
         }
         function showInputForm(){ loadingMessage.style.display = 'none'; inputContainer.style.display = 'block'; }
        // --- Initial State ---
        main(); // Start

    </script>
</body>
</html>'''

# --- Flask Routes ---
@app.route("/")
def index():
    global progress_data; progress_data = {"total_books":0,"books_processed":0,"complete":False,"error":None}
    return render_template_string(THREE_TEMPLATE)

@app.route("/get_books")
def get_books_api():
    url = request.args.get("url", "").strip()
    if not url: return jsonify({"error": "Missing URL parameter"}), 400
    books_data = get_books_from_shelf(url)
    error_message = progress_data.get("error")
    if error_message:
        status_code = 500 if ("Failed page 1" in error_message or "fetch" in error_message) and not books_data else 200
        return jsonify({"error": error_message,"books": books_data or []}), status_code
    elif not books_data: return jsonify({"error": "No books found"}), 404
    else: return jsonify({"books": books_data,"total_found": len(books_data)})

# --- ADDED /progress Route ---
@app.route("/progress")
def get_progress():
    total = progress_data.get("total_books", 0)
    processed = progress_data.get("books_processed", 0)
    percent = min(100, int((processed / total) * 100)) if total > 0 else 0
    return jsonify({ "progress": percent, "books_processed": processed, "total_books": total, "complete": progress_data.get("complete", False), "error": progress_data.get("error") })

# --- Main Execution ---
if __name__ == "__main__":
    app.run(debug=True, port=5000)