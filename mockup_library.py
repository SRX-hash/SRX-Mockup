import os
import sys
import json
from PIL import Image, ImageOps, UnidentifiedImageError

# --- Load Configuration ---
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    PATHS = config['paths']
except FileNotFoundError:
    print("FATAL ERROR: config.json not found.", file=sys.stderr)
    sys.exit(1)
except json.JSONDecodeError:
    print("FATAL ERROR: config.json is not valid JSON.", file=sys.stderr)
    sys.exit(1)
# --------------------------

class MockupGenerator:
    """
    Handles the core logic of finding images and compositing them.
    Reads default paths from config.json
    """
    def __init__(self,
                 fabric_dir=PATHS['fabric_dir'],
                 mockup_dir=PATHS['mockup_dir'],
                 mask_dir=PATHS['mask_dir'],
                 output_dir=PATHS['mockup_output_dir']):
        
        self.fabric_dir = fabric_dir
        self.mockup_dir = mockup_dir
        self.mask_dir = mask_dir
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"MockupGenerator initialized. Outputting to: {self.output_dir}")

    def find_file(self, directory, ref_code, extensions):
        """
        Finds a file in a directory matching a ref_code, trying multiple extensions.
        """
        for ext in extensions:
            filename = f"{ref_code}{ext}"
            path = os.path.join(directory, filename)
            if os.path.exists(path):
                print(f"Found file: {path}")
                return path
        return None

    def _generate_core(self, fabric_ref, mockup_name, scaling_factor=1.0):
        """
        Private core function to generate the image.
        NEW LOGIC (Fit, Scale, and Center):
        1. Scales fabric proportionally to "fit" the mockup (like CSS 'contain').
        2. Applies scaling_factor to this "fit" size to allow zooming.
        3. Pastes the (potentially zoomed) fabric, centered, onto the mockup.
        """
        print(f"Starting mockup for Fabric: '{fabric_ref}', Mockup: '{mockup_name}'")
        common_exts = ['.jpg', '.png', '.jpeg', '.webp']

        try:
            # Find fabric
            fabric_path = self.find_file(self.fabric_dir, fabric_ref, common_exts)
            if not fabric_path:
                print(f"Error: Fabric file not found for ref: {fabric_ref}", file=sys.stderr)
                return None
            fabric_img = Image.open(fabric_path).convert("RGBA")
            fabric_width, fabric_height = fabric_img.size

            # Find mockup
            mockup_path = self.find_file(self.mockup_dir, mockup_name, common_exts)
            if not mockup_path:
                print(f"Error: Mockup file not found for name: {mockup_name}", file=sys.stderr)
                return None
            mockup_img = Image.open(mockup_path).convert("RGBA")
            mockup_width, mockup_height = mockup_img.size

            # Find and process mask
            mask_path = self.find_file(self.mask_dir, f"{mockup_name}_mask", ['.png', '.jpg', '.jpeg'])
            if not mask_path:
                print(f"Error: Mask file not found for: {mockup_name}_mask", file=sys.stderr)
                return None
            
            mask_img_raw = Image.open(mask_path).convert("L")
            # Threshold the mask to be a pure B&W silhouette
            mask_img = mask_img_raw.point(lambda x: 255 if x > 10 else 0, mode='1').convert('L')
            print("Mask has been thresholded to a pure silhouette.")
        
        except UnidentifiedImageError as e:
            print(f"Error: Could not read image file. It may be corrupt. {e}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"An error occurred opening files: {e}", file=sys.stderr)
            return None

        # --- *** 1. Calculate "Fit" Dimensions (like 'contain') *** ---
        # Get aspect ratios
        # Handle potential zero division error
        if mockup_height == 0 or fabric_height == 0:
            print("Error: Mockup or fabric height is zero. Cannot calculate ratio.", file=sys.stderr)
            return None
            
        mockup_ratio = mockup_width / mockup_height
        fabric_ratio = fabric_width / fabric_height

        if fabric_ratio > mockup_ratio:
            # Fabric is wider than mockup, so scale based on width
            fit_width = mockup_width
            fit_height = int(fit_width / fabric_ratio)
        else:
            # Fabric is taller or same ratio, so scale based on height
            fit_height = mockup_height
            fit_width = int(fit_height * fabric_ratio)
            
        print(f"Mockup size: {mockup_width}x{mockup_height}")
        print(f"Fabric 'fit' size (at scale 1.0): {fit_width}x{fit_height}")

        # --- *** 2. Apply "Zoom" (Scaling Factor) *** ---
        # A scale of 1.0 = "fit". > 1.0 = zoom in. < 1.0 = zoom out.
        if scaling_factor <= 0:
            print(f"Warning: Invalid scale {scaling_factor}. Defaulting to 1.0.")
            scaling_factor = 1.0
            
        scaled_width = int(fit_width * scaling_factor)
        scaled_height = int(fit_height * scaling_factor)
        print(f"Final scaled size (with zoom): {scaled_width}x{scaled_height}")

        # --- *** 3. Resize Fabric *** ---
        # Use LANCZOS for high-quality resizing
        if scaled_width > 0 and scaled_height > 0:
            resized_fabric_img = fabric_img.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
        else:
            print(f"Error: Final scaled size is invalid ({scaled_width}x{scaled_height}). Aborting.", file=sys.stderr)
            return None

        # --- *** 4. Create Fabric Layer and Paste Centered *** ---
        # Create a new transparent layer matching the mockup size
        fabric_layer = Image.new("RGBA", (mockup_width, mockup_height))
        
        # Calculate top-left coordinates to center the fabric
        paste_x = (mockup_width - scaled_width) // 2
        paste_y = (mockup_height - scaled_height) // 2
        print(f"Pasting fabric at ({paste_x}, {paste_y})")

        # Paste the resized fabric onto the transparent layer
        # The 'paste' function correctly handles negative coordinates (cropping)
        fabric_layer.paste(resized_fabric_img, (paste_x, paste_y))

        # --- 5. Validate and Resize Mask (if needed) ---
        if mockup_img.size != mask_img.size:
            print(f"Warning: Mockup and Mask sizes differ. Resizing mask to fit mockup.", file=sys.stderr)
            mask_img = mask_img.resize(mockup_img.size, Image.Resampling.LANCZOS)

        # --- 6. Composite ---
        # This composites the centered fabric layer (fabric_layer)
        # onto the mockup (mockup_img) using the mask (mask_img)
        final_img = Image.composite(fabric_layer, mockup_img, mask_img)
        
        return final_img

    def create_mockup(self, fabric_ref, mockup_name, scaling_factor=1.0):
        """
        Generates a mockup and SAVES IT TO DISK.
        """
        final_img = self._generate_core(fabric_ref, mockup_name, scaling_factor)
        if final_img is None: return None
            
        output_filename = f"SRX Mockup_{mockup_name}_{fabric_ref}.png"
        output_path = os.path.join(self.output_dir, output_filename)

        try:
            final_img.save(output_path)
            print(f"\nSuccessfully generated mockup:\n{output_path}\n")
            return output_path
        except Exception as e:
            print(f"Error saving final image: {e}", file=sys.stderr)
            return None

    def generate_mockup_image_object(self, fabric_ref, mockup_name, scaling_factor=1.0):
        """
        Generates a mockup and RETURNS THE PIL IMAGE OBJECT.
        """
        final_img = self._generate_core(fabric_ref, mockup_name, scaling_factor)
        if final_img is None: return None
        print(f"\nSuccessfully generated mockup object in memory.")
        return final_img

if __name__ == "__main__":
    print("This is the Mockup Library.")
    print("It is intended to be imported, not run directly.")
