from flask import Flask, request, render_template_string, send_file
from Pylette import extract_colors, Palette
from PIL import Image, ImageDraw
import io
import base64
import os
import tempfile

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Color Palette Extractor</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/alpinejs/3.13.3/cdn.min.js" defer></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        'inter': ['Inter', 'sans-serif'],
                    },
                    colors: {
                        'planetary': '#334EAC',
                        'venus': '#AAD6ED',
                        'meteor': '#F7F2EB',
                        'universe': '#709603',
                        'galaxy': '#0B1F5C',
                        'milkyway': '#FFF9F0',
                        'sky': '#00E3FF'
                    },
                    animation: {
                        'spin-slow': 'spin 3s linear infinite',
                        'pulse-gentle': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                        'fade-in': 'fadeIn 0.5s ease-in-out',
                        'slide-up': 'slideUp 0.5s ease-out',
                    }
                }
            }
        }
    </script>
    <style>
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        @keyframes slideUp {
            from { 
                opacity: 0;
                transform: translateY(30px);
            }
            to { 
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .loading-spinner {
            border: 3px solid #f3f4f6;
            border-top: 3px solid #334EAC;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
        }
        
        .glass-effect {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
    </style>
</head>

<body class="min-h-screen bg-gradient-to-br from-planetary via-universe to-galaxy font-inter" x-data="colorExtractor()">
    
    <!-- Main Container -->
    <div class="container mx-auto px-4 py-8 max-w-4xl">
        
        <!-- Header -->
        <div class="text-center mb-12">
            <h1 class="text-4xl md:text-6xl font-bold text-white mb-4">
                Color Palette Extractor
            </h1>
            <p class="text-lg text-venus/90 max-w-2xl mx-auto">
                Upload an image and we'll extract its beautiful color palette for you
            </p>
        </div>

        <!-- Upload Section -->
        <div class="mb-8">
            <form action="/upload" method="POST" enctype="multipart/form-data" 
                  class="glass-effect rounded-2xl p-8 shadow-xl"
                  @submit="isLoading = true">
                
                <!-- File Upload Area -->
                <div class="relative group mb-6">
                    <input type="file" name="image" accept="image/*" required 
                           id="file-upload"
                           class="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                           @change="handleFileSelect($event)">
                    
                    <div class="border-2 border-dashed border-venus/30 rounded-xl p-8 text-center transition-all duration-300 hover:border-venus/50 hover:bg-white/5">
                        <div class="mb-4">
                            <svg class="w-12 h-12 mx-auto text-venus/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                            </svg>
                        </div>
                        <div x-show="!selectedFile">
                            <h3 class="text-xl font-semibold text-white mb-2">Choose an image</h3>
                            <p class="text-venus/80 text-sm">PNG, JPG, GIF up to 10MB</p>
                        </div>
                        <div x-show="selectedFile" class="text-white">
                            <p class="font-medium" x-text="selectedFile"></p>
                        </div>
                    </div>
                </div>

                <!-- Submit Button -->
                <button type="submit" 
                        :disabled="isLoading"
                        class="w-full bg-gradient-to-r from-planetary to-galaxy hover:from-galaxy hover:to-planetary disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 px-6 rounded-xl transition-all duration-300 transform hover:scale-105 active:scale-95 shadow-lg">
                    <span x-show="!isLoading" class="flex items-center justify-center">
                        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 12l2 2 4-4"></path>
                        </svg>
                        Extract Colors
                    </span>
                    <span x-show="isLoading" class="flex items-center justify-center">
                        <div class="loading-spinner mr-3"></div>
                        Processing...
                    </span>
                </button>
            </form>
        </div>

        <!-- Loading State -->
        <div x-show="isLoading" class="text-center py-12 animate-fade-in">
            <div class="loading-spinner mx-auto mb-4"></div>
            <h3 class="text-xl font-semibold text-white mb-2">Extracting Colors...</h3>
            <p class="text-venus/80">Please wait while we analyze your image</p>
            <div class="mt-6 text-sm text-venus/60">
                <p>✨ Results will appear below when ready</p>
            </div>
        </div>

        <!-- Results Section -->
        {% if uploaded_img or palette_img or hex_colors or error %}
        <div class="space-y-8 animate-slide-up">
            
            <!-- Results Header -->
            <div class="text-center border-t border-venus/20 pt-8">
                <h2 class="text-2xl font-bold text-white mb-2">Results</h2>
                <p class="text-venus/80 text-sm">Your extracted color palette is ready!</p>
            </div>

            {% if uploaded_img %}
            <!-- Uploaded Image -->
            <div class="glass-effect rounded-2xl p-6 shadow-xl">
                <h3 class="text-lg font-semibold text-white mb-4 text-center">Your Image</h3>
                <div class="flex justify-center">
                    <img src="data:image/png;base64,{{ uploaded_img }}" 
                         class="max-w-full h-auto max-h-80 rounded-xl shadow-lg"
                         alt="Uploaded image">
                </div>
            </div>
            
            <div class="glass-effect rounded-2xl p-6 shadow-xl">
                <h3 class="text-lg font-semibold text-white mb-4 text-center">Edit Color</h3>
                <div class="flex justify-between">
                    <input type="hidden" name="red_offset" id="hiddenRed">
                    <input type="hidden" name="green_offset" id="hiddenGreen">
                    <input type="hidden" name="blue_offset" id="hiddenBlue">
                    <div>
                        <p>
                            Red
                        </p>
                        <input type="range" min="-255" max="255" value="0" class="slider" id="redSlider">
                        <p>
                            Value : <span id="redValue"></span>
                        </p>
                    </div>
                    <div>
                        <p>
                            Green
                        </p>
                        <input type="range" min="-255" max="255" value="0" class="slider" id="greenSlider">
                        <p>
                            Value : <span id="greenValue"></span>
                        </p>
                    </div>
                    <div>
                        <p>
                            Blue
                        </p>
                        <input type="range" min="-255" max="255" value="0" class="slider" id="blueSlider">
                        <p>
                            Value : <span id="blueValue"></span>
                        </p>
                    </div>
                    
                </div>
            </div>
            {% endif %}

            {% if hex_colors %}
            <!-- Color Palette -->
            <div class="glass-effect rounded-2xl p-6 shadow-xl">
                <h3 class="text-lg font-semibold text-white mb-6 text-center">Extracted Colors</h3>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {% for hex in hex_colors %}
                    <div class="relative group cursor-pointer transform transition-all duration-300 hover:scale-105"
                         x-data="{ copied: false }"
                         @click="copyToClipboard('{{ hex }}'); copied = true; setTimeout(() => copied = false, 2000)">
                        
                        <div class="bg-white/10 backdrop-blur-sm rounded-xl p-4 border border-white/20 hover:border-white/40 transition-all duration-300">
                            <div class="w-full h-20 rounded-lg mb-3 shadow-inner border border-black/20" 
                                 style="background-color: {{ hex }};"></div>
                            <p class="text-white font-mono text-sm font-medium text-center">{{ hex }}</p>
                            <p class="text-white font-mono text-sm font-medium text-center">{{ percentage[loop.index0] }}</p>
                            <p class="text-venus/60 text-xs text-center mt-1">Click to copy</p>
                        </div>
                        
                        <!-- Copy Notification -->
                        <div x-show="copied" x-transition 
                             class="absolute inset-0 flex items-center justify-center bg-black/70 rounded-xl">
                            <span class="text-white font-semibold text-sm">Copied!</span>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endif %}

            {% if palette_img %}
            <!-- Download Section -->
            <div class="glass-effect rounded-2xl p-6 shadow-xl text-center">
                <h3 class="text-lg font-semibold text-white mb-4">Download Palette</h3>
                <div class="mb-6">
                    <img src="data:image/png;base64,{{ palette_img }}" 
                         class="max-w-full h-auto rounded-lg shadow-lg mx-auto"
                         alt="Color palette">
                </div>
                <a href="data:image/png;base64,{{ palette_img }}" download="color-palette.png"
                   class="inline-flex items-center px-6 py-3 bg-gradient-to-r from-universe to-planetary hover:from-planetary hover:to-universe text-white font-semibold rounded-xl transition-all duration-300 transform hover:scale-105 shadow-lg">
                    <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                    </svg>
                    Download PNG
                </a>
            </div>
            {% endif %}

            {% if error %}
            <!-- Error Message -->
            <div class="bg-red-500/20 border border-red-400/30 backdrop-blur-sm rounded-2xl p-6">
                <div class="flex items-center">
                    <svg class="w-6 h-6 text-red-400 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    <p class="text-red-200">{{ error }}</p>
                </div>
            </div>
            {% endif %}

            <!-- Try Again Button -->
            <div class="text-center pt-4">
                <button @click="window.location.reload()" 
                        class="text-venus/80 hover:text-white transition-colors duration-300 text-sm underline">
                    Extract colors from another image
                </button>
            </div>
        </div>
        {% endif %}
    </div>

    <!-- Footer -->
    <footer class="text-center py-8 mt-16 border-t border-venus/10">
       
    </footer>

    <script>
        function colorExtractor() {
            return {
                selectedFile: null,
                isLoading: false,
                
                handleFileSelect(event) {
                    const file = event.target.files[0];
                    this.selectedFile = file ? file.name : null;
                },
                
                copyToClipboard(text) {
                    navigator.clipboard.writeText(text).then(() => {
                        console.log('Color copied:', text);
                    }).catch(err => {
                        console.error('Copy failed:', err);
                    });
                }
            }
        }
        
        // Hide loading state when page loads with results
        document.addEventListener('DOMContentLoaded', function() {
            // If there are results on page load, we're not loading
            if (document.querySelector('[x-data="colorExtractor()"]')) {
                const app = Alpine.$data(document.querySelector('[x-data="colorExtractor()"]'));
                if (app) {
                    app.isLoading = false;
                }
            }
        });
        
        var redSlider = document.getElementById("redSlider");
        var greenSlider = document.getElementById("greenSlider");
        var blueSlider = document.getElementById("blueSlider");
        
        var redOutput = document.getElementById("redValue");
        redOutput.innerHTML = redSlider.value;
        var greenOutput = document.getElementById("greenValue");
        greenOutput.innerHTML = greenSlider.value;
        var blueOutput = document.getElementById("blueValue");
        blueOutput.innerHTML = blueSlider.value;

        redSlider.oninput = function() {
            redOutput.innerHTML = this.value;
            document.getElementById("hiddenRed").value = this.value;
        }
        greenSlider.oninput = function() {
            greenOutput.innerHTML = this.value;
            document.getElementById("hiddenGreen").value = this.value;
        }
        blueSlider.oninput = function() {
            blueOutput.innerHTML = this.value;
            document.getElementById("hiddenBlue").value = this.value;
        }
    </script>
</body>
</html>
"""

def generate_palette_image(colors, width=400, height=100):
    """
    Membuat gambar palet warna dari list warna.
    """
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
    """
    Mengubah gambar PIL menjadi string base64 untuk ditampilkan di HTML.
    """
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    base64_img = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return base64_img

def adjust_image_colors(img: Image.Image, red_offset: int, green_offset: int, blue_offset: int) -> Image.Image:
    """
    Mengubah warna gambar dengan menambahkan offset pada RGB setiap pixel.
    """
    pixels = img.load()
    width, height = img.size
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            r = min(255, max(0, r + red_offset))
            g = min(255, max(0, g + green_offset))
            b = min(255, max(0, b + blue_offset))
            pixels[x, y] = (r, g, b)
    return img

@app.route('/', methods=['GET'])
def index():
    """
    Menampilkan halaman utama dengan form upload gambar.
    """
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload():
    """
    Proses upload gambar, ekstrak warna, buat gambar palet,
    dan tampilkan hasilnya.
    """
    uploaded_base64 = None

    if 'image' not in request.files:
        return render_template_string(HTML_TEMPLATE, error="Tidak ada file gambar yang diupload.")

    image_file = request.files['image']
    if image_file.filename == '':
        return render_template_string(HTML_TEMPLATE, error="Tidak ada file yang dipilih.")

    try:
        img = Image.open(image_file.stream).convert("RGB")
        uploaded_base64 = image_to_base64(img)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_image_file:
            img.save(temp_image_file.name, format='PNG')
            temp_file_path = temp_image_file.name

        colors = []
        try:
            colors = extract_colors(temp_file_path, palette_size=4)
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        
        frequencies = [f"{s.freq * 100:.2f}%" for s in colors]

        palette_img = generate_palette_image(colors)
        palette_base64 = image_to_base64(palette_img)

        hex_colors = [f'#{c.rgb[0]:02x}{c.rgb[1]:02x}{c.rgb[2]:02x}' for c in colors]

        return render_template_string(
            HTML_TEMPLATE,
            uploaded_img=uploaded_base64,
            palette_img=palette_base64,
            hex_colors=hex_colors,
            percentage=frequencies
        )
    except Exception as e:
        return render_template_string(
            HTML_TEMPLATE,
            uploaded_base64=uploaded_base64,
            error=f"Terjadi error saat ekstraksi warna: {e}"
        )

if __name__ == '__main__':
    app.run(debug=True)