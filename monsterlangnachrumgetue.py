#!/usr/bin/env python3
import sys
import os
import csv
import json
from datetime import datetime
from pathlib import Path
import shutil
from typing import List, Dict, Any, Optional, Set, Tuple

from PyQt6.QtCore import (
    Qt, QSize, QTimer, QEvent, QPropertyAnimation, QThreadPool,
    QMimeData, QUrl, QPoint, QRect, QModelIndex
)
from PyQt6.QtGui import (
    QPixmap, QImage, QDragEnterEvent, QDropEvent, QAction, 
    QIcon, QKeySequence, QPainter, QTransform, QColor, QFont
)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QFileDialog, QComboBox,
    QVBoxLayout, QHBoxLayout, QScrollArea, QLineEdit, QMessageBox,
    QPushButton, QCheckBox, QTabWidget, QStatusBar, QFormLayout, 
    QTableWidget, QTableWidgetItem, QDialog, QMainWindow, QListWidget,
    QListWidgetItem, QSplitter, QFrame, QSpinBox, QGroupBox, QHeaderView,
    QTextEdit, QMenu, QSizePolicy, QGridLayout, QToolBar, QToolButton,
    QDialogButtonBox, QSlider, QLayout
)


# Configuration paths
CONFIG_DIR = Path.home() / ".photo_catalog"
CONFIG_FILE = CONFIG_DIR / "config.json"
CATEGORIES_FILE = CONFIG_DIR / "categories.json"

# Ensure configuration directory exists
CONFIG_DIR.mkdir(exist_ok=True)

# Default categories for paper antiquities
DEFAULT_CATEGORIES = {
    "Type": [
        "Postcard", "Cabinet Card", "CDV", "Albumen Print", 
        "Daguerreotype", "Tintype", "Ambrotype", "Stereoview"
    ],
    "Era": [
        "Pre-1850", "1850-1900", "1900-1920", "1920-1950", 
        "1950-1980", "1980-2000", "Post-2000"
    ],
    "Condition": [
        "Mint", "Near Mint", "Excellent", "Very Good", "Good", 
        "Fair", "Poor", "Fragment"
    ],
    "Theme": [
        "Portrait", "Landscape", "Architecture", "Street Scene",
        "Transportation", "Industry", "Military", "Fashion",
        "Family", "Event", "Travel"
    ]
}

class ImageItem:
    """Class to represent an image item with all its metadata"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.filename = os.path.basename(file_path)
        self.categories: Dict[str, List[str]] = {}
        self.text = ""
        self.comment = ""
        self.condition = ""
        self.physical_size = ""
        self.image_size = (0, 0)  # (width, height) in pixels
        self.dpi = 0
        self._thumbnail: Optional[QPixmap] = None
        self._load_image_info()
    
    def _load_image_info(self):
        """Load image size information"""
        try:
            image = QImage(self.file_path)
            self.image_size = (image.width(), image.height())
            # DPI could be extracted from EXIF in a real implementation
            self.dpi = 300  # Default assumption
            self._calculate_physical_size()
        except Exception as e:
            print(f"Error loading image info: {e}")
    
    def _calculate_physical_size(self):
        """Calculate physical size based on pixels and DPI"""
        if self.dpi > 0:
            width_inches = self.image_size[0] / self.dpi
            height_inches = self.image_size[1] / self.dpi
            width_cm = width_inches * 2.54
            height_cm = height_inches * 2.54
            self.physical_size = f"{width_cm:.1f}cm x {height_cm:.1f}cm"
    
    def get_thumbnail(self, size=QSize(120, 120)):
        """Get a cached thumbnail of the image"""
        if not self._thumbnail:
            image = QImage(self.file_path)
            pixmap = QPixmap.fromImage(image)
            self._thumbnail = pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, 
                                           Qt.TransformationMode.SmoothTransformation)
        return self._thumbnail
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "file_path": self.file_path,
            "filename": self.filename,
            "categories": self.categories,
            "text": self.text,
            "comment": self.comment,
            "condition": self.condition,
            "physical_size": self.physical_size,
            "image_size": self.image_size,
            "dpi": self.dpi
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ImageItem':
        """Create an ImageItem from a dictionary"""
        item = cls(data["file_path"])
        item.categories = data.get("categories", {})
        item.text = data.get("text", "")
        item.comment = data.get("comment", "")
        item.condition = data.get("condition", "")
        item.physical_size = data.get("physical_size", "")
        item.image_size = data.get("image_size", (0, 0))
        item.dpi = data.get("dpi", 0)
        return item


class ImageListWidget(QListWidget):
    """Custom list widget for displaying images with thumbnails"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIconSize(QSize(100, 100))
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setSpacing(10)
        self.setAcceptDrops(True)
        self.setDragEnabled(False)  # We'll handle moves with buttons
        self.main_window = None  # Reference to main window

    def set_main_window(self, main_window):
        """Set reference to main window"""
        self.main_window = main_window

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events for files"""
        try:
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
        except Exception as e:
            print(f"Error in dragEnterEvent: {e}")
    
    def dragMoveEvent(self, event):
        """Handle drag move events"""
        try:
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
        except Exception as e:
            print(f"Error in dragMoveEvent: {e}")
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop events for files"""
        try:
            if event.mimeData().hasUrls():
                urls = event.mimeData().urls()
                file_paths = [url.toLocalFile() for url in urls]
                
                # Use direct reference to main window instead of parent
                if self.main_window:
                    self.main_window.add_images(file_paths)
                else:
                    # Try parent as fallback
                    parent = self.parent()
                    while parent and not hasattr(parent, 'add_images'):
                        parent = parent.parent()
                    
                    if parent and hasattr(parent, 'add_images'):
                        parent.add_images(file_paths)
                    else:
                        print("Error: Cannot find add_images method")
                
                event.acceptProposedAction()
        except Exception as e:
            print(f"Error in dropEvent: {e}")
    
    def get_selected_indices(self) -> List[int]:
        """Get the indices of selected items"""
        return [self.row(item) for item in self.selectedItems()]


class CategoryManager(QDialog):
    """Dialog for managing categories"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Category Manager")
        self.setMinimumSize(600, 400)
        
        self.categories = self.load_categories()
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Top section - add new category group
        top_group = QGroupBox("Add New Category Group")
        top_layout = QHBoxLayout()
        
        self.group_name_edit = QLineEdit()
        self.group_name_edit.setPlaceholderText("Enter new category group name")
        
        add_group_btn = QPushButton("Add Group")
        add_group_btn.clicked.connect(self.add_group)
        
        top_layout.addWidget(self.group_name_edit)
        top_layout.addWidget(add_group_btn)
        top_group.setLayout(top_layout)
        
        # Middle section - category groups in tabs
        self.tab_widget = QTabWidget()
        self.refresh_tabs()
        
        # Bottom buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                  QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_categories)
        buttons.rejected.connect(self.reject)
        
        layout.addWidget(top_group)
        layout.addWidget(self.tab_widget)
        layout.addWidget(buttons)
    
    def refresh_tabs(self):
        """Refresh all category tabs"""
        self.tab_widget.clear()
        
        for group_name, values in self.categories.items():
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            
            # Top of tab - add new category value
            value_layout = QHBoxLayout()
            value_edit = QLineEdit()
            value_edit.setPlaceholderText(f"Add new value to {group_name}")
            
            add_value_btn = QPushButton("Add Value")
            add_value_btn.clicked.connect(lambda checked, g=group_name, e=value_edit: 
                                         self.add_value(g, e.text()))
            
            delete_group_btn = QPushButton("Delete Group")
            delete_group_btn.clicked.connect(lambda checked, g=group_name:
                                            self.delete_group(g))
            
            value_layout.addWidget(value_edit)
            value_layout.addWidget(add_value_btn)
            value_layout.addWidget(delete_group_btn)
            tab_layout.addLayout(value_layout)
            
            # List of current values
            list_widget = QListWidget()
            for value in values:
                item = QListWidgetItem(value)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                list_widget.addItem(item)
            
            list_widget.itemChanged.connect(lambda item, g=group_name:
                                         self.value_changed(g, item))
            
            # Context menu for value deletion
            list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            list_widget.customContextMenuRequested.connect(
                lambda pos, lw=list_widget, g=group_name: 
                self.show_value_context_menu(pos, lw, g))
            
            tab_layout.addWidget(list_widget)
            self.tab_widget.addTab(tab, group_name)
    
    def add_group(self):
        """Add a new category group"""
        group_name = self.group_name_edit.text().strip()
        if not group_name:
            QMessageBox.warning(self, "Warning", "Please enter a group name")
            return
        
        if group_name in self.categories:
            QMessageBox.warning(self, "Warning", f"Group '{group_name}' already exists")
            return
        
        self.categories[group_name] = []
        self.group_name_edit.clear()
        self.refresh_tabs()
    
    def delete_group(self, group_name):
        """Delete a category group"""
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete the group '{group_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.categories[group_name]
            self.refresh_tabs()
    
    def add_value(self, group_name, value):
        """Add a new value to a category group"""
        value = value.strip()
        if not value:
            return
        
        if value in self.categories[group_name]:
            QMessageBox.warning(
                self, "Warning", f"Value '{value}' already exists in {group_name}")
            return
        
        self.categories[group_name].append(value)
        self.refresh_tabs()
        
        # Focus on the added tab
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == group_name:
                self.tab_widget.setCurrentIndex(i)
                break
    
    def value_changed(self, group_name, item):
        """Handle when a value is edited"""
        index = item.listWidget().row(item)
        new_value = item.text().strip()
        
        # Update the value if it's valid and not a duplicate
        if new_value and new_value not in self.categories[group_name]:
            self.categories[group_name][index] = new_value
        else:
            # Revert if invalid or duplicate
            if not new_value:
                QMessageBox.warning(self, "Warning", "Value cannot be empty")
            else:
                QMessageBox.warning(
                    self, "Warning", f"Value '{new_value}' already exists in {group_name}")
            
            # Block signals to prevent recursion
            item.listWidget().blockSignals(True)
            item.setText(self.categories[group_name][index])
            item.listWidget().blockSignals(False)
    
    def show_value_context_menu(self, pos, list_widget, group_name):
        """Show context menu for category values"""
        item = list_widget.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        delete_action = menu.addAction("Delete")
        action = menu.exec(list_widget.mapToGlobal(pos))
        
        if action == delete_action:
            index = list_widget.row(item)
            value = self.categories[group_name][index]
            
            reply = QMessageBox.question(
                self, "Confirm Deletion",
                f"Are you sure you want to delete '{value}' from {group_name}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                del self.categories[group_name][index]
                self.refresh_tabs()
                
                # Focus on the affected tab
                for i in range(self.tab_widget.count()):
                    if self.tab_widget.tabText(i) == group_name:
                        self.tab_widget.setCurrentIndex(i)
                        break
    
    def save_categories(self):
        """Save categories and close dialog"""
        try:
            with open(CATEGORIES_FILE, 'w') as f:
                json.dump(self.categories, f, indent=2)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save categories: {str(e)}")
    
    @staticmethod
    def load_categories():
        """Load categories from file or use defaults"""
        if CATEGORIES_FILE.exists():
            try:
                with open(CATEGORIES_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Use default categories if file doesn't exist or is invalid
        return DEFAULT_CATEGORIES.copy()


class ImagePreviewDialog(QDialog):
    """Dialog for image preview with manipulation options"""
    
    def __init__(self, images: List[ImageItem], parent=None):
        super().__init__(parent)
        self.images = images
        self.current_index = 0
        self.zoom_level = 1.0
        self.rotation = 0
        
        self.setWindowTitle("Image Preview")
        self.setMinimumSize(800, 600)
        self.init_ui()
        self.update_preview()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Image display
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidget(self.image_label)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        # Navigation
        nav_group = QGroupBox("Navigation")
        nav_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton("Previous")
        self.prev_btn.clicked.connect(self.show_previous)
        
        self.image_counter = QLabel("1 / 1")
        
        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self.show_next)
        
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.image_counter)
        nav_layout.addWidget(self.next_btn)
        nav_group.setLayout(nav_layout)
        
        # Zoom controls
        zoom_group = QGroupBox("Zoom")
        zoom_layout = QHBoxLayout()
        
        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        
        self.zoom_reset_btn = QPushButton("100%")
        self.zoom_reset_btn.clicked.connect(self.zoom_reset)
        
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        
        zoom_layout.addWidget(self.zoom_out_btn)
        zoom_layout.addWidget(self.zoom_reset_btn)
        zoom_layout.addWidget(self.zoom_in_btn)
        zoom_group.setLayout(zoom_layout)
        
        # Rotation controls
        rotation_group = QGroupBox("Rotation")
        rotation_layout = QHBoxLayout()
        
        self.rotate_left_btn = QPushButton("↺ 90°")
        self.rotate_left_btn.clicked.connect(self.rotate_left)
        
        self.rotate_right_btn = QPushButton("↻ 90°")
        self.rotate_right_btn.clicked.connect(self.rotate_right)
        
        rotation_layout.addWidget(self.rotate_left_btn)
        rotation_layout.addWidget(self.rotate_right_btn)
        rotation_group.setLayout(rotation_layout)
        
        # Add controls to layout
        controls_layout.addWidget(nav_group)
        controls_layout.addWidget(zoom_group)
        controls_layout.addWidget(rotation_group)
        
        # File info
        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.info_label.setStyleSheet("padding: 5px; background-color: #f0f0f0; border-radius: 3px;")
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        
        layout.addWidget(self.scroll_area)
        layout.addLayout(controls_layout)
        layout.addWidget(self.info_label)
        layout.addWidget(close_btn)
    
    def update_preview(self):
        """Update the image preview and info"""
        if not self.images:
            return
        
        image = self.images[self.current_index]
        pixmap = QPixmap(image.file_path)
        
        # Apply rotation if needed
        if self.rotation != 0:
            transform = QTransform().rotate(self.rotation)
            pixmap = pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        
        # Apply zoom if needed
        if self.zoom_level != 1.0:
            new_size = pixmap.size() * self.zoom_level
            pixmap = pixmap.scaled(new_size, Qt.AspectRatioMode.KeepAspectRatio, 
                                 Qt.TransformationMode.SmoothTransformation)
        
        self.image_label.setPixmap(pixmap)
        
        # Update image counter
        self.image_counter.setText(f"{self.current_index + 1} / {len(self.images)}")
        
        # Update info label
        img = image
        info_text = (
            f"<b>File:</b> {img.filename}<br>"
            f"<b>Size:</b> {img.image_size[0]}x{img.image_size[1]} pixels<br>"
            f"<b>Physical Size:</b> {img.physical_size}<br>"
            f"<b>Path:</b> {img.file_path}"
        )
        self.info_label.setText(info_text)
        
        # Enable/disable navigation buttons
        self.prev_btn.setEnabled(self.current_index > 0)
        self.next_btn.setEnabled(self.current_index < len(self.images) - 1)
    
    def show_next(self):
        """Show next image"""
        if self.current_index < len(self.images) - 1:
            self.current_index += 1
            self.update_preview()
    
    def show_previous(self):
        """Show previous image"""
        if self.current_index > 0:
            self.current_index -= 1
            self.update_preview()
    
    def zoom_in(self):
        """Zoom in the image"""
        self.zoom_level *= 1.2
        self.update_preview()
    
    def zoom_out(self):
        """Zoom out the image"""
        self.zoom_level /= 1.2
        self.update_preview()
    
    def zoom_reset(self):
        """Reset zoom level"""
        self.zoom_level = 1.0
        self.update_preview()
    
    def rotate_left(self):
        """Rotate image 90 degrees left"""
        self.rotation = (self.rotation - 90) % 360
        self.update_preview()
    
    def rotate_right(self):
        """Rotate image 90 degrees right"""
        self.rotation = (self.rotation + 90) % 360
        self.update_preview()


class CSVPreviewDialog(QDialog):
    """Dialog for previewing CSV data before export"""
    
    def __init__(self, images: List[ImageItem], parent=None):
        super().__init__(parent)
        self.images = images
        
        self.setWindowTitle("CSV Export Preview")
        self.setMinimumSize(900, 600)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "Preview of data to be exported to CSV. Check and confirm before export."
        )
        instructions.setStyleSheet("font-weight: bold; color: #555;")
        
        # Table widget
        self.table = QTableWidget()
        headers = ["Thumbnail", "Filename", "Physical Size", "Category", 
                  "Text", "Comment", "Condition"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 100)
        
        # Fill the table
        self.populate_table()
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | 
                                  QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addWidget(instructions)
        layout.addWidget(self.table)
        layout.addWidget(buttons)
    
    def populate_table(self):
        """Fill the table with image data"""
        self.table.setRowCount(len(self.images))
        
        for row, image in enumerate(self.images):
            # Thumbnail
            thumbnail = image.get_thumbnail(QSize(80, 80))
            thumbnail_label = QLabel()
            thumbnail_label.setPixmap(thumbnail)
            thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row, 0, thumbnail_label)
            
            # Filename
            self.table.setItem(row, 1, QTableWidgetItem(image.filename))
            
            # Physical size
            self.table.setItem(row, 2, QTableWidgetItem(image.physical_size))
            
            # Categories
            categories_text = ""
            for group, values in image.categories.items():
                if values:
                    categories_text += f"{group}: {', '.join(values)}; "
            self.table.setItem(row, 3, QTableWidgetItem(categories_text))
            
            # Text
            self.table.setItem(row, 4, QTableWidgetItem(image.text))
            
            # Comment
            self.table.setItem(row, 5, QTableWidgetItem(image.comment))
            
            # Condition
            self.table.setItem(row, 6, QTableWidgetItem(image.condition))
        
        # Adjust row heights
        for row in range(self.table.rowCount()):
            self.table.setRowHeight(row, 80)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.images: List[ImageItem] = []
        self.exported_images: List[ImageItem] = []
        self.categories = CategoryManager.load_categories()
        
        self.setWindowTitle("Photo Collection Manager")
        self.setMinimumSize(1200, 800)
        
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        # Central widget
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Split the window horizontally
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - Lists and controls
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # List 1 - Main image list
        list1_group = QGroupBox("Image Collection")
        list1_layout = QVBoxLayout()
        
        # List widget
        self.image_list = ImageListWidget()
        self.image_list.set_main_window(self)  # Set reference to main window
        self.image_list.itemSelectionChanged.connect(self.update_preview)
        
        # Buttons under list
        list1_buttons = QHBoxLayout()
        
        add_btn = QPushButton("Add Images")
        add_btn.clicked.connect(self.open_file_dialog)
        
        move_up_btn = QPushButton("▲")
        move_up_btn.clicked.connect(self.move_selected_up)
        
        move_down_btn = QPushButton("▼")
        move_down_btn.clicked.connect(self.move_selected_down)
        
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self.delete_selected)
        
        list1_buttons.addWidget(add_btn)
        list1_buttons.addWidget(move_up_btn)
        list1_buttons.addWidget(move_down_btn)
        list1_buttons.addWidget(delete_btn)
        
        list1_layout.addWidget(self.image_list)
        list1_layout.addLayout(list1_buttons)
        list1_group.setLayout(list1_layout)
        
        # List 2 - Exported images
        list2_group = QGroupBox("Exported Images")
        list2_layout = QVBoxLayout()
        
        self.exported_list = QListWidget()
        
        list2_buttons = QHBoxLayout()
        
        transfer_back_btn = QPushButton("Transfer Back")
        transfer_back_btn.clicked.connect(self.transfer_back_to_list1)
        
        list2_buttons.addWidget(transfer_back_btn)
        
        list2_layout.addWidget(self.exported_list)
        list2_layout.addLayout(list2_buttons)
        list2_group.setLayout(list2_layout)
        
        # Add both lists to the left layout
        left_layout.addWidget(list1_group, 2)  # 2/3 of the space
        left_layout.addWidget(list2_group, 1)  # 1/3 of the space
        
        # Right side - Preview and details
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Preview section
        preview_group = QGroupBox("Image Preview")
        preview_layout = QVBoxLayout()
        
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_content = QWidget()
        self.preview_layout = QFlowLayout()
        self.preview_content.setLayout(self.preview_layout)
        self.preview_scroll.setWidget(self.preview_content)
        
        preview_buttons = QHBoxLayout()
        
        open_preview_btn = QPushButton("Open Full Preview")
        open_preview_btn.clicked.connect(self.open_preview_dialog)
        
        preview_buttons.addWidget(open_preview_btn)
        preview_buttons.addStretch()
        
        preview_layout.addWidget(self.preview_scroll)
        preview_layout.addLayout(preview_buttons)
        preview_group.setLayout(preview_layout)
        
        # Details and metadata section
        details_group = QGroupBox("Image Details")
        details_layout = QVBoxLayout()
        
        # Form for editing metadata
        form_layout = QFormLayout()
        
        # Image info (non-editable)
        self.filename_label = QLabel()
        self.size_label = QLabel()
        self.phys_size_label = QLabel()
        
        form_layout.addRow("Filename:", self.filename_label)
        form_layout.addRow("Dimensions:", self.size_label)
        form_layout.addRow("Physical Size:", self.phys_size_label)
        
        # Editable fields
        self.text_edit = QLineEdit()
        self.text_edit.textChanged.connect(self.update_text)
        
        self.comment_edit = QTextEdit()
        self.comment_edit.setMaximumHeight(80)
        self.comment_edit.textChanged.connect(self.update_comment)
        
        self.condition_combo = QComboBox()
        self.condition_combo.currentTextChanged.connect(self.update_condition)
        
        form_layout.addRow("Text:", self.text_edit)
        form_layout.addRow("Comment:", self.comment_edit)
        form_layout.addRow("Condition:", self.condition_combo)
        
        # Category section
        category_layout = QVBoxLayout()
        
        category_header = QHBoxLayout()
        category_label = QLabel("Categories:")
        
        manage_categories_btn = QPushButton("Manage Categories")
        manage_categories_btn.clicked.connect(self.open_category_manager)
        
        category_header.addWidget(category_label)
        category_header.addWidget(manage_categories_btn)
        
        self.category_widgets = {}  # To store category widgets
        self.category_scroll = QScrollArea()
        self.category_scroll.setWidgetResizable(True)
        self.category_container = QWidget()
        self.category_form = QFormLayout(self.category_container)
        self.category_scroll.setWidget(self.category_container)
        
        category_layout.addLayout(category_header)
        category_layout.addWidget(self.category_scroll)
        
        # Add form and category layouts to details
        details_layout.addLayout(form_layout)
        details_layout.addLayout(category_layout)
        details_group.setLayout(details_layout)
        
        # Export section
        export_group = QGroupBox("Export Options")
        export_layout = QVBoxLayout()
        
        # Scan mode selection
        scan_layout = QHBoxLayout()
        scan_layout.addWidget(QLabel("Scan Mode:"))
        
        self.scan_mode_combo = QComboBox()
        self.scan_mode_combo.addItems([
            "Single", "Pair", "All", 
            "Group of X", "Alternate"
        ])
        self.scan_mode_combo.currentTextChanged.connect(self.scan_mode_changed)
        
        scan_layout.addWidget(self.scan_mode_combo)
        
        # Interval settings (initially hidden)
        self.interval_widget = QWidget()
        interval_layout = QHBoxLayout(self.interval_widget)
        interval_layout.setContentsMargins(0, 0, 0, 0)
        
        interval_layout.addWidget(QLabel("Interval:"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setMinimum(1)
        self.interval_spin.setMaximum(100)
        self.interval_spin.setValue(1)
        interval_layout.addWidget(self.interval_spin)
        
        self.interval_widget.setVisible(False)
        
        # Export buttons
        export_buttons = QHBoxLayout()
        
        preview_csv_btn = QPushButton("Preview CSV")
        preview_csv_btn.clicked.connect(self.preview_csv)
        
        export_csv_btn = QPushButton("Export to CSV")
        export_csv_btn.clicked.connect(self.export_csv)
        
        export_buttons.addWidget(preview_csv_btn)
        export_buttons.addWidget(export_csv_btn)
        
        export_layout.addLayout(scan_layout)
        export_layout.addWidget(self.interval_widget)
        export_layout.addLayout(export_buttons)
        export_group.setLayout(export_layout)
        
        # Add sections to right layout
        right_layout.addWidget(preview_group)
        right_layout.addWidget(details_group)
        right_layout.addWidget(export_group)
        
        # Add widgets to splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 800])  # Initial sizes
        
        # Add splitter to main layout
        main_layout.addWidget(splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Set central widget
        self.setCentralWidget(central_widget)
        
        # Create menus
        self.create_menus()
        
        # Load categories
        self.reload_categories()
        self.update_category_widgets()
    
    def create_menus(self):
        """Create application menus"""
        # File menu
        file_menu = self.menuBar().addMenu("&File")
        
        open_action = QAction("&Add Images...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(open_action)
        
        export_action = QAction("&Export to CSV...", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self.export_csv)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = self.menuBar().addMenu("&Edit")
        
        select_all_action = QAction("Select &All", self)
        select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        select_all_action.triggered.connect(self.select_all)
        edit_menu.addAction(select_all_action)
        
        deselect_all_action = QAction("&Deselect All", self)
        deselect_all_action.setShortcut(QKeySequence("Ctrl+D"))
        deselect_all_action.triggered.connect(self.deselect_all)
        edit_menu.addAction(deselect_all_action)
        
        edit_menu.addSeparator()
        
        delete_action = QAction("&Delete Selected", self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_action.triggered.connect(self.delete_selected)
        edit_menu.addAction(delete_action)
        
        # Tools menu
        tools_menu = self.menuBar().addMenu("&Tools")
        
        categories_action = QAction("&Manage Categories...", self)
        categories_action.triggered.connect(self.open_category_manager)
        tools_menu.addAction(categories_action)
        
        # Help menu
        help_menu = self.menuBar().addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def open_file_dialog(self):
        """Open file dialog to select images"""
        options = QFileDialog.Option.ReadOnly
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Images", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.tif);;All Files (*)",
            options=options
        )
        
        if files:
            self.add_images(files)
    
    def add_images(self, file_paths):
        """Add images to the collection"""
        added = 0
        for file_path in file_paths:
            # Check if image is already in the list
            if any(img.file_path == file_path for img in self.images):
                continue
                
            try:
                image_item = ImageItem(file_path)
                self.images.append(image_item)
                
                # Add to list widget
                list_item = QListWidgetItem(self.image_list)
                list_item.setText(image_item.filename)
                list_item.setIcon(QIcon(image_item.get_thumbnail()))
                list_item.setData(Qt.ItemDataRole.UserRole, len(self.images) - 1)
                
                added += 1
            except Exception as e:
                self.status_bar.showMessage(f"Error loading {file_path}: {str(e)}", 5000)
        
        if added > 0:
            self.status_bar.showMessage(f"Added {added} images", 3000)
            # Select the first added image if none selected
            if not self.image_list.selectedItems():
                self.image_list.setCurrentRow(0)
    
    def get_selected_image_indices(self) -> List[int]:
        """Get indices of selected images in the main list"""
        return [self.image_list.row(item) for item in self.image_list.selectedItems()]
    
    def get_selected_images(self) -> List[ImageItem]:
        """Get selected image items"""
        indices = self.get_selected_image_indices()
        return [self.images[i] for i in indices]
    
    def update_preview(self):
        """Update the preview area with selected images"""
        # Clear previous previews
        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        selected_images = self.get_selected_images()
        
        if not selected_images:
            # Clear detail fields
            self.filename_label.setText("")
            self.size_label.setText("")
            self.phys_size_label.setText("")
            self.text_edit.setText("")
            self.comment_edit.setText("")
            self.condition_combo.setCurrentIndex(-1)
            return
        
        # Determine thumbnail size based on number of selected images
        if len(selected_images) <= 2:
            thumb_size = QSize(200, 200)
        elif len(selected_images) <= 4:
            thumb_size = QSize(150, 150)
        else:
            thumb_size = QSize(120, 120)
        
        # Add preview for each selected image
        for image in selected_images:
            thumb_label = QLabel()
            thumb_label.setPixmap(image.get_thumbnail(thumb_size))
            thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.preview_layout.addWidget(thumb_label)
        
        # Update details for the first selected image
        self.update_details(selected_images[0])
    
    def update_details(self, image: ImageItem):
        """Update detail fields for the given image"""
        self.filename_label.setText(image.filename)
        self.size_label.setText(f"{image.image_size[0]} x {image.image_size[1]} pixels")
        self.phys_size_label.setText(image.physical_size)
        
        # Block signals to prevent triggering update functions
        self.text_edit.blockSignals(True)
        self.comment_edit.blockSignals(True)
        self.condition_combo.blockSignals(True)
        
        self.text_edit.setText(image.text)
        self.comment_edit.setText(image.comment)
        
        # Update condition dropdown
        self.reload_categories()  # Make sure categories are up to date
        self.condition_combo.clear()
        self.condition_combo.addItem("")  # Empty option
        
        if "Condition" in self.categories:
            self.condition_combo.addItems(self.categories["Condition"])
            
            # Set current condition if it exists
            index = self.condition_combo.findText(image.condition)
            if index >= 0:
                self.condition_combo.setCurrentIndex(index)
        
        # Update category widgets
        self.update_category_widgets()
        self.update_selected_categories()
        
        # Unblock signals
        self.text_edit.blockSignals(False)
        self.comment_edit.blockSignals(False)
        self.condition_combo.blockSignals(False)
    
    def update_text(self):
        """Update text field for selected images"""
        selected_images = self.get_selected_images()
        if not selected_images:
            return
            
        new_text = self.text_edit.text()
        for image in selected_images:
            image.text = new_text
    
    def update_comment(self):
        """Update comment field for selected images"""
        selected_images = self.get_selected_images()
        if not selected_images:
            return
            
        new_comment = self.comment_edit.toPlainText()
        for image in selected_images:
            image.comment = new_comment
    
    def update_condition(self, condition):
        """Update condition field for selected images"""
        selected_images = self.get_selected_images()
        if not selected_images:
            return
            
        for image in selected_images:
            image.condition = condition
    
    def reload_categories(self):
        """Reload categories from file"""
        self.categories = CategoryManager.load_categories()
    
    def update_category_widgets(self):
        """Create or update category selection widgets"""
        # Clear existing widgets
        while self.category_form.count():
            item = self.category_form.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.category_widgets.clear()
        
        # Create new widgets for each category group
        for group, values in self.categories.items():
            if group == "Condition":  # Skip condition as it's handled separately
                continue
                
            # Multi-select combo box
            combo = QComboBox()
            combo.addItem("")  # Empty option
            combo.addItems(values)
            combo.setProperty("group", group)
            combo.currentTextChanged.connect(
                lambda text, g=group: self.category_selected(g, text)
            )
            
            # List of selected values
            list_widget = QListWidget()
            list_widget.setMaximumHeight(80)
            list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
            
            # Context menu for removal
            list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            list_widget.customContextMenuRequested.connect(
                lambda pos, lw=list_widget, g=group: self.show_category_context_menu(pos, lw, g)
            )
            
            self.category_form.addRow(f"{group}:", combo)
            self.category_form.addRow("", list_widget)
            
            # Store widgets for later access
            self.category_widgets[group] = {
                "combo": combo,
                "list": list_widget
            }
    
    def update_selected_categories(self):
        """Update category widgets with selected image's categories"""
        selected_images = self.get_selected_images()
        if not selected_images:
            return
            
        image = selected_images[0]
        
        # Update each category list
        for group, widgets in self.category_widgets.items():
            list_widget = widgets["list"]
            list_widget.clear()
            
            if group in image.categories:
                for value in image.categories[group]:
                    QListWidgetItem(value, list_widget)
    
    def category_selected(self, group, text):
        """Handle category selection"""
        if not text:
            return
            
        selected_images = self.get_selected_images()
        if not selected_images:
            return
            
        # Add to category for all selected images
        for image in selected_images:
            if group not in image.categories:
                image.categories[group] = []
                
            # Avoid duplicates
            if text not in image.categories[group]:
                image.categories[group].append(text)
        
        # Update the list for the first image
        self.update_selected_categories()
        
        # Reset combo box
        self.category_widgets[group]["combo"].setCurrentIndex(0)
    
    def show_category_context_menu(self, pos, list_widget, group):
        """Show context menu for category list"""
        item = list_widget.itemAt(pos)
        if not item:
            return
            
        menu = QMenu(self)
        remove_action = menu.addAction("Remove")
        action = menu.exec(list_widget.mapToGlobal(pos))
        
        if action == remove_action:
            value = item.text()
            
            selected_images = self.get_selected_images()
            for image in selected_images:
                if group in image.categories and value in image.categories[group]:
                    image.categories[group].remove(value)
            
            # Update list
            self.update_selected_categories()
    
    def scan_mode_changed(self, mode):
        """Handle scan mode selection change"""
        # Show interval settings if interval mode selected
        show_interval = mode in ["Group of X", "Alternate"]
        self.interval_widget.setVisible(show_interval)
    
    def get_images_to_export(self) -> List[List[ImageItem]]:
        """Get images to export based on selected scan mode"""
        mode = self.scan_mode_combo.currentText()
        
        # Get the preview images (currently selected images)
        preview_images = self.get_selected_images()
        
        # If no images are selected, fall back to all images for certain modes
        if not preview_images:
            if mode in ["All"]:
                preview_images = self.images.copy()
            else:
                return []
    
        if mode == "Single":
            # Export each image in the preview list as a separate entry
            return [[image] for image in preview_images]
    
        elif mode == "Pair":
            # Export images in pairs (2 consecutive images per entry)
            pairs = [preview_images[i:i + 2] for i in range(0, len(preview_images), 2)]
            return pairs

        elif mode == "All":
            # Export all preview images as one entry
            return [preview_images]
    
        elif mode == "Group of X":
            # Export images in groups of X per entry (where X is the interval setting)
            interval = self.interval_spin.value()
            groups = [preview_images[i:i + interval] for i in range(0, len(preview_images), interval)]
            return groups
    
        elif mode == "Alternate":
            # Export images in alternating groups (taking every 2nd, 3rd, etc. image based on interval setting)
            interval = self.interval_spin.value()
            if interval <= 1:
                return [preview_images]
            
            result = []
            for step in range(interval):
                group = []
                for i in range(step, len(preview_images), interval):
                    group.append(preview_images[i])
                if group:  # Only add non-empty groups
                    result.append(group)
            return result
        
        return []

    def export_csv(self):
        """Export image data to CSV"""
        groups_of_images = self.get_images_to_export()
        
        if not groups_of_images:
            QMessageBox.warning(self, "Warning", "No images to export")
            return
        
        # Ask for file path
        options = QFileDialog.Option.ReadOnly
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export to CSV", "",
            "CSV Files (*.csv);;All Files (*)",
            options=options
        )
        
        if not file_path:
            return
            
        if not file_path.lower().endswith('.csv'):
            file_path += '.csv'
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow([
                    "Filename(s)", "Physical Size", "Category", 
                    "Text", "Comment", "Condition"
                ])
                
                # Write data
                for group in groups_of_images:
                    filenames = ", ".join([image.filename for image in group])
                    if group:
                        image = group[0]
                        # Format categories as a string
                        categories_text = ""
                        for group_name, values in image.categories.items():
                            if values:
                                categories_text += f"{group_name}: {', '.join(values)}; "
                        
                        writer.writerow([
                            filenames,
                            image.physical_size,
                            categories_text,
                            image.text,
                            image.comment,
                            image.condition
                        ])
            
            # Add exported images to list2
            for group in groups_of_images:
                for image in group:
                    if image not in self.exported_images:
                        self.exported_images.append(image)
                        
                        # Add to exported list
                        item = QListWidgetItem(image.filename)
                        item.setIcon(QIcon(image.get_thumbnail(QSize(32, 32))))
                        self.exported_list.addItem(item)
            
            self.status_bar.showMessage(f"Exported {len(groups_of_images)} groups of images to {file_path}", 5000)
            
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to export CSV: {str(e)}"
            )
            
    def preview_csv(self):
        """Preview CSV data before export"""
        groups_of_images = self.get_images_to_export()
        if not groups_of_images:
            QMessageBox.warning(self, "Warning", "No images to preview")
            return
    
        # Create a preview dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("CSV Export Preview")
        dialog.setMinimumSize(900, 600)
        layout = QVBoxLayout(dialog)
    
        # Instructions
        instructions = QLabel(
         "Preview of data to be exported to CSV. Check and confirm before export."
        )
        instructions.setStyleSheet("font-weight: bold; color: #555;")
        layout.addWidget(instructions)
    
        # Table widget
        table = QTableWidget()
        headers = ["Filename(s)", "Physical Size", "Category", 
              "Text", "Comment", "Condition"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    
        # Fill the table with grouped data according to scan mode
        table.setRowCount(len(groups_of_images))
    
        for row, group in enumerate(groups_of_images):
            # Filenames - combined for the group
            filenames = ", ".join([image.filename for image in group])
            table.setItem(row, 0, QTableWidgetItem(filenames))
        
            if group:  # If the group has at least one image
                image = group[0]  # Use first image of the group for other details
            
                # Physical size
                table.setItem(row, 1, QTableWidgetItem(image.physical_size))
            
                # Categories
                categories_text = ""
                for group_name, values in image.categories.items():
                    if values:
                        categories_text += f"{group_name}: {', '.join(values)}; "
                        table.setItem(row, 2, QTableWidgetItem(categories_text))
            
                # Text
                table.setItem(row, 3, QTableWidgetItem(image.text))
            
                # Comment
                table.setItem(row, 4, QTableWidgetItem(image.comment))
            
                # Condition
                table.setItem(row, 5, QTableWidgetItem(image.condition))
    
        layout.addWidget(table)
    
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
    
        # Show the dialog
        dialog.exec()
    
    def transfer_back_to_list1(self):
        """Transfer selected images back from exported list to main list"""
        selected_items = self.exported_list.selectedItems()
        if not selected_items:
            return
            
        for item in selected_items:
            index = self.exported_list.row(item)
            # Remove from exported list
            self.exported_list.takeItem(index)
            self.exported_images.pop(index)
    
    def move_selected_up(self):
        """Move selected items up in the list"""
        indices = self.get_selected_image_indices()
        if not indices or min(indices) == 0:
            return
            
        # Sort indices to maintain order
        indices.sort()
        
        # Move items one by one
        for idx in indices:
            # Swap images in the list
            self.images[idx], self.images[idx-1] = self.images[idx-1], self.images[idx]
            
            # Update list widget
            item1 = self.image_list.item(idx)
            item2 = self.image_list.item(idx-1)
            
            text1, text2 = item1.text(), item2.text()
            icon1, icon2 = item1.icon(), item2.icon()
            
            item2.setText(text1)
            item2.setIcon(icon1)
            
            item1.setText(text2)
            item1.setIcon(icon2)
            
            # Move selection
            self.image_list.setCurrentRow(idx-1)
    
    def move_selected_down(self):
        """Move selected items down in the list"""
        indices = self.get_selected_image_indices()
        if not indices or max(indices) >= len(self.images) - 1:
            return
            
        # Sort indices in reverse to maintain order
        indices.sort(reverse=True)
        
        # Move items one by one
        for idx in indices:
            # Swap images in the list
            self.images[idx], self.images[idx+1] = self.images[idx+1], self.images[idx]
            
            # Update list widget
            item1 = self.image_list.item(idx)
            item2 = self.image_list.item(idx+1)
            
            text1, text2 = item1.text(), item2.text()
            icon1, icon2 = item1.icon(), item2.icon()
            
            item2.setText(text1)
            item2.setIcon(icon1)
            
            item1.setText(text2)
            item1.setIcon(icon2)
            
            # Move selection
            self.image_list.setCurrentRow(idx+1)
    
    def delete_selected(self):
        """Delete selected images from the list"""
        indices = self.get_selected_image_indices()
        if not indices:
            return
            
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete {len(indices)} selected images?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Sort indices in reverse to avoid index shifting
            indices.sort(reverse=True)
            
            for idx in indices:
                self.image_list.takeItem(idx)
                self.images.pop(idx)
            
            self.update_preview()
    
    def open_preview_dialog(self):
        """Open dialog with full preview of selected images"""
        selected_images = self.get_selected_images()
        
        if not selected_images:
            QMessageBox.information(
                self, "Information", "Please select images to preview"
            )
            return
            
        dialog = ImagePreviewDialog(selected_images, self)
        dialog.exec()
    
    def open_category_manager(self):
        """Open dialog to manage categories"""
        dialog = CategoryManager(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Reload categories and update UI
            self.reload_categories()
            self.update_category_widgets()
            self.update_selected_categories()
    
    def select_all(self):
        """Select all items in the image list"""
        for i in range(self.image_list.count()):
            self.image_list.item(i).setSelected(True)
    
    def deselect_all(self):
        """Deselect all items in the image list"""
        for i in range(self.image_list.count()):
            self.image_list.item(i).setSelected(False)
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self, "About Photo Collection Manager",
            """
            <h1>Photo Collection Manager</h1>
            <p>A tool for managing your photo collection and exporting data to CSV for marketplaces.</p>
            <p>Developed for HEINZ1110.</p>
            <p>Current Date: 2025-04-03</p>
            """
        )
    
    def load_settings(self):
        """Load application settings"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    settings = json.load(f)
                    
                if "window_size" in settings:
                    width, height = settings["window_size"]
                    self.resize(width, height)
            except Exception:
                pass
    
    def save_settings(self):
        """Save application settings"""
        settings = {
            "window_size": [self.width(), self.height()]
        }
        
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.save_settings()
        event.accept()


class QFlowLayout(QLayout):
    """Custom flow layout for the image preview area"""
    
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        
        self.items = []
    
    def __del__(self):
        """Delete all items on deletion"""
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)
    
    def addItem(self, item):
        """Add an item to the layout"""
        self.items.append(item)
    
    def count(self):
        """Return number of items"""
        return len(self.items)
    
    def itemAt(self, index):
        """Get item at index"""
        if 0 <= index < len(self.items):
            return self.items[index]
        return None
    
    def takeAt(self, index):
        """Remove and return item at index"""
        if 0 <= index < len(self.items):
            return self.items.pop(index)
        return None
    
    def expandingDirections(self):
        """Return expanding directions"""
        return Qt.Orientation.Horizontal | Qt.Orientation.Vertical
    
    def hasHeightForWidth(self):
        """Return whether height depends on width"""
        return True
    
    def heightForWidth(self, width):
        """Calculate height for given width"""
        return self.doLayout(QRect(0, 0, width, 0), True)
    
    def setGeometry(self, rect):
        """Set geometry for the layout"""
        super().setGeometry(rect)
        self.doLayout(rect, False)
    
    def sizeHint(self):
        """Return recommended size"""
        return self.minimumSize()
    
    def minimumSize(self):
        """Return minimum size"""
        size = QSize()
        
        for item in self.items:
            size = size.expandedTo(item.minimumSize())
        
        size += QSize(2 * self.contentsMargins().left(), 2 * self.contentsMargins().top())
        return size
    
    def doLayout(self, rect, testOnly):
        """Layout items within the given rectangle"""
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()
        
        for item in self.items:
            style = item.widget().style()
            layout_spacing_x = style.layoutSpacing(
                QSizePolicy.ControlType.PushButton, QSizePolicy.ControlType.PushButton, Qt.Orientation.Horizontal)
            layout_spacing_y = style.layoutSpacing(
                QSizePolicy.ControlType.PushButton, QSizePolicy.ControlType.PushButton, Qt.Orientation.Vertical)
            
            space_x = spacing + layout_spacing_x
            space_y = spacing + layout_spacing_y
            
           
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()  # Start new line
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0
            
            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
        
        return y + line_height - rect.y()


def main():
    """Main function to run the application"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set application style
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f5f5f5;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #cccccc;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 8px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px;
        }
        QPushButton {
            background-color: #4a86e8;
            color: white;
            border-radius: 4px;
            padding: 5px 10px;
            border: none;
        }
        QPushButton:hover {
            background-color: #3b78de;
        }
        QPushButton:pressed {
            background-color: #2d5bbd;
        }
        QComboBox {
            padding: 5px;
            border: 1px solid #cccccc;
            border-radius: 4px;
        }
        QLineEdit, QTextEdit {
            padding: 5px;
            border: 1px solid #cccccc;
            border-radius: 4px;
        }
        QListWidget {
            border: 1px solid #cccccc;
            border-radius: 4px;
        }
        QStatusBar {
            background-color: #e0e0e0;
        }
        QTableWidget {
            gridline-color: #d0d0d0;
        }
        QHeaderView::section {
            background-color: #e0e0e0;
            padding: 5px;
            border: 1px solid #cccccc;
            font-weight: bold;
        }
    """)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()