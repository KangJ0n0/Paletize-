from flask import Flask, request, render_template_string, session, redirect, url_for
from Pylette import extract_colors
from PIL import Image, ImageDraw, ImageFont
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
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { 
            font-family: 'Poppins', sans-serif;
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
        /* Loading Animation Styles */
        .loading-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(255, 255, 255, 0.95);
            z-index: 9999;
            justify-content: center;
            align-items: center;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
        }
        .loading-container {
            text-align: center;
            padding: 2rem;
            background: white;
            border-radius: 1rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            transform: translateY(-10%);
            animation: slideUp 0.3s ease-out forwards;
        }
        .loading-spinner {
            width: 60px;
            height: 60px;
            border: 5px solid #e5e7eb;
            border-top: 5px solid #2563eb;
            border-radius: 50%;
            animation: spin 1s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite;
            margin: 0 auto;
        }
        .loading-text {
            margin-top: 1.25rem;
            color: #1e40af;
            font-weight: 600;
            font-size: 1.125rem;
            letter-spacing: 0.025em;
        }
        .loading-subtext {
            margin-top: 0.5rem;
            color: #6b7280;
            font-size: 0.875rem;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        @keyframes slideUp {
            from { 
                opacity: 0;
                transform: translateY(0);
            }
            to { 
                opacity: 1;
                transform: translateY(-10%);
            }
        }
        .fade-in {
            animation: fadeIn 0.3s ease-in;
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
    </style>
</head>
<body class="min-h-screen">
    <!-- Loading Overlay -->
    <div id="loadingOverlay" class="loading-overlay">
        <div class="loading-container">
            <div class="loading-spinner"></div>
            <div class="loading-text">Processing Image</div>
            <div class="loading-subtext">Please wait while we process your image...</div>
        </div>
    </div>

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
        // Loading Overlay Functions
        function showLoading() {
            const overlay = document.getElementById('loadingOverlay');
            overlay.style.display = 'flex';
            document.body.style.overflow = 'hidden';
            // Add loading dots animation
            let dots = 0;
            const loadingText = overlay.querySelector('.loading-text');
            const originalText = loadingText.textContent;
            const dotInterval = setInterval(() => {
                dots = (dots + 1) % 4;
                loadingText.textContent = originalText + '.'.repeat(dots);
            }, 500);
            // Store interval ID for cleanup
            overlay.dataset.dotInterval = dotInterval;
        }

        function hideLoading() {
            const overlay = document.getElementById('loadingOverlay');
            // Clear the dots animation
            if (overlay.dataset.dotInterval) {
                clearInterval(parseInt(overlay.dataset.dotInterval));
            }
            overlay.style.display = 'none';
            document.body.style.overflow = 'auto';
        }

        // Modify form submissions to show loading
        document.addEventListener('DOMContentLoaded', function() {
            const forms = document.querySelectorAll('form');
            forms.forEach(form => {
                form.addEventListener('submit', function() {
                    showLoading();
                });
            });
        });

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
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { 
            font-family: 'Poppins', sans-serif;
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
            padding: 1.5rem;
            background-color: #f8fafc;
            border-radius: 1rem;
            margin-bottom: 1rem;
            transition: all 0.2s ease;
            border: 1px solid #e2e8f0;
        }
        .slider-container:hover {
            background-color: #f1f5f9;
            transform: translateY(-1px);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        .slider-container.active {
            background-color: #f1f5f9;
            border-color: #2563eb;
        }
        .slider-label {
            display: flex;
            align-items: center;
            margin-bottom: 1rem;
            font-weight: 500;
            color: #1e293b;
        }
        .color-indicator {
            width: 24px;
            height: 24px;
            border-radius: 6px;
            margin-right: 0.75rem;
            border: 2px solid #e2e8f0;
        }
        .red-indicator { background-color: #ef4444; }
        .green-indicator { background-color: #22c55e; }
        .blue-indicator { background-color: #3b82f6; }
        
        input[type="range"] {
            -webkit-appearance: none;
            width: 100%;
            height: 8px;
            background: #e2e8f0;
            border-radius: 4px;
            outline: none;
            margin: 1rem 0;
        }
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 24px;
            height: 24px;
            background: white;
            border-radius: 50%;
            cursor: pointer;
            transition: all 0.2s;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            border: 2px solid #2563eb;
        }
        input[type="range"]::-webkit-slider-thumb:hover {
            transform: scale(1.1);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .value-display {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: white;
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
            border: 1px solid #e2e8f0;
            margin-top: 0.5rem;
        }
        .value-number {
            font-family: 'Poppins', monospace;
            font-weight: 600;
            color: #1e293b;
            min-width: 3rem;
            text-align: right;
        }
        .value-label {
            color: #64748b;
            font-size: 0.875rem;
        }
        .reset-button {
            position: relative;
            overflow: hidden;
        }
        .reset-button::after {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 50%;
            transform: translate(-50%, -50%);
            transition: width 0.3s, height 0.3s;
        }
        .reset-button:active::after {
            width: 200%;
            height: 200%;
        }
        /* Loading Animation Styles */
        .loading-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(255, 255, 255, 0.95);
            z-index: 9999;
            justify-content: center;
            align-items: center;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
        }
        .loading-container {
            text-align: center;
            padding: 2rem;
            background: white;
            border-radius: 1rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            transform: translateY(-10%);
            animation: slideUp 0.3s ease-out forwards;
        }
        .loading-spinner {
            width: 60px;
            height: 60px;
            border: 5px solid #e5e7eb;
            border-top: 5px solid #2563eb;
            border-radius: 50%;
            animation: spin 1s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite;
            margin: 0 auto;
        }
        .loading-text {
            margin-top: 1.25rem;
            color: #1e40af;
            font-weight: 600;
            font-size: 1.125rem;
            letter-spacing: 0.025em;
        }
        .loading-subtext {
            margin-top: 0.5rem;
            color: #6b7280;
            font-size: 0.875rem;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        @keyframes slideUp {
            from { 
                opacity: 0;
                transform: translateY(0);
            }
            to { 
                opacity: 1;
                transform: translateY(-10%);
            }
        }
        .fade-in {
            animation: fadeIn 0.3s ease-in;
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
    </style>
</head>
<body class="min-h-screen">
    <!-- Loading Overlay -->
    <div id="loadingOverlay" class="loading-overlay">
        <div class="loading-container">
            <div class="loading-spinner"></div>
            <div class="loading-text">Processing Image</div>
            <div class="loading-subtext">Please wait while we process your image...</div>
        </div>
    </div>

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
        <!-- Upload Form -->
        <div class="bg-white rounded-xl shadow-sm border p-8">
            <form action="/upload_edit" method="POST" enctype="multipart/form-data" id="uploadForm">
                <div class="mb-6">
                    <label class="block text-lg font-medium text-gray-700 mb-3">Choose Image to Edit</label>
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

                <button type="submit" 
                        class="w-full bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 transition-colors text-lg font-medium">
                    Upload and Edit Image
                </button>
            </form>
        </div>

        <script>
            // Loading Overlay Functions
            function showLoading() {
                const overlay = document.getElementById('loadingOverlay');
                overlay.style.display = 'flex';
                document.body.style.overflow = 'hidden';
            }

            function hideLoading() {
                const overlay = document.getElementById('loadingOverlay');
                overlay.style.display = 'none';
                document.body.style.overflow = 'auto';
            }

            // Modify form submissions to show loading
            document.addEventListener('DOMContentLoaded', function() {
                const forms = document.querySelectorAll('form');
                forms.forEach(form => {
                    form.addEventListener('submit', function() {
                        showLoading();
                    });
                });
            });

            // Image Preview Functionality
            const imageInput = document.getElementById('imageInput');
            const uploadForm = document.getElementById('uploadForm');
            const dropZone = document.querySelector('.border-dashed');

            // Handle file selection
            imageInput.addEventListener('change', function(e) {
                if (e.target.files[0]) {
                    if (e.target.files[0].size > 10 * 1024 * 1024) { // 10MB limit
                        alert('File size exceeds 10MB limit');
                        e.target.value = '';
                    }
                }
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
                const file = e.dataTransfer.files[0];
                if (file) {
                    if (file.size > 10 * 1024 * 1024) { // 10MB limit
                        alert('File size exceeds 10MB limit');
                        return;
                    }
                    imageInput.files = e.dataTransfer.files;
                }
            });

            // Prevent form submission if no image is selected
            uploadForm.addEventListener('submit', function(e) {
                if (!imageInput.files.length) {
                    e.preventDefault();
                    alert('Please select an image first');
                }
            });
        </script>
        {% else %}
        
        <!-- Image Preview Section -->
        <div class="bg-white rounded-xl shadow-sm border p-8 mb-8">
            <div class="flex justify-between items-center mb-6">
                <h3 class="text-xl font-semibold text-gray-900">Image Preview</h3>
                <div>
                    <input type="file" name="image" accept="image/*" required id="changeImageInput" class="hidden" />
                    <button type="button" onclick="document.getElementById('changeImageInput').click()" 
                            class="bg-gray-600 text-white py-2 px-4 rounded-lg hover:bg-gray-700 transition-colors text-sm font-medium">
                        Change Image
                    </button>
                </div>
            </div>
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
            <div class="flex justify-between items-center mb-6">
                <h3 class="text-xl font-semibold text-gray-900">Adjust Colors</h3>
                <button type="button" onclick="resetSliders()" 
                        class="reset-button bg-gray-100 text-gray-600 py-2 px-4 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium flex items-center">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Reset All
                </button>
            </div>
            <form action="/adjust" method="POST" id="adjustForm">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <!-- Red -->
                    <div class="slider-container" id="redContainer">
                        <div class="slider-label">
                            <div class="color-indicator red-indicator"></div>
                            Red Channel
                        </div>
                        <input type="range" min="-255" max="255" value="{{ red_offset|default(0) }}" 
                               name="red_offset" id="redSlider" 
                               class="red-slider">
                        <div class="value-display">
                            <span class="value-label">Value</span>
                            <span id="redValue" class="value-number">{{ red_offset|default(0) }}</span>
                        </div>
                    </div>
                    
                    <!-- Green -->
                    <div class="slider-container" id="greenContainer">
                        <div class="slider-label">
                            <div class="color-indicator green-indicator"></div>
                            Green Channel
                        </div>
                        <input type="range" min="-255" max="255" value="{{ green_offset|default(0) }}" 
                               name="green_offset" id="greenSlider"
                               class="green-slider">
                        <div class="value-display">
                            <span class="value-label">Value</span>
                            <span id="greenValue" class="value-number">{{ green_offset|default(0) }}</span>
                        </div>
                    </div>
                    
                    <!-- Blue -->
                    <div class="slider-container" id="blueContainer">
                        <div class="slider-label">
                            <div class="color-indicator blue-indicator"></div>
                            Blue Channel
                        </div>
                        <input type="range" min="-255" max="255" value="{{ blue_offset|default(0) }}" 
                               name="blue_offset" id="blueSlider"
                               class="blue-slider">
                        <div class="value-display">
                            <span class="value-label">Value</span>
                            <span id="blueValue" class="value-number">{{ blue_offset|default(0) }}</span>
                        </div>
                    </div>
                </div>
                
                <div class="mt-8">
                    <button type="submit" 
                            class="w-full bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 transition-colors text-lg font-medium flex items-center justify-center">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                        </svg>
                        Apply Color Changes
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
        // Loading Overlay Functions
        function showLoading(message = 'Processing Image') {
            const overlay = document.getElementById('loadingOverlay');
            const loadingText = overlay.querySelector('.loading-text');
            loadingText.textContent = message;
            overlay.style.display = 'flex';
            document.body.style.overflow = 'hidden';
            
            // Add loading dots animation
            let dots = 0;
            const originalText = loadingText.textContent;
            const dotInterval = setInterval(() => {
                dots = (dots + 1) % 4;
                loadingText.textContent = originalText + '.'.repeat(dots);
            }, 500);
            // Store interval ID for cleanup
            overlay.dataset.dotInterval = dotInterval;
        }

        function hideLoading() {
            const overlay = document.getElementById('loadingOverlay');
            // Clear the dots animation
            if (overlay.dataset.dotInterval) {
                clearInterval(parseInt(overlay.dataset.dotInterval));
            }
            overlay.style.display = 'none';
            document.body.style.overflow = 'auto';
        }

        // Handle change image functionality
        const changeImageInput = document.getElementById('changeImageInput');
        if (changeImageInput) {
            changeImageInput.addEventListener('change', function(e) {
                if (e.target.files[0]) {
                    if (e.target.files[0].size > 10 * 1024 * 1024) {
                        alert('File size exceeds 10MB limit');
                        e.target.value = '';
                        return;
                    }
                    
                    // Create and submit form
                    const form = document.createElement('form');
                    form.method = 'POST';
                    form.action = '/upload_edit';
                    form.enctype = 'multipart/form-data';
                    
                    const input = document.createElement('input');
                    input.type = 'file';
                    input.name = 'image';
                    input.files = e.target.files;
                    
                    form.appendChild(input);
                    document.body.appendChild(form);
                    
                    showLoading('Changing Image');
                    form.submit();
                }
            });
        }

        // Handle color adjustment form
        const adjustForm = document.getElementById('adjustForm');
        if (adjustForm) {
            adjustForm.addEventListener('submit', function(e) {
                showLoading('Adjusting Colors');
            });
        }

        function resetSliders() {
            const sliders = ['red', 'green', 'blue'];
            sliders.forEach(color => {
                const slider = document.getElementById(`${color}Slider`);
                const container = document.getElementById(`${color}Container`);
                slider.value = 0;
                container.classList.remove('active');
                updateSliderContainer(slider);
            });
        }
        
        // Enhanced slider functionality
        function updateSliderContainer(slider) {
            const container = slider.closest('.slider-container');
            const value = parseInt(slider.value);
            
            // Update active state
            document.querySelectorAll('.slider-container').forEach(c => c.classList.remove('active'));
            if (value !== 0) {
                container.classList.add('active');
            }
            
            // Update value display with color
            const valueDisplay = container.querySelector('.value-number');
            valueDisplay.textContent = value;
            if (value > 0) {
                valueDisplay.style.color = '#059669';
            } else if (value < 0) {
                valueDisplay.style.color = '#dc2626';
            } else {
                valueDisplay.style.color = '#1e293b';
            }
        }

        // Initialize sliders
        document.addEventListener('DOMContentLoaded', function() {
            const sliders = ['red', 'green', 'blue'];
            sliders.forEach(color => {
                const slider = document.getElementById(`${color}Slider`);
                if (slider) {
                    updateSliderContainer(slider);
                    slider.addEventListener('input', function() {
                        updateSliderContainer(this);
                    });
                }
            });
        });
    </script>
</body>
</html>
"""

def generate_palette_image(colors, width=800, height=300):
    """Generate a styled palette image from color list"""
    # Create image with white background
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # Calculate dimensions
    num_colors = len(colors)
    if num_colors == 0:
        return img
        
    # Draw color strip
    strip_height = 200
    swatch_width = width // num_colors
    
    # Draw color blocks
    for i, color in enumerate(colors):
        rgb_tuple = tuple(color.rgb)
        # Draw main color block
        draw.rectangle(
            [(i * swatch_width, 0), ((i + 1) * swatch_width, strip_height)],
            fill=rgb_tuple
        )
        
        # Draw hex label background
        label_y = strip_height
        label_height = height - strip_height
        draw.rectangle(
            [(i * swatch_width, label_y), ((i + 1) * swatch_width, height)],
            fill='#f8f8f8'
        )
        
        # Add hex text
        hex_color = f'#{color.rgb[0]:02x}{color.rgb[1]:02x}{color.rgb[2]:02x}'
        try:
            # Try to use a monospace font if available
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            # Fallback to default font
            font = ImageFont.load_default()
            
        # Calculate text position to center it
        text_bbox = draw.textbbox((0, 0), hex_color, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        text_x = (i * swatch_width) + (swatch_width - text_width) // 2
        text_y = label_y + (label_height - text_height) // 2
        
        # Draw text with shadow for better visibility
        draw.text((text_x + 1, text_y + 1), hex_color, fill='#00000033', font=font)  # Shadow
        draw.text((text_x, text_y), hex_color, fill='#333333', font=font)  # Main text
    
    # Add subtle border
    draw.rectangle([(0, 0), (width-1, height-1)], outline='#e5e7eb')
    
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
    try:
        if 'image' not in request.files:
            return render_template_string(EXTRACT_TEMPLATE, error="No image file uploaded")

        image_file = request.files['image']
        if image_file.filename == '':
            return render_template_string(EXTRACT_TEMPLATE, error="No file selected")

        # Save original image to session
        img = Image.open(image_file.stream).convert("RGB")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
            img.save(temp_file.name, format='PNG')
            session['original_image_path'] = temp_file.name
        
        # Extract colors
        colors = extract_colors(temp_file.name, palette_size=4)
        frequencies = [f"{s.freq * 100:.2f}%" for s in colors]
        hex_colors = [f'#{c.rgb[0]:02x}{c.rgb[1]:02x}{c.rgb[2]:02x}' for c in colors]
        
        # Generate palette image with new styling
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
        
        # Generate palette image with new styling
        palette_img = generate_palette_image(colors)
        
        return render_template_string(
            EDIT_TEMPLATE,
            original_img=image_to_base64(original_img),
            edited_img=image_to_base64(edited_img),
            palette_img=image_to_base64(palette_img),
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

@app.route('/upload_edit', methods=['POST'])
def upload_edit():
    """Handle image upload for edit page"""
    try:
        if 'image' not in request.files:
            return render_template_string(EDIT_TEMPLATE, error="No image file uploaded")

        image_file = request.files['image']
        if image_file.filename == '':
            return render_template_string(EDIT_TEMPLATE, error="No file selected")

        # Save original image to session
        img = Image.open(image_file.stream).convert("RGB")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
            img.save(temp_file.name, format='PNG')
            session['original_image_path'] = temp_file.name
        
        # Extract initial colors
        colors = extract_colors(temp_file.name, palette_size=4)
        frequencies = [f"{s.freq * 100:.2f}%" for s in colors]
        hex_colors = [f'#{c.rgb[0]:02x}{c.rgb[1]:02x}{c.rgb[2]:02x}' for c in colors]
        
        return render_template_string(
            EDIT_TEMPLATE,
            original_img=image_to_base64(img),
            hex_colors=hex_colors,
            percentage=frequencies
        )
    except Exception as e:
        return render_template_string(
            EDIT_TEMPLATE,
            error=f"Error processing image: {str(e)}"
        )

if __name__ == '__main__':
    app.run(debug=True)