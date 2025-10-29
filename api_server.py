import os
import glob
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json

# --- Load Configuration ---
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    PATHS = config['paths']
except FileNotFoundError:
    print("FATAL ERROR: config.json not found. Server cannot start.")
    exit(1)
except json.JSONDecodeError:
    print("FATAL ERROR: config.json is not valid JSON. Server cannot start.")
    exit(1)

# --- Configuration from config.json ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MOCKUP_DIR = os.path.join(PROJECT_ROOT, PATHS.get('mockup_output_dir', 'generated_mockups'))
TECHPACK_DIR = os.path.join(PROJECT_ROOT, PATHS.get('pdf_output_dir', 'generated_techpacks'))
EXCEL_DIR = os.path.join(PROJECT_ROOT, PATHS.get('excel_dir', 'excel_files'))
FABRIC_SWATCH_DIR = os.path.join(PROJECT_ROOT, PATHS.get('fabric_swatch_dir', 'fabric_swatches'))

# --- Initialize Flask App ---
app = Flask(__name__)
CORS(app) # Standard CORS for safety

print(f"--- Masco Mockup API Server ---")
print(f"Watching Mockups in: {MOCKUP_DIR}")
print(f"Watching Techpacks in: {TECHPACK_DIR}")
print(f"Watching Excels in: {EXCEL_DIR}")
print(f"Watching Swatches in: {FABRIC_SWATCH_DIR}")
print("-----------------------------------")
print(f"SERVER RUNNING! Open this link in your browser:")
print(f"http://127.0.0.1:5000")
print("-----------------------------------")


def find_file(directory, base_filename):
    """Finds a file with common image extensions."""
    extensions = ['.jpg', '.png', '.jpeg', '.webp']
    for ext in extensions:
        path = os.path.join(directory, f"{base_filename}{ext}")
        if os.path.exists(path):
            return f"{base_filename}{ext}"
    return None

def find_fabric_details_from_report(excel_path, ref_code):
    """
    Smarter function to read complex Excel reports.
    It scans for 'Job No' and 'Style' labels.
    """
    try:
        df = pd.read_excel(excel_path, header=None)
        df = df.fillna("") 
        fabrication = f"Job No '{ref_code}' not found in Excel."
        excel_found = False

        for row_index in range(df.shape[0]):
            for col_index in range(df.shape[1]):
                cell_value = str(df.iloc[row_index, col_index]).strip()
                
                if cell_value == "Job No":
                    if col_index + 1 < df.shape[1]:
                        job_no_from_file = str(df.iloc[row_index, col_index + 1]).strip()
                        
                        if job_no_from_file == ref_code:
                            print(f"Found matching Job No at ({row_index}, {col_index+1})")
                            excel_found = True
                            
                            if row_index + 1 < df.shape[0]:
                                style_label = str(df.iloc[row_index + 1, col_index]).strip()
                                if style_label == "Style":
                                    style_value = str(df.iloc[row_index + 1, col_index + 1]).strip()
                                    fabrication = style_value
                                    print(f"Found Style: {fabrication}")
                                    return fabrication, True
                            
                            fabrication = "Job No found, but 'Style' label is in an unexpected place."
                            return fabrication, True

        return fabrication, excel_found

    except Exception as e:
        print(f"CRITICAL ERROR reading Excel {excel_path}: {e}")
        return "Error reading Excel file.", False

def find_all_mockups_by_ref(ref_code):
    """
    Finds all mockups for a given ref code and groups them by category.
    """
    all_mockups = {
        "men": [],
        "women": [],
        "kids": []
    }
    
    # General search pattern for all mockups of this ref
    mockup_search_pattern = os.path.join(MOCKUP_DIR, f"SRX Mockup_*_{ref_code}.png")
    
    print(f"Scanning for all mockups matching: {mockup_search_pattern}")

    for mockup_path in glob.glob(mockup_search_pattern):
        mockup_filename = os.path.basename(mockup_path)
        
        prefix = "SRX Mockup_"
        suffix = f"_{ref_code}.png"
        
        if not (mockup_filename.startswith(prefix) and mockup_filename.endswith(suffix)):
            continue

        # Extract the full garment name (e.g., "men_polo", "women_tshirt")
        mockup_name = mockup_filename[len(prefix):-len(suffix)]
        
        # Determine category
        category = None
        if mockup_name.startswith("men"):
            category = "men"
        elif mockup_name.startswith("women"):
            category = "women"
        elif mockup_name.startswith("kids"):
            category = "kids"
        else:
            continue # Skip if it doesn't match a category

        # Check for techpack
        techpack_filename = f"SRX Techpack_{mockup_name}_{ref_code}.pdf"
        techpack_path = os.path.join(TECHPACK_DIR, techpack_filename)
        techpack_url_path = f"/static/techpacks/{techpack_filename}" if os.path.exists(techpack_path) else None

        # Add to the correct category list
        all_mockups[category].append({
            "garmentName": mockup_name.replace('_', ' ').title(), 
            "mockupUrl": f"/static/mockups/{mockup_filename}",
            "techpackUrl": techpack_url_path
        })

    print(f"Found {len(all_mockups['men'])} men, {len(all_mockups['women'])} women, {len(all_mockups['kids'])} kids mockups.")
    return all_mockups


# --- *** NEW: FRONTEND ROUTES *** ---

@app.route('/')
def serve_index():
    """Serves the index.html file."""
    return send_from_directory(PROJECT_ROOT, 'index.html')

@app.route('/app.js')
def serve_js():
    """Serves the app.js file."""
    return send_from_directory(PROJECT_ROOT, 'app.js')

@app.route('/Masco-Logo.png')
def serve_logo():
    """Serves the logo file."""
    return send_from_directory(PROJECT_ROOT, 'Masco-Logo.png')


# --- *** NEW: SINGLE API ROUTE *** ---
@app.route('/api/get-all-info')
def get_all_info():
    """
    API: Gets EVERYTHING in one go.
    Reads Excel, finds swatch, and finds all mockups.
    """
    ref_code = request.args.get('ref')
    if not ref_code:
        return jsonify({"error": "No 'ref' parameter provided"}), 400

    print(f"\n--- New Request for {ref_code} ---")
    
    # 1. Get Excel Details
    fabrication = "Fabrication details not found."
    excel_found = False
    excel_path = os.path.join(EXCEL_DIR, f"{ref_code} price.xlsx")
    
    if os.path.exists(excel_path):
        print(f"Reading Excel file: {excel_path}")
        fabrication, excel_found = find_fabric_details_from_report(excel_path, ref_code)
    else:
        print(f"Excel file not found: {excel_path}")
        fabrication = "Price file not found."

    # 2. Get Swatch Image
    swatch_filename = find_file(FABRIC_SWATCH_DIR, ref_code)
    swatch_url = None
    if swatch_filename:
        swatch_url = f"/static/swatches/{swatch_filename}"
    else:
        print(f"Swatch image not found for {ref_code} in {FABRIC_SWATCH_DIR}")
        swatch_url = f"https://placehold.co/400x400/eeeeee/cccccc?text={ref_code.replace('-', '%0A')}&font=inter"

    # 3. Get All Mockups (Men, Women, Kids)
    available_mockups = find_all_mockups_by_ref(ref_code)

    # 4. Return ONE response
    return jsonify({
        "refNo": ref_code,
        "style": fabrication,
        "imageUrl": swatch_url,
        "excelFound": excel_found,
        "availableMockups": available_mockups
    })


# --- Static File Routes (Unchanged) ---
@app.route('/static/mockups/<filename>')
def serve_mockup(filename):
    """Serves files from your 'generated_mockups' folder."""
    return send_from_directory(MOCKUP_DIR, filename)

@app.route('/static/techpacks/<filename>')
def serve_techpack(filename):
    """Serves files from your 'generated_techpacks' folder."""
    return send_from_directory(TECHPACK_DIR, filename)

@app.route('/static/swatches/<filename>')
def serve_swatch(filename):
    """Serves files from your 'fabric_swatches' folder."""
    return send_from_directory(FABRIC_SWATCH_DIR, filename)


# --- Run the Server ---
if __name__ == '__main__':
    app.run(port=5000, debug=True)

