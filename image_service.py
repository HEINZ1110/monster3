from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QSize, Qt
from PIL import Image

class ImageService:
    """Handles image loading, saving, and thumbnail generation."""

    def load_image(self, file_path: str) -> QImage:
        """Loads an image from file."""
        try:
            img = QImage(file_path)
            if img.isNull():
                raise ValueError(f"Could not load image: {file_path}")
            return img
        except Exception as e:
            print(f"Error loading image {file_path}: {e}")
            return QImage()  # Return an empty image on error

    def generate_thumbnail(self, image: QImage, size: QSize) -> QPixmap:
        """Generates a thumbnail of the image."""
        return QPixmap.fromImage(image).scaled(size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    def get_image_size(self, file_path: str) -> tuple[int, int]:
        """Gets the width and height of an image in pixels."""
        try:
            img = Image.open(file_path)
            return img.size  # (width, height)
        except Exception as e:
            print(f"Error getting image size for {file_path}: {e}")
            return (0, 0)

    def convert_to_grayscale(self, image: QImage) -> QImage:
        """Converts a QImage to grayscale."""
        grayscale_image = image.convertToFormat(QImage.Format.Format_Grayscale8)
        return grayscale_image