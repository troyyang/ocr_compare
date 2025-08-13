import os
import logging
from PIL import Image

# Set up logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_images_preview(images_dir, output_image, scale_factor=0.15):
    """Generate a long preview image of all images in the directory
    
    Args:
        images_dir (str): Directory containing images
        output_image (str): Path to save the output preview image
        scale_factor (float): Factor to scale images by (default: 1.0)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if directory exists
        if not os.path.isdir(images_dir):
            logger.error(f"Directory does not exist: {images_dir}")
            return False
        
        # Get all image files
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff']
        image_files = [
            os.path.join(images_dir, f) for f in os.listdir(images_dir)
            if os.path.isfile(os.path.join(images_dir, f)) and 
            any(f.lower().endswith(ext) for ext in image_extensions)
        ]
        
        if not image_files:
            logger.error(f"No image files found in {images_dir}")
            return False
        
        # Sort files alphabetically
        image_files.sort()
        
        # Calculate total size needed
        max_width = 0
        total_height = 0
        loaded_images = []
        
        # First pass: load all images and calculate dimensions
        for img_path in image_files:
            try:
                img = Image.open(img_path)
                
                # Resize if scale factor is not 1.0
                if scale_factor != 1.0:
                    new_width = int(img.width * scale_factor)
                    new_height = int(img.height * scale_factor)
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                
                loaded_images.append(img)
                max_width = max(max_width, img.width)
                total_height += img.height
                
            except Exception as e:
                logger.warning(f"Could not process image {img_path}: {str(e)}")
                continue
        
        if not loaded_images:
            logger.error("No valid images could be processed")
            return False
        
        # Create empty canvas
        composite = Image.new("RGB", (max_width, total_height), "white")
        y_offset = 0
        
        # Second pass: composite images
        for img in loaded_images:
            composite.paste(img, (0, y_offset))
            y_offset += img.height
        
        # Save result
        composite.save(output_image, quality=85)
        logger.info(f"Preview image generated successfully: {output_image}")
        return True
        
    except Exception as e:
        logger.error(f"Image processing error: {str(e)}")
        return False

def generate_preview(input_path, output_image, scale_factor=0.15):
    """Generate preview from directory of images
    
    Args:
        input_path (str): Directory containing images
        output_image (str): Path to save the output preview image
        scale_factor (float): Factor to scale images by (default: 1.0)
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not os.path.isdir(input_path):
        logger.error(f"Input path is not a directory: {input_path}")
        return False
    
    return generate_images_preview(input_path, output_image, scale_factor)

def convert_png_to_rgba(input_path: str, output_path: str) -> None:
    """
    Convert a PNG image to RGBA mode using PIL.
    
    Args:
        input_path (str): Path to the input PNG file.
        output_path (str): Path to save the output RGBA PNG file.
    """
    try:
        # Open the PNG image
        img = Image.open(input_path)
        if img.mode != "RGBA":
            # Convert to RGBA mode
            img_rgba = img.convert("RGBA")
            # Save the converted image
            img_rgba.save(output_path, "PNG")
            logger.debug(f"Image converted to RGBA and saved as {output_path}")
    except Exception as e:
        logger.error(f"Error converting image: {e}")


# Example usage
if __name__ == "__main__":
    # Example: generate_preview("./my_images", "combined_preview.jpg", 0.5)
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python script.py <input_directory> <output_image> [scale_factor]")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_file = sys.argv[2]
    scale_factor = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    
    if generate_preview(input_dir, output_file, scale_factor):
        print(f"Successfully generated preview image: {output_file}")
    else:
        print("Failed to generate preview image")
        sys.exit(1)