import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import os
import shutil
from pathlib import Path
import datetime
import re
import json
import logging
from typing import List, Dict, Callable

# Set up logging
logging.basicConfig(
    filename='sorting_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def configure_theme(root: tk.Tk):
    """Configure a futuristic, dark, and minimal theme."""
    style = ttk.Style(root)
    
    # Color palette
    colors = {
        "bg": "#1C2526",        # Dark charcoal background
        "fg": "#E0E0E0",        # Light text for contrast
        "accent": "#00D9FF",    # Neon cyan for buttons and highlights
        "hover": "#00A3CC",     # Slightly darker cyan for hover effects
        "entry_bg": "#2A3439",  # Slightly lighter dark for entry fields
        "separator": "#4B5EAA"  # Subtle blue for separators
    }
    
    # Configure root window
    root.configure(bg=colors["bg"])
    
    # Font settings
    font = ("Helvetica", 10, "normal")
    font_bold = ("Helvetica", 10, "bold")
    
    # Configure ttk styles
    style.theme_use('clam')
    style.configure("TLabel", 
                    background=colors["bg"], 
                    foreground=colors["fg"], 
                    font=font,
                    padding=5)
    style.configure("TButton", 
                    background=colors["accent"], 
                    foreground=colors["bg"], 
                    font=font_bold,
                    borderwidth=0,
                    padding=8)
    style.map("TButton",
              background=[("active", colors["hover"]), ("!active", colors["accent"])],
              foreground=[("active", colors["fg"]), ("!active", colors["bg"])])
    style.configure("TCheckbutton",
                    background=colors["bg"],
                    foreground=colors["fg"],
                    font=font,
                    padding=5)
    style.map("TCheckbutton",
              background=[("active", colors["bg"]), ("!active", colors["bg"])],
              foreground=[("active", colors["accent"]), ("!active", colors["fg"])])
    style.configure("TEntry",
                    fieldbackground=colors["entry_bg"],
                    foreground=colors["fg"],
                    font=font,
                    borderwidth=1)
    style.configure("TFrame",
                    background=colors["bg"])
    style.configure("TSeparator",
                    background=colors["separator"])
    # Custom styles for LabelFrame and its label
    style.configure("Dark.TLabelframe", background=colors["bg"], bordercolor=colors["accent"])
    style.configure("Dark.TLabelframe.Label", background=colors["bg"], foreground=colors["accent"], font=font_bold)
    
    # Return colors for use in non-ttk widgets
    return colors

class Filter:
    """Base class for file filters."""
    def __init__(self, name: str, destination: str):
        self.name = name
        self.destination = destination

    def apply(self, file_path: Path) -> bool:
        """Check if the file matches the filter criteria."""
        raise NotImplementedError

    def get_destination_folder(self, prefix: str = "") -> str:
        """Return the destination folder name with optional prefix."""
        return f"{prefix}{self.destination}"

class ExtensionFilter(Filter):
    """Filter files by extension."""
    def __init__(self, extensions: List[str], destination: str):
        super().__init__("ByExtension_" + "_".join(extensions), destination)
        self.extensions = [ext.lower() for ext in extensions]

    def apply(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.extensions

class SizeFilter(Filter):
    """Filter files by size (in bytes)."""
    def __init__(self, name: str, min_size: int = None, max_size: int = None, destination: str = None):
        super().__init__(name, destination or name)
        self.min_size = min_size
        self.max_size = max_size

    def apply(self, file_path: Path) -> bool:
        file_size = file_path.stat().st_size
        if self.min_size is not None and file_size < self.min_size:
            return False
        if self.max_size is not None and file_size > self.max_size:
            return False
        return True

class DateFilter(Filter):
    """Filter files by modification date."""
    def __init__(self, name: str, days_ago: int, destination: str = None):
        super().__init__(name, destination or name)
        self.days_ago = days_ago

    def apply(self, file_path: Path) -> bool:
        mod_time = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
        delta = datetime.datetime.now() - mod_time
        return delta.days <= self.days_ago

class CustomRegexFilter(Filter):
    """Filter files by user-defined regex pattern on filename."""
    def __init__(self, name: str, pattern: str, destination: str = None):
        super().__init__(name, destination or name)
        self.pattern = re.compile(pattern, re.IGNORECASE)

    def apply(self, file_path: Path) -> bool:
        return bool(self.pattern.search(file_path.name))

class FileSorter:
    """Main class to handle file sorting operations."""
    def __init__(self, config_file: str = "config.json"):
        self.filters: List[Filter] = []
        self.source_dir: Path = None
        self.config_file = config_file
        self.folder_prefix = "AETH_"  # Default prefix
        self.load_config()

    def load_config(self):
        """Load filters and settings from config.json."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # Load folder prefix from settings
                self.folder_prefix = config.get("settings", {}).get("folder_prefix", "AETH_")
                logging.info(f"Loaded folder prefix: {self.folder_prefix}")
                # Load filters
                for filter_config in config.get("filters", []):
                    filter_type = filter_config.get("type")
                    destination = filter_config.get("destination", "Default")
                    if filter_type == "ExtensionFilter":
                        self.add_filter(ExtensionFilter(
                            filter_config.get("extensions", []),
                            destination
                        ))
                    elif filter_type == "SizeFilter":
                        min_size_mb = filter_config.get("min_size_mb")
                        min_size = int(min_size_mb * 1024 * 1024) if min_size_mb is not None else None
                        self.add_filter(SizeFilter(
                            "LargeFiles",
                            min_size=min_size,
                            destination=destination
                        ))
                    elif filter_type == "DateFilter":
                        self.add_filter(DateFilter(
                            "RecentFiles",
                            filter_config.get("days_ago", 7),
                            destination
                        ))
                    elif filter_type == "CustomRegexFilter":
                        self.add_filter(CustomRegexFilter(
                            "Custom",
                            filter_config.get("pattern", ".*"),
                            destination
                        ))
                    logging.info(f"Loaded filter: {filter_type} -> {destination}")
            else:
                logging.warning(f"Config file {self.config_file} not found")
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in {self.config_file}: {str(e)}")
        except Exception as e:
            logging.error(f"Error loading config: {str(e)}")

    def save_config(self):
        """Save current filters and settings to config.json."""
        config = {
            "filters": [],
            "settings": {
                "recursive": False,
                "overwrite_existing": False,
                "folder_prefix": self.folder_prefix
            }
        }
        for filter_obj in self.filters:
            filter_data = {"destination": filter_obj.destination}
            if isinstance(filter_obj, ExtensionFilter):
                filter_data["type"] = "ExtensionFilter"
                filter_data["extensions"] = filter_obj.extensions
            elif isinstance(filter_obj, SizeFilter):
                filter_data["type"] = "SizeFilter"
                filter_data["min_size_mb"] = filter_obj.min_size / (1024 * 1024) if filter_obj.min_size else None
            elif isinstance(filter_obj, DateFilter):
                filter_data["type"] = "DateFilter"
                filter_data["days_ago"] = filter_obj.days_ago
            elif isinstance(filter_obj, CustomRegexFilter):
                filter_data["type"] = "CustomRegexFilter"
                filter_data["pattern"] = filter_obj.pattern.pattern
            config["filters"].append(filter_data)
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logging.info(f"Saved config to {self.config_file}")
        except Exception as e:
            logging.error(f"Error saving config: {str(e)}")

    def add_filter(self, filter_obj: Filter):
        """Add a filter to the sorter."""
        self.filters.append(filter_obj)
        logging.info(f"Added filter: {filter_obj.name} -> {filter_obj.get_destination_folder(self.folder_prefix)}")

    def set_source_dir(self, directory: str):
        """Set the source directory for sorting."""
        self.source_dir = Path(directory)
        if not self.source_dir.is_dir():
            raise ValueError(f"Invalid directory: {directory}")
        logging.info(f"Source directory set to: {directory}")

    def sort_files(self) -> Dict[str, int]:
        """Sort files in the source directory based on filters."""
        if not self.source_dir:
            raise ValueError("Source directory not set")

        results = {"moved": 0, "skipped": 0, "errors": 0}
        for file_path in self.source_dir.iterdir():
            if not file_path.is_file():
                continue

            moved = False
            for filter_obj in self.filters:
                if filter_obj.apply(file_path):
                    try:
                        dest_folder = self.source_dir / filter_obj.get_destination_folder(self.folder_prefix)
                        dest_folder.mkdir(exist_ok=True)
                        dest_path = dest_folder / file_path.name
                        shutil.move(str(file_path), str(dest_path))
                        logging.info(f"Moved {file_path} to {dest_path}")
                        results["moved"] += 1
                        moved = True
                        break
                    except Exception as e:
                        logging.error(f"Error moving {file_path}: {str(e)}")
                        results["errors"] += 1

            if not moved:
                results["skipped"] += 1
                logging.info(f"Skipped {file_path}: no matching filter")

        return results

class FileSorterGUI:
    """GUI for the file sorter application."""
    def __init__(self):
        self.sorter = FileSorter()
        self.root = tk.Tk()
        self.root.title("File Sorter")
        self.root.geometry("600x500")  # Slightly taller for better spacing
        
        # Apply futuristic dark theme
        self.colors = configure_theme(self.root)
        
        # Main frame for centering content
        main_frame = ttk.Frame(self.root, style="TFrame")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Folder selection section
        folder_frame = ttk.LabelFrame(main_frame, text="Folder Selection", style="Dark.TLabelframe", padding=10, labelanchor="n")
        folder_frame.grid(row=0, column=0, sticky="ew", pady=10)
        self.source_dir_var = tk.StringVar(value="No folder selected")
        ttk.Label(folder_frame, text="Source Folder:", style="TLabel").grid(row=0, column=0, sticky="w", padx=5)
        ttk.Label(folder_frame, textvariable=self.source_dir_var, wraplength=450, style="TLabel").grid(row=1, column=0, columnspan=2, sticky="w", padx=5)
        ttk.Button(folder_frame, text="Browse", command=self.select_folder, style="TButton").grid(row=2, column=0, columnspan=2, pady=5)
        
        # Separator
        ttk.Separator(main_frame, orient="horizontal", style="TSeparator").grid(row=1, column=0, sticky="ew", pady=10)
        
        # Filter selection section
        filter_frame = ttk.LabelFrame(main_frame, text="Filters", style="Dark.TLabelframe", padding=10, labelanchor="n")
        filter_frame.grid(row=2, column=0, sticky="ew", pady=10)
        self.filter_vars = {
            "Images": tk.BooleanVar(),
            "Documents": tk.BooleanVar(),
            "LargeFiles": tk.BooleanVar(),
            "RecentFiles": tk.BooleanVar()
        }
        for i, filter_name in enumerate(self.filter_vars):
            ttk.Checkbutton(filter_frame, text=filter_name, variable=self.filter_vars[filter_name], style="TCheckbutton").grid(row=i, column=0, sticky="w", padx=10, pady=2)
        
        ttk.Label(filter_frame, text="Custom Regex (e.g., '.*\\.bak$'):", style="TLabel").grid(row=len(self.filter_vars), column=0, sticky="w", padx=10, pady=5)
        self.custom_filter_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.custom_filter_var, width=40, style="TEntry").grid(row=len(self.filter_vars)+1, column=0, padx=10, pady=5)
        
        # Separator
        ttk.Separator(main_frame, orient="horizontal", style="TSeparator").grid(row=3, column=0, sticky="ew", pady=10)
        
        # Actions section
        actions_frame = ttk.Frame(main_frame, style="TFrame")
        actions_frame.grid(row=4, column=0, sticky="ew", pady=10)
        ttk.Label(actions_frame, text=f"Folder Prefix: {self.sorter.folder_prefix}", style="TLabel").grid(row=0, column=0, columnspan=2, pady=5)
        ttk.Button(actions_frame, text="Save Filters to Config", command=self.save_config, style="TButton").grid(row=1, column=0, padx=5)
        ttk.Button(actions_frame, text="Sort Files", command=self.sort_files, style="TButton").grid(row=1, column=1, padx=5)
        
        # After all widgets are created, let window autosize
        self.root.update_idletasks()
        self.root.geometry("")

    def select_folder(self):
        """Open file dialog to select source folder."""
        folder = filedialog.askdirectory(title="Select Folder to Sort")
        if folder:
            self.source_dir_var.set(folder)
            try:
                self.sorter.set_source_dir(folder)
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                logging.error(f"Failed to set source directory: {str(e)}")

    def save_config(self):
        """Save current filter settings to config.json."""
        try:
            self.sorter.save_config()
            messagebox.showinfo("Success", f"Filters saved to {self.sorter.config_file}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {str(e)}")

    def sort_files(self):
        """Apply selected filters and sort files."""
        if not self.source_dir_var.get() or self.source_dir_var.get() == "No folder selected":
            messagebox.showwarning("Warning", "Please select a source folder")
            return

        # Reset filters to avoid duplicates
        self.sorter.filters = []

        # Add selected filters from GUI
        if self.filter_vars["Images"].get():
            self.sorter.add_filter(ExtensionFilter([".jpg", ".png", ".gif"], "Images"))
        if self.filter_vars["Documents"].get():
            self.sorter.add_filter(ExtensionFilter([".pdf", ".doc", ".docx", ".txt"], "Documents"))
        if self.filter_vars["LargeFiles"].get():
            self.sorter.add_filter(SizeFilter("LargeFiles", min_size=10*1024*1024, destination="LargeFiles"))
        if self.filter_vars["RecentFiles"].get():
            self.sorter.add_filter(DateFilter("RecentFiles", days_ago=7, destination="RecentFiles"))
        if self.custom_filter_var.get():
            try:
                self.sorter.add_filter(CustomRegexFilter("Custom", self.custom_filter_var.get(), "Backups"))
            except re.error as e:
                messagebox.showerror("Error", f"Invalid regex pattern: {str(e)}")
                return

        # Perform sorting
        try:
            results = self.sorter.sort_files()
            message = (
                f"Sorting completed!\n"
                f"Moved: {results['moved']} files\n"
                f"Skipped: {results['skipped']} files\n"
                f"Errors: {results['errors']} files\n"
                f"Check sorting_log.txt for details."
            )
            messagebox.showinfo("Success", message)
        except Exception as e:
            messagebox.showerror("Error", f"Sorting failed: {str(e)}")
            logging.error(f"Sorting failed: {str(e)}")

    def run(self):
        """Start the GUI main loop."""
        self.root.mainloop()

def main():
    """Entry point for the application."""
    app = FileSorterGUI()
    app.run()

if __name__ == "__main__":
    main()