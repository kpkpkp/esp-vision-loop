"""Photo preprocessing — crop to display region and resize for vision model."""

from PIL import Image


def preprocess_photo(photo_path, config, output_size=(512, 512)):
    """
    Crop and resize a photo to isolate the display region.

    If crop_region is set in config, crops to that bounding box.
    Always resizes to output_size for consistent vision model input.

    Args:
        photo_path: Path to the raw camera photo.
        config: Parsed device.yaml dict.
        output_size: Target (width, height) tuple.

    Returns:
        str: Path to the preprocessed photo (*_crop.jpg).
    """
    img = Image.open(photo_path)

    # Crop to display region if configured
    crop_region = config.get("capture", {}).get("crop_region")
    if crop_region:
        # crop_region is [x1, y1, x2, y2]
        img = img.crop(tuple(crop_region))

    # Resize to standard dimensions for the vision model
    img = img.resize(output_size, Image.LANCZOS)

    # Save alongside original
    out_path = photo_path.rsplit(".", 1)[0] + "_crop.jpg"
    img.save(out_path, "JPEG", quality=95)

    return out_path
