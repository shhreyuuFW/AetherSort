# AetherSort

AetherSort is a cross-platform file sorting utility with both a modern GUI and a retro-themed CLI. It helps you organize files in a selected folder using customizable filters such as file type, size, modification date, and custom regular expressions. AetherSort is ideal for quickly decluttering your directories and keeping your files organized.

---

## Features

- **Modern GUI**: User-friendly interface with a dark, futuristic theme.
- **Retro CLI**: Terminal-based interface with dynamic resizing and green-on-black aesthetics.
- **Flexible Filters**:
  - Sort by file extension (e.g., Images, Documents)
  - Sort by file size (e.g., Large Files)
  - Sort by modification date (e.g., Recent Files)
  - Custom regex-based sorting
- **Customizable Folder Prefix**: Add a prefix to all destination folders.
- **Configurable**: Save and load filter configurations via `config.json`.
- **Logging**: All actions and errors are logged to `sorting_log.txt`.

---

## Installation

### Requirements

- Python 3.8+
- [Tkinter](https://docs.python.org/3/library/tkinter.html) (usually included with Python)
- On Windows, for CLI:
- pip install windows-curses
