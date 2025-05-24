from flask import Flask, request, render_template_string, send_file
from Pylette import extract_colors
from PIL import Image, ImageDraw
import io
import base64
import os
import tempfile # Import for creating temporary files

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Color Palette Extractor</title>
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #f0f2f5;
            color: #333;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px;
            min-height: 100vh;
            box-sizing: border-box;
        }
        h1, h2 {
            color: #2c3e50;
            margin-bottom: 20px;
        }
        form {
            background-color: #ffffff;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            display: flex;
            flex-direction: column;
            gap: 20px;
            align-items: center;
            margin-bottom: 30px;
            width: 100%;
            max-width: 500px;
        }
        input[type="file"] {
            border: 2px solid #3498db;
            padding: 12px;
            border-radius: 8px;
            width: 100%;
            box-sizing: border-box;
            background-color: #ecf0f1;
            color: #2c3e50;
            cursor: pointer;
        }
        button[type="submit"] {
            background-color: #3498db;
            color: white;
            padding: 12px 25px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1.1em;
            font-weight: bold;
            transition: background-color 0.3s ease, transform 0.2s ease;
            box-shadow: 0 4px 10px rgba(52, 152, 219, 0.3);
        }
        button[type="submit"]:hover {
            background-color: #2980b9;
            transform: translateY(-2px);
        }
        img {
            border: 2px solid #ddd;
            border-radius: 8px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
            margin-top: 15px;
        }
        .color-box-container {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 15px;
            margin-top: 20px;
            width: 100%;
            max-width: 600px;
        }
        .color-box {
            width: 120px; /* Slightly larger for better visibility */
            height: 120px;
            display: flex; /* Use flexbox for centering text */
            align-items: center; /* Center text vertically */
            justify-content: center; /* Center text horizontally */
            margin: 0; /* Remove individual margin as gap handles spacing */
            border-radius: 12px; /* More rounded corners */
            border: 2px solid #333;
            font-family: 'Inter', sans-serif;
            color: #333;
            text-align: center;
            font-weight: bold;
            font-size: 0.9em; /* Adjust font size */
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s ease;
        }
        .color-box:hover {
            transform: translateY(-5px);
        }
        a {
            background-color: #2ecc71;
            color: white;
            padding: 10px 20px;
            border-radius: 8px;
            text-decoration: none;
            margin-top: 20px;
            transition: background-color 0.3s ease;
            box-shadow: 0 4px 10px rgba(46, 204, 113, 0.3);
        }
        a:hover {
            background-color: #27ae60;
        }

        /* Responsive adjustments */
        @media (max-width: 600px) {
            form {
                padding: 20px;
            }
            .color-box {
                width: 100px;
                height: 100px;
                font-size: 0.8em;
            }
        }
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap" rel="stylesheet">
</head>
<body>
    <h1>Upload Image to Extract Colors</h1>
    <form action="/upload" method="POST" enctype="multipart/form-data">
        <input type="file" name="image" accept="image/*" required />
        <button type="submit">Extract</button>
    </form>

    {% if uploaded_img %}
        <h2>Uploaded Image:</h2>
        <img src="data:image/png;base64,{{ uploaded_img }}" style="max-width:300px; width: 100%; height: auto;"/><br>
    {% endif %}

    {% if palette_img %}
        <h2>Generated Color Palette:</h2>
        <img src="data:image/png;base64,{{ palette_img }}" alt="Palette Image" style="max-width:500px; width: 100%; height: auto;"/><br>
        <a href="data:image/png;base64,{{ palette_img }}" download="palette.png">Download Palette</a>
    {% endif %}

    {% if hex_colors %}
        <h2>Main Colors:</h2>
        <div class="color-box-container">
            {% for hex in hex_colors %}
                <div class="color-box" style="background-color: {{ hex }};">{{ hex }}</div>
            {% endfor %}
        </div>
    {% endif %}

    {% if error %}
        <p style="color: red; font-weight: bold; margin-top: 20px;">Error: {{ error }}</p>
    {% endif %}
</body>
</html>
"""

def generate_palette_image(colors, width=400, height=100):
    """
    Generates a PIL Image representing the color palette.
    """
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    num_colors = len(colors)
    if num_colors == 0: # Handle case with no colors to avoid division by zero
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
    Converts a PIL Image object to a base64 encoded string for embedding in HTML.
    """
    buffer = io.BytesIO()
    img.save(buffer, format="PNG") # Save as PNG for transparency and general web use
    base64_img = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return base64_img

@app.route('/', methods=['GET'])
def index():
    """
    Renders the main page with the image upload form.
    """
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload():
    """
    Handles image upload, extracts colors, generates palette image,
    and displays results.
    """
    uploaded_base64 = None # Initialize to None

    if 'image' not in request.files:
        # Handle case where no file is uploaded
        return render_template_string(HTML_TEMPLATE, error="No image file provided.")

    image_file = request.files['image']
    if image_file.filename == '':
        # Handle case where an empty file is selected
        return render_template_string(HTML_TEMPLATE, error="No selected file.")

    try:
        # Open the image using PIL
        img = Image.open(image_file.stream).convert("RGB")

        # Convert the uploaded image to base64 for display
        uploaded_base64 = image_to_base64(img)

        # --- Temporary File Handling for Pylette ---
        # Create a temporary file to save the image, as Pylette seems to prefer file paths.
        # tempfile.NamedTemporaryFile creates a unique temporary file.
        # 'delete=False' means we'll manually delete it in the finally block.
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_image_file:
            # Save the PIL Image to the temporary file
            img.save(temp_image_file.name, format='PNG')
            temp_file_path = temp_image_file.name # Get the path to the temporary file

        colors = [] # Initialize colors list
        try:
            # Pass the path to the temporary file to extract_colors
            colors = extract_colors(temp_file_path, palette_size=4)
        finally:
            # Ensure the temporary file is deleted, even if extract_colors fails
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        # --- End Temporary File Handling ---

        # Generate palette image from extracted colors
        palette_img = generate_palette_image(colors)
        palette_base64 = image_to_base64(palette_img)

        # Get hex codes for the extracted colors
        # FIX: Changed from c.hex to converting c.rgb tuple to hex string
        hex_colors = [f'#{c.rgb[0]:02x}{c.rgb[1]:02x}{c.rgb[2]:02x}' for c in colors]

        return render_template_string(
            HTML_TEMPLATE,
            uploaded_img=uploaded_base64,
            palette_img=palette_base64,
            hex_colors=hex_colors
        )
    except Exception as e:
        # Catch any other exceptions during processing and display an error message
        # Ensure uploaded_base64 is passed even on error
        return render_template_string(
            HTML_TEMPLATE,
            uploaded_img=uploaded_base64,
            error=f"An error occurred during color extraction: {e}"
        )

if __name__ == '__main__':
    # Run the Flask app in debug mode (for development)
    app.run(debug=True)
