import os
import io
import sys
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image, ImageOps

def compress_image(image_field, max_width=1024, quality=80):
    """
    Compresses an uploaded image.
    - Preserves Exif orientation (prevents rotated mobile photos).
    - Resizes to strictly max_width (maintaining aspect ratio).
    - Converts to WebP for maximum size saving (while preserving good quality).
    - Returns the modified image ready to be saved by Django.
    """
    if not image_field or not getattr(image_field, 'file', None):
        return image_field

    # Open image using Pillow
    img = Image.open(image_field)
    
    # Preserve Exif orientation
    img = ImageOps.exif_transpose(img)
    
    # Needs conversion to RGB if saving as WebP/JPEG and mode is RGBA or P
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
        
    width, height = img.size
    if width > max_width:
        new_width = max_width
        new_height = int((max_width / width) * height)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
    output = io.BytesIO()
    # Save as WebP
    img.save(output, format='WEBP', quality=quality, optimize=True)
    output.seek(0)
    
    # Change filename extension
    old_name = image_field.name.rsplit('.', 1)[0]
    new_name = f"{os.path.basename(old_name)}.webp"

    # Replace the file in the field
    return InMemoryUploadedFile(
        output,
        'ImageField',
        new_name,
        'image/webp',
        sys.getsizeof(output),
        None
    )