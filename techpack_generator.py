import os
import sys
import json
from mockup_library import MockupGenerator
from PIL import Image as PILImage # For checking template dimensions
# ReportLab imports
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader

# --- Configuration ---
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    PATHS = config['paths']
    COORDS = config['techpack_coords']
except FileNotFoundError:
    print("FATAL ERROR: config.json not found.", file=sys.stderr)
    sys.exit(1)
except json.JSONDecodeError:
    print("FATAL ERROR: config.json is not valid JSON.", file=sys.stderr)
    sys.exit(1)
# ---------------------

def calculate_pdf_box(
    total_template_width_px, total_template_height_px,
    selection_x_px, selection_y_px,
    selection_width_px, selection_height_px,
    page_width_pt, page_height_pt
):
    """
    Converts pixel coordinates (from top-left) to PDF points (from bottom-left).
    """
    x_ratio = selection_x_px / total_template_width_px
    y_ratio = selection_y_px / total_template_height_px
    width_ratio = selection_width_px / total_template_width_px
    height_ratio = selection_height_px / total_template_height_px
    
    pdf_width = width_ratio * page_width_pt
    pdf_height = height_ratio * page_height_pt
    pdf_x = x_ratio * page_width_pt
    
    pdf_y_top = (1 - y_ratio) * page_height_pt
    pdf_y_bottom = pdf_y_top - pdf_height
    
    return (pdf_x, pdf_y_bottom, pdf_width, pdf_height)

def create_techpack_pdf(mockup_image_object, mockup_name, fabric_ref, techpack_template_path):
    """
    Creates the final PDF by overlaying the mockup onto the DYNAMIC template.
    """
    os.makedirs(PATHS['pdf_output_dir'], exist_ok=True)
    pdf_filename = f"SRX Techpack_{mockup_name}_{fabric_ref}.pdf"
    pdf_path = os.path.join(PATHS['pdf_output_dir'], pdf_filename)

    page_width, page_height = A4
    pdf_x, pdf_y, pdf_width, pdf_height = calculate_pdf_box(
        COORDS['total_template_width_px'],
        COORDS['total_template_height_px'],
        COORDS['selection_x_px'],
        COORDS['selection_y_px'],
        COORDS['selection_width_px'],
        COORDS['selection_height_px'],
        page_width,
        page_height
    )
    
    c = canvas.Canvas(pdf_path, pagesize=A4)

    try:
        # 1. Draw the full-page template first
        c.drawImage(
            techpack_template_path, 0, 0,
            width=page_width, height=page_height,
            preserveAspectRatio=True, anchor='c'
        )
        
        # 2. Draw the generated mockup on top
        mockup_img_reader = ImageReader(mockup_image_object)
        c.drawImage(
            mockup_img_reader, pdf_x, pdf_y,
            width=pdf_width, height=pdf_height,
            preserveAspectRatio=True, mask='auto'
        )
        
        c.save()
        print(f"\nSuccessfully generated techpack:\n{pdf_path}\n")
        return pdf_path
    except Exception as e:
        print(f"Error: Could not draw images on PDF. {e}", file=sys.stderr)
        print(f"Please ensure your template '{techpack_template_path}' exists and is valid.", file=sys.stderr)
        if os.path.exists(pdf_path):
            os.remove(pdf_path) # Clean up failed PDF
        return None

def run_generator():
    """
    Main function to run the full techpack generation workflow.
    """
    print("--- SRX Techpack Generator ---")

    try:
        fabric_ref = input("Enter Fabric Ref Code (e.g., FAB-101): ").strip()
        mockup_name = input("Enter Garments Type (e.g., men polo): ").strip()
        
        # --- *** NEW: Get Scaling Factor *** ---
        try:
            scale_input = input("Enter fabric scale (e.g., 0.5 for half, 1.0 for normal): ").strip()
            if not scale_input:
                scaling_factor = 1.0
            else:
                scaling_factor = float(scale_input)
            if scaling_factor <= 0:
                print("Warning: Scale must be > 0. Defaulting to 1.0.")
                scaling_factor = 1.0
        except ValueError:
            print("Error: Invalid scale. Defaulting to 1.0.")
            scaling_factor = 1.0
        # --- *** END NEW SECTION *** ---

        if not fabric_ref or not mockup_name:
            print("Error: Both fields are required.", file=sys.stderr)
            return
        
        # --- 1. Find the correct techpack template ---
        template_filename = f"techpack_{mockup_name}.jpg"
        template_path = os.path.join(PATHS['techpack_template_dir'], template_filename)
        
        if not os.path.exists(template_path):
            print(f"Error: Techpack template not found.", file=sys.stderr)
            print(f"Looked for: {template_path}", file=sys.stderr)
            print(f"Please check your 'techpack_templates' folder.", file=sys.stderr)
            return
        print(f"Using template: {template_path}")

        # --- 2. Step 1: Generate the mockup image IN MEMORY ---
        print("\n--- Step 1: Generating Mockup Image ---")
        generator = MockupGenerator()
        
        # Pass the new scaling_factor
        mockup_image_object = generator.generate_mockup_image_object(fabric_ref, mockup_name, scaling_factor)

        if not mockup_image_object:
            print("Error: Mockup generation failed. Cannot proceed to PDF.", file=sys.stderr)
            print(f"Please ensure 'mockups/{mockup_name}.png' and 'masks/{mockup_name}_mask.png' exist.", file=sys.stderr)
            return
        
        # --- 3. Step 2: Generate the techpack PDF ---
        print("\n--- Step 2: Generating Techpack PDF ---")
        create_techpack_pdf(mockup_image_object, mockup_name, fabric_ref, template_path)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)

if __name__ == "__main__":
    run_generator()