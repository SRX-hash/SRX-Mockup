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
    DB_FILE = PATHS.get('fabric_database_file', 'fabric_database.xlsx')
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
DATABASE_PATH = os.path.join(EXCEL_DIR, DB_FILE)

# --- Initialize Flask App ---
app = Flask(__name__)
CORS(app)

print(f"--- Masco Mockup API Server ---")
print(f"Watching Database: {DATABASE_PATH}")
print(f"Watching Mockups in: {MOCKUP_DIR}")
print(f"Watching Swatches in: {FABRIC_SWATCH_DIR}")
print("-----------------------------------")


def find_file(directory, base_filename):
    """Finds a file with common image extensions."""
    extensions = ['.jpg', '.png', '.jpeg', '.webp']
    for ext in extensions:
        path = os.path.join(directory, f"{base_filename}{ext}")
        if os.path.exists(path):
            return f"{base_filename}{ext}"
    return None

def get_mockups_for_ref(ref_code):
    """
    Finds all mockups and techpacks for a given ref_code.
    This is the "one-fetch" logic.
    """
    mockups = {
        "men": [],
        "women": [],
        "kids": []
    }
    
    categories = mockups.keys()
    
    for category in categories:
        mockup_search_pattern = os.path.join(MOCKUP_DIR, f"SRX Mockup_{category}*_{ref_code}.png")
        
        for mockup_path in glob.glob(mockup_search_pattern):
            mockup_filename = os.path.basename(mockup_path)
            
            prefix = "SRX Mockup_"
            suffix = f"_{ref_code}.png"
            
            if mockup_filename.startswith(prefix) and mockup_filename.endswith(suffix):
                mockup_name = mockup_filename[len(prefix):-len(suffix)]
            else:
                continue

            techpack_filename = f"SRX Techpack_{mockup_name}_{ref_code}.pdf"
            techpack_path = os.path.join(TECHPACK_DIR, techpack_filename)
            
            techpack_url_path = None
            if os.path.exists(techpack_path):
                techpack_url_path = f"/static/techpacks/{techpack_filename}"

            mockups[category].append({
                "garmentName": mockup_name.replace('_', ' ').title(), 
                "mockupUrl": f"/static/mockups/{mockup_filename}",
                "techpackUrl": techpack_url_path
            })
            
    return mockups

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
@app.route('/api/find-fabrics')
def find_fabrics():
    """
    NEW API: Searches the master database by Fabrication OR Ref.
    """
    search_term = request.args.get('search', '').lower()
    if not search_term:
        return jsonify({"error": "No 'search' parameter provided"}), 400

    print(f"Searching database for: '{search_term}'")

    try:
        df = pd.read_excel(DATABASE_PATH)
    except FileNotFoundError:
        print(f"FATAL ERROR: Database file not found at {DATABASE_PATH}")
        return jsonify({"error": f"Database file not found: {DB_FILE}"}), 500
    except Exception as e:
        print(f"CRITICAL ERROR reading Excel {DATABASE_PATH}: {e}")
        return jsonify({"error": "Error reading Excel database."}), 500

    # Ensure columns exist and handle case sensitivity
    df.columns = [str(c).lower() for c in df.columns]
    
    # --- FIX for 'fabric ref' ---
    required_cols_set = {'fabric ref', 'style', 'fabrication'}
    
    if not required_cols_set.issubset(df.columns):
        print(f"Error: Database columns are wrong. Found: {df.columns}")
        return jsonify({"error": f"Database must have columns: Fabric ref, Style, Fabrication"}), 500
        
    df.rename(columns={'fabric ref': 'ref'}, inplace=True)
    # --- END OF FIX ---

    # --- NEW DUAL-SEARCH LOGIC ---
    df_str = df.astype(str)
    search_term_str = str(search_term) # ensure search term is string
    
    # 1. Try to find a direct match in the 'ref' column (case-insensitive)
    matches = df_str[df_str['ref'].str.lower() == search_term_str]
    
    # 2. If no direct ref match, search the 'fabrication' column (contains)
    if matches.empty:
        print(f"No direct ref match. Searching 'fabrication' column...")
        matches = df_str[df_str['fabrication'].str.lower().str.contains(search_term_str, na=False)]
    else:
        print(f"Found a direct match in 'ref' column.")
    # --- END NEW LOGIC ---

    results = []
    
    if matches.empty:
        print("No matches found.")
    else:
        print(f"Found {len(matches)} matches.")
        # Iterate over unique 'ref' codes from the matches
        unique_refs = matches['ref'].unique()
        
        for ref_code in unique_refs:
            # Get the first matching row for this ref to pull style info
            row = matches[matches['ref'] == ref_code].iloc[0]
            style = row['style']
            
            # Find the swatch image
            swatch_filename = find_file(FABRIC_SWATCH_DIR, ref_code)
            swatch_url = None
            if swatch_filename:
                swatch_url = f"/static/swatches/{swatch_filename}"
            else:
                print(f"Swatch image not found for {ref_code}")
                # Provide a placeholder
                swatch_url = f"https://placehold.co/400x400/eeeeee/cccccc?text={ref_code.replace('-', '%0A')}&font=inter"
            
            # Get all mockups for this ref
            mockups = get_mockups_for_ref(ref_code)
            
            results.append({
                "ref": ref_code,
                "style": style,
                "swatchUrl": swatch_url,
                "availableMockups": mockups
            })

    return jsonify(results)

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

