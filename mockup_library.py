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
        This version scales the fabric, then tiles it to fill the mockup.
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

            # --- *** 1. Apply Scaling Factor *** ---
            if scaling_factor != 1.0 and scaling_factor > 0:
                print(f"Applying scaling factor of {scaling_factor} to fabric.")
                new_width = int(fabric_img.width * scaling_factor)
                new_height = int(fabric_img.height * scaling_factor)
                if new_width > 0 and new_height > 0:
                    # Use LANCZOS for high-quality resizing (zooming)
                    fabric_img = fabric_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                else:
                    print(f"Warning: Invalid scaling factor {scaling_factor} resulted in zero dimension. Ignoring.")
            
            # Find mockup
            mockup_path = self.find_file(self.mockup_dir, mockup_name, common_exts)
            if not mockup_path:
                print(f"Error: Mockup file not found for name: {mockup_name}", file=sys.stderr)
                return None
            mockup_img = Image.open(mockup_path).convert("RGBA")

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

        # --- *** 2. Tile the Scaled Fabric *** ---
        # This is the corrected logic. We tile the (now scaled) fabric.
        # This works for "zoom out" (tiling a small image) and
        # "zoom in" (tiling a huge image, which just pastes one tile).
        print("Tiling/Cropping scaled fabric to mockup size...")
        mockup_width, mockup_height = mockup_img.size
        fabric_width, fabric_height = fabric_img.size # This is the *scaled* fabric size

        fabric_layer = Image.new("RGBA", (mockup_width, mockup_height))

        for x in range(0, mockup_width, fabric_width):
            for y in range(0, mockup_height, fabric_height):
                fabric_layer.paste(fabric_img, (x, y))
        # --- *** END OF MODIFICATION *** ---

        # --- 3. Validate and Resize Mask (if needed) ---
        if mockup_img.size != mask_img.size:
            print(f"Warning: Mockup and Mask sizes differ. Resizing mask to fit mockup.", file=sys.stderr)
            mask_img = mask_img.resize(mockup_img.size, Image.Resampling.LANCZOS)

        # --- 4. Composite ---
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