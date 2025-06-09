from flask import Flask, request, render_template_string, session, redirect, url_for
from Pylette import extract_colors
from PIL import Image, ImageDraw
import io
import base64
import os
import tempfile

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Template untuk halaman ekstraksi warna
EXTRACT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Color Palette Extractor</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        body { 
            font-family: 'Inter', sans-serif;
            background-color: #f8fafc;
        }
        .preview-container {
            display: none;
            position: relative;
            background-color: #f1f5f9;
            border-radius: 0.5rem;
            padding: 1rem;
            margin-bottom: 1rem;
            text-align: center; /* Center the content */
        }
        .preview-container img {
            max-width: 100%;
            max-height: 400px;
            object-fit: contain;
            border-radius: 0.375rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin: 0 auto; /* Center the image */
            display: block; /* Remove inline spacing */
        }
        .remove-preview {
            position: absolute;
            top: 1rem;
            right: 1rem;
            background: rgba(255, 255, 255, 0.9);
            border-
            transition: all 0.2s;
        }
        .remove-preview:hover {
            background: rgba(255, 255, 255, 1);
            transform: scale(1.05);
        }
        .color-swatch {
            transition: transform 0.2s;
        }
        .color-swatch:hover {
            transform: scale(1.05);
        }
        .nav-link {
            position: relative;
            padding-bottom: 0.5rem;
        }
        .nav-link::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            width: 0;
            height: 2px;
            background-color: #2563eb;
            transition: width 0.2s;
        }
        .nav-link:hover::after {
            width: 100%;
        }
        .nav-link.active::after {
            width: 100%;
        }
        .palette-container {
            position: relative;
        }
        .color-strip {
            width: 100%;
            height: 200px;
            display: flex;
        }
        .color-label {
            text-align: center;
            font-family: monospace;
            padding: 8px 0;
            font-size: 14px;
            color: #333;
        }
    </style>
</head>
<body class="min-h-screen">
    <!-- Navbar -->
    <nav class="bg-white shadow-sm border-b sticky top-0 z-50">
        <div class="max-w-6xl mx-auto px-4">
            <div class="flex justify-between items-center h-16">
                <h1 class="text-xl font-semibold text-blue-500">Paletize</h1>
                <div class="flex space-x-8">
                    <a href="/" class="nav-link text-gray-600 hover:text-gray-900 active">Extract Colors</a>
                    <a href="/edit" class="nav-link text-gray-600 hover:text-gray-900">Edit Image</a>
                </div>
            </div>
        </div>
    </nav>

    <div class="max-w-5xl mx-auto px-4 py-8">
        <!-- Header -->
        <div class="text-center mb-12">
            <h2 class="text-4xl font-bold text-gray-900 mb-3">Extract Color Palette</h2>
            <p class="text-lg text-gray-600">Upload an image to extract its dominant colors and create beautiful palettes</p>
        </div>

        <!-- Upload Form -->
        <div class="bg-white rounded-xl shadow-sm border p-8 mb-8">
            <form action="/upload" method="POST" enctype="multipart/form-data" id="uploadForm">
                <div class="mb-6">
                    <label class="block text-lg font-medium text-gray-700 mb-3">Choose Image</label>
                    <div class="flex items-center justify-center w-full">
                        <label class="flex flex-col items-center justify-center w-full h-32 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100">
                            <div class="flex flex-col items-center justify-center pt-5 pb-6">
                                <svg class="w-10 h-10 mb-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                                </svg>
                                <p class="mb-2 text-sm text-gray-500"><span class="font-semibold">Click to upload</span> or drag and drop</p>
                                <p class="text-xs text-gray-500">PNG, JPG or JPEG (MAX. 10MB)</p>
                            </div>
                            <input type="file" name="image" accept="image/*" required id="imageInput" class="hidden" />
                        </label>
                    </div>
                </div>
                
                <!-- Preview Container -->
                <div id="previewContainer" class="preview-container">
                    <img id="imagePreview" src="" alt="Preview">
                    <button type="button" id="removePreview" class="remove-preview">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <button type="submit" 
                        class="w-full bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 transition-colors text-lg font-medium">
                    Extract Colors
                </button>
            </form>
        </div>

        <!-- Results -->
        {% if uploaded_img or hex_colors or error %}
        <div class="space-y-8">
            {% if uploaded_img %}
            <!-- Uploaded Image -->
            <div class="bg-white rounded-xl shadow-sm border p-8">
                <h3 class="text-xl font-semibold text-gray-900 mb-6">Uploaded Image</h3>
                <div class="flex justify-center">
                    <img src="data:image/png;base64,{{ uploaded_img }}" 
                         class="max-w-full h-auto max-h-[500px] rounded-lg shadow-sm"
                         alt="Uploaded image">
                </div>
            </div>
            {% endif %}

            {% if hex_colors %}
            <!-- Color Palette -->
            <div class="bg-white rounded-xl shadow-sm border p-8">
                <h3 class="text-xl font-semibold text-gray-900 mb-6">Extracted Colors</h3>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-6">
                    {% for hex in hex_colors %}
                    <div class="text-center color-swatch">
                        <div class="w-full h-32 rounded-xl mb-3 shadow-sm border" 
                             style="background-color: {{ hex }};"></div>
                        <p class="text-sm font-mono text-gray-700 mb-1">{{ hex }}</p>
                        <p class="text-xs text-gray-500">{{ percentage[loop.index0] }}</p>
                    </div>
                    {% endfor %}
                </div>
                
                <!-- Continue to Edit Button -->
                <div class="mt-8 text-center">
                    <a href="/edit" class="inline-block bg-green-600 text-white py-3 px-8 rounded-lg hover:bg-green-700 transition-colors text-lg font-medium">
                        Edit This Image
                    </a>
                </div>
            </div>
            {% endif %}

            {% if palette_img %}
            <!-- Download Palette -->
            <div class="bg-white rounded-xl shadow-sm border p-8 text-center">
                <h3 class="text-xl font-semibold text-gray-900 mb-6">Color Palette</h3>
                
                <!-- Styled palette similar to the reference image -->
                <div class="palette-container mb-6 max-w-3xl mx-auto rounded-lg overflow-hidden border shadow-sm">
                    <div class="color-strip">
                        {% for hex in hex_colors %}
                        <div style="background-color: {{ hex }}; flex: 1;"></div>
                        {% endfor %}
                    </div>
                    <div class="color-labels bg-gray-100" style="display: flex;">
                        {% for hex in hex_colors %}
                        <div class="color-label" style="flex: 1;">{{ hex }}</div>
                        {% endfor %}
                    </div>
                </div>
                
                <div class="flex justify-center space-x-4">
                    <a href="data:image/png;base64,{{ palette_img }}" download="color-palette.png"
                       class="inline-block bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 transition-colors text-lg font-medium">
                        Download Palette
                    </a>
                    
                    <!-- Generate HTML for styled palette download -->
                    <button id="downloadHtmlBtn" 
                            class="inline-block bg-gray-600 text-white py-3 px-6 rounded-lg hover:bg-gray-700 transition-colors text-lg font-medium">
                        Download HTML Version
                    </button>
                </div>
            </div>
            {% endif %}

            {% if error %}
            <!-- Error Message -->
            <div class="bg-red-50 border border-red-200 rounded-xl p-6">
                <p class="text-red-700 text-center">{{ error }}</p>
            </div>
            {% endif %}
        </div>
        {% endif %}
    </div>

    <script>
        // Image Preview Functionality
        const imageInput = document.getElementById('imageInput');
        const previewContainer = document.getElementById('previewContainer');
        const imagePreview = document.getElementById('imagePreview');
        const removePreview = document.getElementById('removePreview');
        const uploadForm = document.getElementById('uploadForm');
        const dropZone = document.querySelector('.border-dashed');

        // Handle file selection
        imageInput.addEventListener('change', function(e) {
            handleFileSelect(e.target.files[0]);
        });

        // Handle drag and drop
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('border-blue-500');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('border-blue-500');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('border-blue-500');
            handleFileSelect(e.dataTransfer.files[0]);
        });

        function handleFileSelect(file) {
            if (file) {
                if (file.size > 10 * 1024 * 1024) { // 10MB limit
                    alert('File size exceeds 10MB limit');
                    return;
                }
                const reader = new FileReader();
                reader.onload = function(e) {
                    imagePreview.src = e.target.result;
                    previewContainer.style.display = 'block';
                }
                reader.readAsDataURL(file);
            }
        }

        removePreview.addEventListener('click', function() {
            imageInput.value = '';
            previewContainer.style.display = 'none';
            imagePreview.src = '';
        });

        // Prevent form submission if no image is selected
        uploadForm.addEventListener('submit', function(e) {
            if (!imageInput.files.length) {
                e.preventDefault();
                alert('Please select an image first');
            }
        });
        
        {% if hex_colors %}
        // Download HTML palette functionality
        const downloadHtmlBtn = document.getElementById('downloadHtmlBtn');
        if (downloadHtmlBtn) {
            downloadHtmlBtn.addEventListener('click', function() {
                const colors = [{% for hex in hex_colors %}'{{ hex }}',{% endfor %}];
                
                const htmlContent = `
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>Color Palette</title>
                    <style>
                        body {
                            margin: 0;
                            padding: 20px;
                            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                        }
                        .palette-container {
                            width: 800px;
                            margin: 0 auto;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                            border-radius: 4px;
                            overflow: hidden;
                        }
                        .color-strip {
                            height: 200px;
                            display: flex;
                        }
                        .color-block {
                            flex: 1;
                        }
                        .color-labels {
                            display: flex;
                            background: #f8f8f8;
                        }
                        .color-label {
                            flex: 1;
                            text-align: center;
                            padding: 12px 0;
                            font-family: monospace;
                            font-size: 14px;
                            color: #333;
                        }
                    </style>
                </head>
                <body>
                    <div class="palette-container">
                        <div class="color-strip">
                            ${colors.map(color => `<div class="color-block" style="background-color: ${color};"></div>`).join('')}
                        </div>
                        <div class="color-labels">
                            ${colors.map(color => `<div class="color-label">${color}</div>`).join('')}
                        </div>
                    </div>
                </body>
                </html>
                `;
                
                const blob = new Blob([htmlContent], {type: 'text/html'});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'color-palette.html';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            });
        }
        {% endif %}
    </script>
</body>
</html>
"""

# Template untuk halaman edit gambar
EDIT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Edit Image Colors</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        body { 
            font-family: 'Inter', sans-serif;
            background-color: #f8fafc;
        }
        .nav-link {
            position: relative;
            padding-bottom: 0.5rem;
        }
        .nav-link::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            width: 0;
            height: 2px;
            background-color: #2563eb;
            transition: width 0.2s;
        }
        .nav-link:hover::after {
            width: 100%;
        }
        .nav-link.active::after {
            width: 100%;
        }
        .color-swatch {
            transition: transform 0.2s;
        }
        .color-swatch:hover {
            transform: scale(1.05);
        }
        .slider-container {
            position: relative;
            padding: 1rem;
            background-color: #f1f5f9;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
        }
        .slider-container:hover {
            background-color: #e2e8f0;
        }
        input[type="range"] {
            -webkit-appearance: none;
            width: 100%;
            height: 6px;
            background: #e2e8f0;
            border-radius: 3px;
            outline: none;
        }
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 20px;
            height: 20px;
            background: #2563eb;
            border-radius: 50%;
            cursor: pointer;
            transition: all 0.2s;
        }
        input[type="range"]::-webkit-slider-thumb:hover {
            transform: scale(1.1);
        }
    </style>
</head>
<body class="min-h-screen">
    <!-- Navbar -->
    <nav class="bg-white shadow-sm border-b sticky top-0 z-50">
        <div class="max-w-6xl mx-auto px-4">
            <div class="flex justify-between items-center h-16">
                <h1 class="text-xl font-semibold text-blue-500">Paletize</h1>
                <div class="flex space-x-8">
                    <a href="/" class="nav-link text-gray-600 hover:text-gray-900">Extract Colors</a>
                    <a href="/edit" class="nav-link text-gray-600 hover:text-gray-900 active">Edit Image</a>
                </div>
            </div>
        </div>
    </nav>

    <div class="max-w-5xl mx-auto px-4 py-8">
        <!-- Header -->
        <div class="text-center mb-12">
            <h2 class="text-4xl font-bold text-gray-900 mb-3">Edit Image Colors</h2>
            <p class="text-lg text-gray-600">Adjust RGB values to modify your image colors</p>
        </div>

        {% if not session.get('original_image_path') %}
        <!-- No Image Message -->
        <div class="bg-yellow-50 border border-yellow-200 rounded-xl p-8 text-center">
            <h3 class="text-xl font-semibold text-yellow-800 mb-3">No Image Found</h3>
            <p class="text-yellow-700 mb-6">Please upload an image first to edit its colors.</p>
            <a href="/" class="inline-block bg-blue-600 text-white py-3 px-8 rounded-lg hover:bg-blue-700 transition-colors text-lg font-medium">
                Go to Extract Colors
            </a>
        </div>
        {% else %}
        
        <!-- Image Preview Section -->
        <div class="bg-white rounded-xl shadow-sm border p-8 mb-8">
            <h3 class="text-xl font-semibold text-gray-900 mb-6 text-center">Image Preview</h3>
            <div class="flex flex-col items-center space-y-8">
                <!-- Original Image -->
                <div class="w-full max-w-2xl">
                    <h4 class="text-lg font-medium text-gray-700 mb-3 text-center">Original Image</h4>
                    <div class="flex justify-center">
                        <img src="data:image/png;base64,{{ original_img|default('') }}" 
                             class="max-w-full h-auto max-h-[400px] rounded-lg shadow-sm"
                             alt="Original image">
                    </div>
                </div>

                {% if edited_img %}
                <!-- Edited Image -->
                <div class="w-full max-w-2xl">
                    <h4 class="text-lg font-medium text-gray-700 mb-3 text-center">Edited Image</h4>
                    <div class="flex justify-center">
                        <img src="data:image/png;base64,{{ edited_img }}" 
                             class="max-w-full h-auto max-h-[400px] rounded-lg shadow-sm"
                             alt="Edited image">
                    </div>
                    <!-- Download Button -->
                    <div class="mt-4 text-center">
                        <a href="data:image/png;base64,{{ edited_img }}" 
                           download="edited-image.png"
                           class="inline-block bg-green-600 text-white py-2 px-6 rounded-lg hover:bg-green-700 transition-colors">
                            Download Edited Image
                        </a>
                    </div>
                </div>
                {% endif %}
            </div>
        </div>

        <!-- Color Adjustment Form -->
        <div class="bg-white rounded-xl shadow-sm border p-8 mb-8">
            <h3 class="text-xl font-semibold text-gray-900 mb-6">Adjust Colors</h3>
            <form action="/adjust" method="POST">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <!-- Red -->
                    <div class="slider-container">
                        <label class="block text-sm font-medium text-gray-700 mb-3">Red</label>
                        <input type="range" min="-255" max="255" value="{{ red_offset|default(0) }}" 
                               name="red_offset" id="redSlider" 
                               class="mb-2">
                        <div class="text-center">
                            <span class="text-sm text-gray-600">Value: </span>
                            <span id="redValue" class="font-medium">{{ red_offset|default(0) }}</span>
                        </div>
                    </div>
                    
                    <!-- Green -->
                    <div class="slider-container">
                        <label class="block text-sm font-medium text-gray-700 mb-3">Green</label>
                        <input type="range" min="-255" max="255" value="{{ green_offset|default(0) }}" 
                               name="green_offset" id="greenSlider"
                               class="mb-2">
                        <div class="text-center">
                            <span class="text-sm text-gray-600">Value: </span>
                            <span id="greenValue" class="font-medium">{{ green_offset|default(0) }}</span>
                        </div>
                    </div>
                    
                    <!-- Blue -->
                    <div class="slider-container">
                        <label class="block text-sm font-medium text-gray-700 mb-3">Blue</label>
                        <input type="range" min="-255" max="255" value="{{ blue_offset|default(0) }}" 
                               name="blue_offset" id="blueSlider"
                               class="mb-2">
                        <div class="text-center">
                            <span class="text-sm text-gray-600">Value: </span>
                            <span id="blueValue" class="font-medium">{{ blue_offset|default(0) }}</span>
                        </div>
                    </div>
                </div>
                
                <div class="flex gap-4 mt-8">
                    <button type="submit" 
                            class="flex-1 bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 transition-colors text-lg font-medium">
                        Apply Changes
                    </button>
                    <button type="button" onclick="resetSliders()" 
                            class="flex-1 bg-gray-600 text-white py-3 px-6 rounded-lg hover:bg-gray-700 transition-colors text-lg font-medium">
                        Reset
                    </button>
                </div>
            </form>
        </div>

        {% if hex_colors %}
        <!-- Updated Color Palette -->
        <div class="bg-white rounded-xl shadow-sm border p-8">
            <h3 class="text-xl font-semibold text-gray-900 mb-6">Updated Color Palette</h3>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-6">
                {% for hex in hex_colors %}
                <div class="text-center color-swatch">
                    <div class="w-full h-32 rounded-xl mb-3 shadow-sm border" 
                         style="background-color: {{ hex }};"></div>
                    <p class="text-sm font-mono text-gray-700 mb-1">{{ hex }}</p>
                    <p class="text-xs text-gray-500">{{ percentage[loop.index0] }}</p>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        {% if error %}
        <!-- Error Message -->
        <div class="bg-red-50 border border-red-200 rounded-xl p-6 mt-8">
            <p class="text-red-700 text-center">{{ error }}</p>
        </div>
        {% endif %}
        
        {% endif %}
    </div>

    <script>
        function resetSliders() {
            document.getElementById('redSlider').value = 0;
            document.getElementById('greenSlider').value = 0;
            document.getElementById('blueSlider').value = 0;
            
            document.getElementById('redValue').textContent = '0';
            document.getElementById('greenValue').textContent = '0';
            document.getElementById('blueValue').textContent = '0';
        }
        
        // Update slider values with smooth transitions
        document.getElementById('redSlider').oninput = function() {
            document.getElementById('redValue').textContent = this.value;
        }
        document.getElementById('greenSlider').oninput = function() {
            document.getElementById('greenValue').textContent = this.value;
        }
        document.getElementById('blueSlider').oninput = function() {
            document.getElementById('blueValue').textContent = this.value;
        }
    </script>
</body>
</html>
"""

def generate_palette_image(colors, width=400, height=100):
    """Generate a palette image from color list"""
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    num_colors = len(colors)
    if num_colors == 0:
        return img
    swatch_width = width // num_colors
    for i, color in enumerate(colors):
        rgb_tuple = tuple(color.rgb)
        draw.rectangle(
            [(i * swatch_width, 0), ((i + 1) * swatch_width, height)],
            fill=rgb_tuple
        )
    return img

def image_to_base64(img: Image.Image) -> str:
    """Convert PIL image to base64 string"""
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def adjust_image_colors(img: Image.Image, red_offset: int, green_offset: int, blue_offset: int) -> Image.Image:
    """Adjust image colors by adding offsets to RGB values"""
    img_copy = img.copy()
    pixels = img_copy.load()
    width, height = img_copy.size
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            r = min(255, max(0, r + red_offset))
            g = min(255, max(0, g + green_offset))
            b = min(255, max(0, b + blue_offset))
            pixels[x, y] = (r, g, b)
    return img_copy

@app.route('/')
def index():
    """Halaman ekstraksi warna"""
    return render_template_string(EXTRACT_TEMPLATE)

@app.route('/edit')
def edit():
    """Halaman edit gambar"""
    try:
        if 'original_image_path' in session and os.path.exists(session['original_image_path']):
            original_img = Image.open(session['original_image_path'])
            # Check if there's an edited image in session
            edited_img = None
            if 'edited_image_path' in session and os.path.exists(session['edited_image_path']):
                edited_img = Image.open(session['edited_image_path'])
                edited_img = image_to_base64(edited_img)
            
            return render_template_string(
                EDIT_TEMPLATE,
                original_img=image_to_base64(original_img),
                edited_img=edited_img
            )
    except Exception as e:
        return render_template_string(
            EDIT_TEMPLATE,
            error=f"Error loading image: {str(e)}"
        )
    return render_template_string(EDIT_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload():
    """Handle image upload dan ekstraksi warna"""
    if 'image' not in request.files:
        return render_template_string(EXTRACT_TEMPLATE, error="No image file uploaded")

    image_file = request.files['image']
    if image_file.filename == '':
        return render_template_string(EXTRACT_TEMPLATE, error="No file selected")

    try:
        # Save original image to session
        img = Image.open(image_file.stream).convert("RGB")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
            img.save(temp_file.name, format='PNG')
            session['original_image_path'] = temp_file.name
        
        # Extract colors
        colors = extract_colors(temp_file.name, palette_size=4)
        frequencies = [f"{s.freq * 100:.2f}%" for s in colors]
        hex_colors = [f'#{c.rgb[0]:02x}{c.rgb[1]:02x}{c.rgb[2]:02x}' for c in colors]
        
        # Generate palette image
        palette_img = generate_palette_image(colors)
        
        return render_template_string(
            EXTRACT_TEMPLATE,
            uploaded_img=image_to_base64(img),
            palette_img=image_to_base64(palette_img),
            hex_colors=hex_colors,
            percentage=frequencies
        )
    except Exception as e:
        return render_template_string(
            EXTRACT_TEMPLATE,
            error=f"Error processing image: {str(e)}"
        )

@app.route('/adjust', methods=['POST'])
def adjust_colors():
    """Handle color adjustment requests"""
    try:
        # Get offsets from form
        red_offset = int(request.form.get('red_offset', 0))
        green_offset = int(request.form.get('green_offset', 0))
        blue_offset = int(request.form.get('blue_offset', 0))
        
        # Load original image from session
        if 'original_image_path' not in session or not os.path.exists(session['original_image_path']):
            return render_template_string(EDIT_TEMPLATE, error="Original image not found. Please upload an image first.")
        
        original_img = Image.open(session['original_image_path'])
        
        # Apply color adjustments
        edited_img = adjust_image_colors(original_img, red_offset, green_offset, blue_offset)
        
        # Save adjusted image for color extraction and session
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
            edited_img.save(temp_file.name, format='PNG')
            session['edited_image_path'] = temp_file.name
            temp_path = temp_file.name
        
        # Extract colors from adjusted image
        colors = extract_colors(temp_path, palette_size=4)
        os.unlink(temp_path)  # Clean up temp file
        
        frequencies = [f"{s.freq * 100:.2f}%" for s in colors]
        hex_colors = [f'#{c.rgb[0]:02x}{c.rgb[1]:02x}{c.rgb[2]:02x}' for c in colors]
        
        return render_template_string(
            EDIT_TEMPLATE,
            original_img=image_to_base64(original_img),
            edited_img=image_to_base64(edited_img),
            hex_colors=hex_colors,
            percentage=frequencies,
            red_offset=red_offset,
            green_offset=green_offset,
            blue_offset=blue_offset
        )
    except Exception as e:
        return render_template_string(
            EDIT_TEMPLATE,
            error=f"Error adjusting colors: {str(e)}",
            red_offset=request.form.get('red_offset', 0),
            green_offset=request.form.get('green_offset', 0),
            blue_offset=request.form.get('blue_offset', 0)
        )

if __name__ == '__main__':
    app.run(debug=True)