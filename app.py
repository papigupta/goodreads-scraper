# app.py - Adding Spine Text via Canvas Texture
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

# --- Helper Functions (From User's Code) ---
def get_edge_color(image_url, edge_width_percent=10):
    # ... (Code Provided By User - Assumed OK) ...
    if not Image or not ImageStat or not io: return "#808080"
    try:
        response = requests.get(image_url, stream=True, timeout=10); response.raise_for_status()
        img = Image.open(io.BytesIO(response.content))
        if img.mode not in ('RGB', 'L'): img = img.convert('RGB')
        img_width, img_height = img.size
        if img_width <= 1 or img_height <= 0: return "#808080"
        width = max(1, int(img.width * (edge_width_percent / 100)))
        if width > img_width: width = img_width
        edge = img.crop((0, 0, width, img.height)); stat = ImageStat.Stat(edge)
        avg_color = (128,128,128);
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
    # ... (Code Provided By User - Including Author/Publisher Scraping) ...
    global progress_data; progress_data = {"total_books":0,"books_processed":0,"complete":False,"error":None}; books=[]; headers={"User-Agent":"Mozilla/5.0"}
    try:
        page = 1
        initial_response = requests.get(f"{url}&page=1", headers=headers, timeout=15); initial_response.raise_for_status()
        initial_soup = BeautifulSoup(initial_response.text, "html.parser"); count_elem = initial_soup.select_one('#shelfHeader .greyText'); total_books = 0
        if count_elem and 'books)' in count_elem.text: match = re.search(r'of (\d+) books', count_elem.text); total_books = int(match.group(1)) if match else 0
        if total_books == 0: count_elem_fallback = initial_soup.select_one('.selectedShelf'); total_books = int(''.join(filter(str.isdigit, count_elem_fallback.text))) if count_elem_fallback else 0
        if total_books == 0: total_books = 1
        progress_data["total_books"] = total_books
        while True:
            current_url = f"{url}&page={page}";
            print(f"Scraping page {page}...")
            if page == 1: response = initial_response; soup = initial_soup
            else:
                try: response = requests.get(current_url, headers=headers, timeout=10); response.raise_for_status()
                except requests.exceptions.RequestException as page_err: print(f"Error page {page}: {page_err}."); progress_data["error"] = f"Warn: Failed page {page}."; break
                soup = BeautifulSoup(response.text, "html.parser")
            rows = soup.select('tr[id^="review_"]')
            if not rows: break
            for row in rows:
                title_elem=row.select_one('td.field.title .value a'); author_elem=row.select_one('td.field.author .value a'); image_elem=row.select_one('td.field.cover img'); publisher_elem = row.select_one('td.field.publisher .value') # Added publisher selector
                if title_elem and author_elem: # Ensure title and author exist
                    raw_image_url = image_elem.get("src") if image_elem else ""; high_res_image_url = raw_image_url
                    if raw_image_url: high_res_image_url = re.sub(r'\._S[XY]?\d+_?\.', '.', raw_image_url)
                    spine_color = get_edge_color(high_res_image_url) if image_elem and high_res_image_url and Image else "#808080"
                    author_name = author_elem.text.strip() # Get author text
                    publisher_name = publisher_elem.text.strip() if publisher_elem else "" # Get publisher text safely
                    books.append({
                        "title": title_elem.text.strip(),
                        "author": author_name, # Include author
                        "publisher": publisher_name, # Include publisher
                        "image": high_res_image_url,
                        "spine_color": spine_color
                    })
                    progress_data["books_processed"] = len(books)
            page += 1
        if not books and not progress_data.get("error"): progress_data["error"] = "No books found."
        progress_data["total_books"] = progress_data.get("books_processed", 0)
        progress_data["complete"] = True; print(f"Scraping finished. Found: {len(books)}"); return books
    except Exception as e: print(f"Scraping error: {e}"); traceback.print_exc(); progress_data["error"] = str(e); progress_data["complete"] = True; return None

# --- Flask App ---
app = Flask(__name__)

# --- HTML Template (With Spine Text JS Added) ---
THREE_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"> <meta name="viewport" content="width=device-width, initial-scale=1.0"> <title>My 3D Bookshelf</title>
    <style> body { margin: 0; background-color: #090909; color: #eee; font-family: system-ui, sans-serif; overflow-y: scroll; } #info { display: none; } #loading-message, #input-container { position: fixed; top: 50%; left: 50%; transform: translate(-50%,-50%); background: #fff; color: #333; padding: 30px; border-radius: 8px; box-shadow: 0 5px 15px rgba(0,0,0,.2); text-align: center; z-index: 200; min-width: 250px; } #input-container h2 { margin-top: 0; color: #333; } #input-container input[type=text] { width: calc(100% - 22px); padding: 10px; margin-bottom: 15px; border: 1px solid #ccc; border-radius: 4px; font-size: 1em;} #input-container button { padding: 10px 20px; background-color: #4CAF50; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 1em;} #input-container button:hover { background-color: #45a049; } #canvas-container { width: 100%; height: 100%; position: fixed; top: 0; left: 0; z-index: 1; } canvas { display: block; } /* Loader Styles */ #progress-bar { width: 80%; background-color: #e0e0e0; border-radius: 4px; overflow: hidden; margin: 10px auto 5px auto;} #progress-fill { height: 15px; background-color: #4A90E2; width: 0%; transition: width 0.3s ease; text-align: center; color: white; line-height: 15px; font-size: 0.8em;} #status-text { font-family: monospace; margin-top: 10px; font-size: 0.9em; color: #555;} </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
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
        const BOOK_DEFAULTS = { HEIGHT: 9.0, WIDTH: 6.075, THICKNESS: 1.125 }; // Keep large size from user code
        const PAGE_COLOR = 0xf5f5dc;
        const BOOK_SPACING = -6; // Keep large overlap from user code
        const TARGET_ROTATION_X = THREE.MathUtils.degToRad(-90);
        const TARGET_ROTATION_Y = THREE.MathUtils.degToRad(88);
        const CAMERA_Z = 30; const CAMERA_Y = 6; const CAMERA_FOV = 35; // Keep camera for large size
        const ANIM_START_X = 40; const ANIM_DURATION = 0.7; const ANIM_STAGGER = 0.03; const ANIM_EASE = "back.out(0.5)";
        // --- Added Spine Text Constants ---
        const SPINE_TEXTURE_HEIGHT = 450; // Increase resolution for larger books
        const SPINE_TEXTURE_WIDTH = Math.round(SPINE_TEXTURE_HEIGHT * (BOOK_DEFAULTS.THICKNESS / BOOK_DEFAULTS.HEIGHT));
        const SPINE_FONT_FAMILY = 'Arial, sans-serif';
        const SPINE_TITLE_SIZE_PX = 14;   // Adjusted size
        const SPINE_AUTHOR_SIZE_PX = 8;  // Adjusted size
        const SPINE_PUBLISHER_SIZE_PX = 6; // Adjusted size
        const SPINE_PADDING_PX = 15;      // Adjusted padding
        const SPINE_TEXT_OPACITY = 0.66;


        // --- DOM Elements ---
        const inputContainer=document.getElementById('input-container'); const loadingMessage=document.getElementById('loading-message'); const shelfForm=document.getElementById('shelfForm'); const shelfUrlInput=document.getElementById('shelfUrl'); const statsDiv=document.getElementById('stats'); const canvasContainer=document.getElementById('canvas-container'); const progressBarFill=document.getElementById('progress-fill'); const statusText=document.getElementById('status-text');

        // --- Three.js Variables ---
        let scene, camera, renderer; let bookData=[]; const textureLoader=new THREE.TextureLoader(); const booksGroup=new THREE.Group(); let currentScrollY=window.scrollY; let targetGroupY=0; let animationFrameId=null; let progressIntervalId=null;

        // --- Helper: Get Contrast Color (Copied from previous step) ---
        function getContrastColor(hexColor) {
            if (!hexColor || hexColor.length < 7 || hexColor === '#NaNNaNNaN') return '#000000';
            try {
                const r = parseInt(hexColor.substr(1, 2), 16); const g = parseInt(hexColor.substr(3, 2), 16); const b = parseInt(hexColor.substr(5, 2), 16);
                const luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
                return luminance > 0.5 ? '#000000' : '#FFFFFF';
            } catch (e) { return '#000000'; }
        }

        // --- Helper: Create Spine Texture (NEW) ---
        function createSpineTexture(book, widthPx, heightPx) {
            const canvas = document.createElement('canvas');
            canvas.width = widthPx; canvas.height = heightPx;
            const ctx = canvas.getContext('2d');
            if (!ctx) return null; // Check if context is available

            // 1. Background
            ctx.fillStyle = book.spine_color || '#808080';
            ctx.fillRect(0, 0, widthPx, heightPx);

            // 2. Text Setup
            const textColor = getContrastColor(book.spine_color || '#808080');
            ctx.fillStyle = textColor;
            ctx.font = `${SPINE_AUTHOR_SIZE_PX}px ${SPINE_FONT_FAMILY}`;

            // 3. Rotate for Vertical Text (Draw bottom-to-top)
            ctx.save();
            ctx.translate(widthPx / 2, heightPx / 2); ctx.rotate(Math.PI / 2); ctx.translate(-heightPx / 2, -widthPx / 2);
            const drawWidth = heightPx; const drawHeight = widthPx; // Swapped dimensions after rotation

            // 4. Draw Publisher (Top Left-ish)
            if (book.publisher && book.publisher !== "Unknown") { // Check if publisher exists and isn't default
               ctx.font = `${SPINE_PUBLISHER_SIZE_PX}px ${SPINE_FONT_FAMILY}`;
               ctx.textAlign = 'left'; ctx.textBaseline = 'top';
               ctx.globalAlpha = SPINE_TEXT_OPACITY;
               ctx.fillText(book.publisher, SPINE_PADDING_PX, SPINE_PADDING_PX); // Draw near top-left
               ctx.globalAlpha = 1.0;
            }

            // 5. Draw Title (Centered)
            ctx.font = `bold ${SPINE_TITLE_SIZE_PX}px ${SPINE_FONT_FAMILY}`;
            ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
            const titleText = book.title || '';
            const maxTextWidth = drawWidth - (SPINE_PADDING_PX * 2);
            let truncatedTitle = titleText;
            // Basic truncation if too wide
            if(ctx.measureText(titleText).width > maxTextWidth) {
               let fitChars = titleText.length;
               while(ctx.measureText(titleText.substring(0, fitChars) + "...").width > maxTextWidth && fitChars > 0) { fitChars--; }
               truncatedTitle = titleText.substring(0, Math.max(0, fitChars)) + "...";
            }
            ctx.fillText(truncatedTitle, drawWidth / 2, drawHeight / 2); // Center

            // 6. Draw Author (Bottom Right-ish)
            ctx.font = `${SPINE_AUTHOR_SIZE_PX}px ${SPINE_FONT_FAMILY}`;
            ctx.textAlign = 'right'; ctx.textBaseline = 'bottom';
            ctx.globalAlpha = SPINE_TEXT_OPACITY;
            const authorText = book.author || '';
            // Simple truncation for author too
            let truncatedAuthor = authorText;
             if(ctx.measureText(authorText).width > maxTextWidth) {
               let fitChars = authorText.length;
               while(ctx.measureText("..." + authorText.substring(authorText.length - fitChars)).width > maxTextWidth && fitChars > 0) { fitChars--; }
               truncatedAuthor = "..." + authorText.substring(authorText.length - Math.max(0, fitChars));
            }
            ctx.fillText(truncatedAuthor, drawWidth - SPINE_PADDING_PX, drawHeight - SPINE_PADDING_PX); // Near bottom-right
            ctx.globalAlpha = 1.0;

            ctx.restore(); // Restore context rotation

            // Create and return texture
            const texture = new THREE.CanvasTexture(canvas);
            texture.colorSpace = THREE.SRGBColorSpace;
            texture.needsUpdate = true;
            return texture;
        }


        // --- Init & Event Handlers ---
        function main() { setupEventHandlers(); showInputForm(); }
        function setupEventHandlers() { shelfForm.addEventListener('submit', handleUrlSubmit); window.addEventListener('resize', onWindowResize); window.addEventListener('scroll', onWindowScroll); }

        // --- Handle Form Submit ---
        async function handleUrlSubmit(event) { /* ... (Identical - includes loader start/stop) ... */
             event.preventDefault(); const shelfUrl = shelfUrlInput.value.trim(); if (!shelfUrl || !shelfUrl.includes('goodreads.com/review/list/')) { alert('Error: Invalid URL.'); return; } console.log("Shelf URL:", shelfUrl); inputContainer.style.display = 'none'; loadingMessage.style.display = 'block';
             statusText.textContent = "Fetching data..."; progressBarFill.style.width = '0%'; progressBarFill.textContent = '0%'; if (progressIntervalId) clearInterval(progressIntervalId); progressIntervalId = setInterval(updateProgress, 1000);
             try { const apiUrl = `/get_books?url=${encodeURIComponent(shelfUrl)}`; console.log("Fetching from:", apiUrl); const response = await fetch(apiUrl); let errorMsg = `HTTP error ${response.status}`; if (!response.ok) { try { const d=await response.json(); errorMsg = d.error||errorMsg; } catch (e) {} throw new Error(errorMsg); } const data = await response.json(); console.log("Received data:", data);
                if (progressIntervalId) clearInterval(progressIntervalId); progressIntervalId = null; if (data.error && (!data.books || data.books.length === 0)) { throw new Error(data.error); } bookData = data.books || []; statusText.textContent = `${bookData.length} books found. Building scene...`; progressBarFill.style.width = '100%'; progressBarFill.textContent = '100%';
                if (!scene) { initThreeJS(); } populateScene(); // Triggers animations
             } catch (error) { console.error("Fetch error:", error); alert(`Error: ${error.message}`); statusText.textContent = `Error: ${error.message}`; if (progressIntervalId) clearInterval(progressIntervalId); progressIntervalId = null; loadingMessage.style.display = 'block'; }
        }

        // --- updateProgress Function ---
        async function updateProgress() { /* ... (Identical - polls /progress) ... */
             try { const response = await fetch('/progress'); if (!response.ok) { console.warn("Progress check failed:", response.status); return; } const data = await response.json(); const percent = data.progress || 0; if(progressBarFill){ progressBarFill.style.width = percent + '%'; progressBarFill.textContent = percent + '%'; } if(statusText){ if (!data.complete && !data.error) { statusText.textContent = `Processing... (${data.books_processed}/${data.total_books})`; } } if (data.complete || data.error) { console.log("Progress poll end."); if (progressIntervalId) clearInterval(progressIntervalId); progressIntervalId = null; if(progressBarFill){ progressBarFill.style.width = '100%'; progressBarFill.textContent = '100%';} if(statusText && data.error){ statusText.textContent = `Error: ${data.error}`; } else if(statusText && data.complete) { /* Let handleUrlSubmit show final */ } } } catch (error) { console.warn("Error fetching progress:", error); }
        }

        // --- Three.js Scene Initialization ---
        function initThreeJS() { /* Uses constants from user's code */
            console.log("Initializing Three.js scene..."); scene = new THREE.Scene(); scene.background = new THREE.Color(0x090909); const aspect = window.innerWidth / window.innerHeight; camera = new THREE.PerspectiveCamera(CAMERA_FOV, aspect, 0.1, 1000);
            camera.position.set(0, CAMERA_Y, CAMERA_Z); // Uses CAMERA_Y=6, CAMERA_Z=30
            camera.lookAt(0, 0, 0); renderer = new THREE.WebGLRenderer({ antialias: true }); renderer.setSize(window.innerWidth, window.innerHeight); renderer.setPixelRatio(window.devicePixelRatio); canvasContainer.appendChild(renderer.domElement); const ambientLight = new THREE.AmbientLight(0xffffff, 0.7); scene.add(ambientLight); const keyLight = new THREE.DirectionalLight(0xffffff, 0.8); keyLight.position.set(-8, 10, 8); scene.add(keyLight); const fillLight = new THREE.DirectionalLight(0xffffff, 0.3); fillLight.position.set(8, 2, 6); scene.add(fillLight); scene.add(booksGroup); window.addEventListener('resize', onWindowResize); if (!animationFrameId) { animate(); console.log("Animation loop started."); }
        }

        // --- Populate Scene with Books ---
        function populateScene() { /* Uses constants from user's code */
             while(booksGroup.children.length > 0){ booksGroup.remove(booksGroup.children[0]); } console.log(`Creating ${bookData.length} book meshes...`);
             const totalStackHeight = bookData.length * (BOOK_DEFAULTS.HEIGHT + BOOK_SPACING) - BOOK_SPACING; // Uses user's size/spacing
             const startY = totalStackHeight / 2 - BOOK_DEFAULTS.HEIGHT / 2;
             const initialGroupY = -startY;
             bookData.forEach((book, index) => {
                 const bookMesh = createBookMesh(book); // Creates larger book
                 bookMesh.position.y = startY - index * (BOOK_DEFAULTS.HEIGHT + BOOK_SPACING);
                 const startX = (index % 2 === 0) ? -ANIM_START_X : ANIM_START_X; bookMesh.position.x = startX; booksGroup.add(bookMesh);
                 gsap.to(bookMesh.position, { x: 0, duration: ANIM_DURATION, delay: 0.05 + index * ANIM_STAGGER, ease: ANIM_EASE });
             });
             console.log("Finished adding meshes and starting animations."); loadingMessage.style.display = 'none';
             document.body.style.height = `${totalStackHeight * 50}px`;
             targetGroupY = initialGroupY; booksGroup.position.y = initialGroupY;
             onWindowScroll(); // Set initial scroll position
         }

        // --- Create Single Book Mesh (MODIFIED FOR SPINE TEXTURE) ---
        function createBookMesh(book) {
             const geometry = new THREE.BoxGeometry(BOOK_DEFAULTS.WIDTH, BOOK_DEFAULTS.HEIGHT, BOOK_DEFAULTS.THICKNESS); // Uses size from constants
             const pageMaterial = new THREE.MeshStandardMaterial({ color: PAGE_COLOR, roughness: 0.95, metalness: 0.05 });
             // --- Create spine texture ---
             const spineTexture = createSpineTexture(book, SPINE_TEXTURE_WIDTH, SPINE_TEXTURE_HEIGHT);
             // --- Use texture for spine material ---
             const spineMaterial = new THREE.MeshStandardMaterial({
                 map: spineTexture,
                 color: 0xffffff, // Base color white
                 roughness: 0.8, metalness: 0.1 });
             const coverMaterial = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.8, metalness: 0.1 });
             if (book.image) { textureLoader.load( book.image, (texture) => { texture.colorSpace = THREE.SRGBColorSpace; const imgAspect = texture.image.naturalWidth / texture.image.naturalHeight; const geomAspect = BOOK_DEFAULTS.WIDTH / BOOK_DEFAULTS.HEIGHT; texture.repeat.set(1, geomAspect / imgAspect); texture.offset.set(0, (1 - texture.repeat.y) / 2); coverMaterial.map = texture; coverMaterial.needsUpdate = true; }, undefined, (err) => { console.error(`Err texture ${book.title}:`, err); } ); }
             const materials = [ pageMaterial, spineMaterial, pageMaterial, pageMaterial, coverMaterial, pageMaterial ]; // R, L(-X/Spine), T, B, F(+Z/Cover), Bk
             const mesh = new THREE.Mesh(geometry, materials);
             mesh.rotation.order = 'YXZ'; mesh.rotation.x = TARGET_ROTATION_X; mesh.rotation.y = TARGET_ROTATION_Y;
             return mesh;
         }

        // --- Handle Scrolling (Uses updated constants) ---
        function onWindowScroll() {
             const totalTravelDistance = Math.max(0, bookData.length - 1) * (BOOK_DEFAULTS.HEIGHT + BOOK_SPACING); currentScrollY = window.scrollY; const maxScroll = document.documentElement.scrollHeight - window.innerHeight; const scrollRatio = maxScroll > 0 ? currentScrollY / maxScroll : 0; const totalStackHeight = bookData.length * (BOOK_DEFAULTS.HEIGHT + BOOK_SPACING) - BOOK_SPACING; const startY = totalStackHeight / 2 - BOOK_DEFAULTS.HEIGHT / 2; const initialGroupY = -startY;
             targetGroupY = initialGroupY + (scrollRatio * totalTravelDistance);
         }
        // --- Render Loop ---
        function animate() {
             animationFrameId = requestAnimationFrame(animate); booksGroup.position.y += (targetGroupY - booksGroup.position.y) * 0.1; renderer.render(scene, camera);
         }
        // --- Resize Handler ---
        function onWindowResize() {
            if (!camera || !renderer) return; camera.aspect = window.innerWidth / window.innerHeight; camera.updateProjectionMatrix(); renderer.setSize(window.innerWidth, window.innerHeight); onWindowScroll();
         }
         function showInputForm(){ loadingMessage.style.display = 'none'; inputContainer.style.display = 'block'; }
        // --- Initial State ---
        main(); // Start

    </script>
</body>
</html>'''

# --- Flask Routes (Including /progress) ---
@app.route("/")
def index():
    global progress_data; progress_data = {"total_books":0,"books_processed":0,"complete":False,"error":None}
    return render_template_string(THREE_TEMPLATE)

@app.route("/get_books")
def get_books_api():
    url = request.args.get("url", "").strip()
    if not url: return jsonify({"error": "Missing URL parameter"}), 400
    # --- Ensure scraper returns author/publisher ---
    books_data = get_books_from_shelf(url)
    error_message = progress_data.get("error")
    if error_message:
        status_code = 500 if ("Failed page 1" in error_message or "fetch" in error_message) and not books_data else 200
        return jsonify({"error": error_message,"books": books_data or []}), status_code
    elif not books_data: return jsonify({"error": "No books found"}), 404
    else: return jsonify({"books": books_data,"total_found": len(books_data)})

@app.route("/progress")
def get_progress():
    total = progress_data.get("total_books", 0)
    processed = progress_data.get("books_processed", 0)
    percent = min(100, int((processed / total) * 100)) if total > 0 else 0
    return jsonify({ "progress": percent, "books_processed": processed, "total_books": total, "complete": progress_data.get("complete", False), "error": progress_data.get("error") })

# --- Main Execution ---
if __name__ == "__main__":
    app.run(debug=True, port=5000)