import curses
import os
import logging
import platform
import re
from pathlib import Path
from typing import List, Dict
from file_sorter import FileSorter, ExtensionFilter, SizeFilter, DateFilter, CustomRegexFilter

# Set up logging (shared with GUI)
logging.basicConfig(
    filename='sorting_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class FileSorterCLI:
    """CLI for the file sorter application with retro theme and dynamic height."""
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.sorter = FileSorter()
        self.source_dir = None
        self.filters = {
            "Images": False,
            "Documents": False,
            "LargeFiles": False,
            "RecentFiles": False
        }
        self.custom_regex = ""
        self.menu_options = [
            "Select Folder",
            "Choose Filters",
            "Set Folder Prefix",
            "Sort Files",
            "Save Config",
            "Exit"
        ]
        self.current_menu = 0
        self.min_height = 12  # Minimum terminal height
        self.max_height = 24  # Maximum terminal height
        self.default_width = 80  # Fixed width for retro aesthetic
        self.setup_curses()

    def setup_curses(self):
        """Initialize curses with retro green-on-black theme."""
        curses.curs_set(0)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_GREEN)
        self.stdscr.bkgd(curses.color_pair(1))
        self.stdscr.clear()

    def resize_window(self, content_lines: int):
        """Dynamically adjust terminal height based on content."""
        # Calculate required height: content + borders (2) + title (1) + status (1) + padding (4)
        required_height = content_lines + 8
        height = max(self.min_height, min(self.max_height, required_height))
        
        try:
            # Resize terminal
            curses.resizeterm(height, self.default_width)
            if platform.system() == "Windows":
                os.system(f"mode con: cols={self.default_width} lines={height}")
            self.stdscr.clear()
        except Exception as e:
            logging.warning(f"Failed to resize terminal: {str(e)}")
            # Fallback: use available terminal size
            pass

    def draw_menu(self):
        """Draw the main menu with dynamic height."""
        content_lines = len(self.menu_options)  # One line per menu item
        self.resize_window(content_lines)
        
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()
        title = "AETHER SORT"
        self.stdscr.addstr(1, (w - len(title)) // 2, title, curses.color_pair(1) | curses.A_BOLD)
        
        # ASCII border
        border = "+" + "-" * (w - 2) + "+"
        self.stdscr.addstr(3, 0, border, curses.color_pair(1))
        self.stdscr.addstr(h - 2, 0, border, curses.color_pair(1))
        for i in range(4, h - 2):
            self.stdscr.addstr(i, 0, "|", curses.color_pair(1))
            self.stdscr.addstr(i, w - 1, "|", curses.color_pair(1))

        # Menu options, centered vertically
        start_y = (h - len(self.menu_options)) // 2
        for idx, option in enumerate(self.menu_options):
            y = start_y + idx
            x = (w - len(option)) // 2
            if idx == self.current_menu:
                self.stdscr.addstr(y, x, option, curses.color_pair(2) | curses.A_BOLD)
            else:
                self.stdscr.addstr(y, x, option, curses.color_pair(1))

        # Status info
        status = f"Folder: {self.source_dir or 'Not set'} | Prefix: {self.sorter.folder_prefix}"
        self.stdscr.addstr(h - 3, 2, status[:w - 4], curses.color_pair(1))
        self.stdscr.refresh()

    def draw_filters(self):
        """Draw the filter selection submenu with dynamic height."""
        filter_names = list(self.filters.keys()) + ["Custom Regex", "Back"]
        content_lines = len(filter_names)  # One line per filter option
        self.resize_window(content_lines)
        
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()
        title = ">>> Select Filters <<<"
        self.stdscr.addstr(1, (w - len(title)) // 2, title, curses.color_pair(1) | curses.A_BOLD)
        
        # ASCII border
        border = "+" + "-" * (w - 2) + "+"
        self.stdscr.addstr(3, 0, border, curses.color_pair(1))
        self.stdscr.addstr(h - 2, 0, border, curses.color_pair(1))
        for i in range(4, h - 2):
            self.stdscr.addstr(i, 0, "|", curses.color_pair(1))
            self.stdscr.addstr(i, w - 1, "|", curses.color_pair(1))

        # Filter options, centered vertically
        start_y = (h - len(filter_names)) // 2
        for idx, name in enumerate(filter_names):
            y = start_y + idx
            x = (w - len(name) - 4) // 2
            prefix = "[X]" if (name in self.filters and self.filters[name]) or (name == "Custom Regex" and self.custom_regex) else "[ ]"
            if idx == self.current_menu:
                self.stdscr.addstr(y, x, f"{prefix} {name}", curses.color_pair(2) | curses.A_BOLD)
            else:
                self.stdscr.addstr(y, x, f"{prefix} {name}", curses.color_pair(1))

        # Custom regex display
        if self.custom_regex:
            regex_display = f"Regex: {self.custom_regex}"[:w - 4]
            self.stdscr.addstr(h - 3, 2, regex_display, curses.color_pair(1))
        
        self.stdscr.refresh()
        return filter_names

    def get_input(self, prompt: str) -> str:
        """Get text input with dynamic height."""
        content_lines = 2  # Prompt + input field
        self.resize_window(content_lines)
        
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()
        self.stdscr.addstr(h // 2 - 1, 2, prompt[:w - 4], curses.color_pair(1))
        self.stdscr.addstr(h // 2, 2, ">>> ", curses.color_pair(1) | curses.A_BOLD)
        curses.curs_set(1)
        input_win = curses.newwin(1, w - 8, h // 2, 6)
        input_win.bkgd(curses.color_pair(1))
        input_win.keypad(True)
        text = ""
        while True:
            input_win.clear()
            input_win.addstr(0, 0, text)
            input_win.refresh()
            ch = input_win.getch()
            if ch == curses.KEY_ENTER or ch == 10:
                break
            elif ch == 27:  # Esc
                text = ""
                break
            elif ch == curses.KEY_BACKSPACE or ch == 127:
                text = text[:-1]
            elif 32 <= ch <= 126:
                text += chr(ch)
        curses.curs_set(0)
        return text.strip()

    def run(self):
        """Main CLI loop."""
        while True:
            self.draw_menu()
            key = self.stdscr.getch()
            
            # Navigation
            if key in (curses.KEY_UP, ord('w'), ord('W')):
                self.current_menu = (self.current_menu - 1) % len(self.menu_options)
            elif key in (curses.KEY_DOWN, ord('s'), ord('S')):
                self.current_menu = (self.current_menu + 1) % len(self.menu_options)
            elif key == ord('q') or key == 27:
                break
            elif key == curses.KEY_ENTER or key == 10:
                option = self.menu_options[self.current_menu]
                if option == "Exit":
                    break
                elif option == "Select Folder":
                    folder = self.get_input("Enter folder path (or press Esc to cancel): ")
                    if folder:
                        try:
                            self.sorter.set_source_dir(folder)
                            self.source_dir = folder
                            self.stdscr.addstr(2, 2, "Folder set successfully!", curses.color_pair(1))
                        except ValueError as e:
                            self.stdscr.addstr(2, 2, f"Error: {str(e)}", curses.color_pair(1))
                        self.stdscr.refresh()
                        curses.napms(1000)
                elif option == "Choose Filters":
                    self.current_menu = 0
                    while True:
                        filter_names = self.draw_filters()
                        key = self.stdscr.getch()
                        if key in (curses.KEY_UP, ord('w'), ord('W')):
                            self.current_menu = (self.current_menu - 1) % len(filter_names)
                        elif key in (curses.KEY_DOWN, ord('s'), ord('S')):
                            self.current_menu = (self.current_menu + 1) % len(filter_names)
                        elif key == curses.KEY_ENTER or key == 10:
                            selected = filter_names[self.current_menu]
                            if selected == "Back":
                                break
                            elif selected == "Custom Regex":
                                regex = self.get_input("Enter regex pattern (e.g., '.*\\.bak$') or Esc to cancel: ")
                                self.custom_regex = regex
                            else:
                                self.filters[selected] = not self.filters[selected]
                        elif key == 27:
                            break
                elif option == "Set Folder Prefix":
                    prefix = self.get_input(f"Enter folder prefix (current: {self.sorter.folder_prefix}): ")
                    if prefix:
                        self.sorter.folder_prefix = prefix
                        self.stdscr.addstr(2, 2, "Prefix updated!", curses.color_pair(1))
                        self.stdscr.refresh()
                        curses.napms(1000)
                elif option == "Sort Files":
                    if not self.source_dir:
                        self.stdscr.addstr(2, 2, "Error: Please select a folder first!", curses.color_pair(1))
                        self.stdscr.refresh()
                        curses.napms(1000)
                        continue
                    self.sorter.filters = []
                    if self.filters["Images"]:
                        self.sorter.add_filter(ExtensionFilter([".jpg", ".png", ".gif"], "Images"))
                    if self.filters["Documents"]:
                        self.sorter.add_filter(ExtensionFilter([".pdf", ".doc", ".docx", ".txt"], "Documents"))
                    if self.filters["LargeFiles"]:
                        self.sorter.add_filter(SizeFilter("LargeFiles", min_size=10*1024*1024, destination="LargeFiles"))
                    if self.filters["RecentFiles"]:
                        self.sorter.add_filter(DateFilter("RecentFiles", days_ago=7, destination="RecentFiles"))
                    if self.custom_regex:
                        try:
                            self.sorter.add_filter(CustomRegexFilter("Custom", self.custom_regex, "Backups"))
                        except re.error as e:
                            self.stdscr.addstr(2, 2, f"Invalid regex: {str(e)}", curses.color_pair(1))
                            self.stdscr.refresh()
                            curses.napms(1000)
                            continue
                    try:
                        results = self.sorter.sort_files()
                        message = (
                            f"Sorting completed!\n"
                            f"Moved: {results['moved']} files\n"
                            f"Skipped: {results['skipped']} files\n"
                            f"Errors: {results['errors']} files"
                        )
                        content_lines = len(message.split('\n'))
                        self.resize_window(content_lines)
                        self.stdscr.clear()
                        h, w = self.stdscr.getmaxyx()
                        for i, line in enumerate(message.split('\n')):
                            self.stdscr.addstr(h // 2 - 2 + i, (w - len(line)) // 2, line, curses.color_pair(1))
                        self.stdscr.refresh()
                        curses.napms(2000)
                    except Exception as e:
                        self.stdscr.addstr(2, 2, f"Error: {str(e)}", curses.color_pair(1))
                        self.stdscr.refresh()
                        curses.napms(1000)
                elif option == "Save Config":
                    try:
                        self.sorter.save_config()
                        self.stdscr.addstr(2, 2, "Config saved!", curses.color_pair(1))
                        self.stdscr.refresh()
                        curses.napms(1000)
                    except Exception as e:
                        self.stdscr.addstr(2, 2, f"Error: {str(e)}", curses.color_pair(1))
                        self.stdscr.refresh()
                        curses.napms(1000)

def main(stdscr):
    """Entry point for the CLI."""
    try:
        cli = FileSorterCLI(stdscr)
        cli.run()
    except Exception as e:
        logging.error(f"CLI crashed: {str(e)}")
        raise

if __name__ == "__main__":
    curses.wrapper(main)