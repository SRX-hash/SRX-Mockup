import sys
from mockup_library import MockupGenerator

def main():
    """
    Main function to run the mockup generator.
    """
    print("--- SRX Mockup Generator ---")

    try:
        # 1. Get user input
        fabric_ref = input("Enter Fabric Ref Code (e.g., FAB-101): ").strip()
        mockup_name = input("Enter Garments Type (e.g., mens_tshirt): ").strip()
        
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
        
        # 2. Initialize generator
        generator = MockupGenerator()
        
        # 3. Run generator (now passing scaling_factor)
        generator.create_mockup(fabric_ref, mockup_name, scaling_factor)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()