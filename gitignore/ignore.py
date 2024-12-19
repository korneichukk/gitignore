#!/usr/bin/env python
import os
from pathlib import Path
import subprocess
import logging
import shutil
from typing import List, Optional, Tuple
import curses
import re

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        # logging.FileHandler("app.log")
    ],
)

logger = logging.getLogger(__file__)
HOME = Path().home()
GITIGNORE_DIR = HOME / "gitignore"


def fuzzy_search(query: str, items: List[str]):
    query = re.sub(r"\s+", " ", query.strip())  # Normalize spaces
    if not query:
        return items

    regex = ".*".join(map(re.escape, query))
    pattern = re.compile(regex, re.IGNORECASE)

    return [item for item in items if pattern.search(item)]


def cli(items: List[str]):
    def draw_cli(stdscr: curses.window):
        curses.curs_set(0)
        stdscr.clear()
        stdscr.refresh()

        current_index = 0  # Current selected item
        query = ""  # Search query
        selected_items = items  # Filtered list of items

        while True:
            stdscr.clear()
            h, _ = stdscr.getmaxyx()

            # Print query prompt
            stdscr.addstr(0, 0, "Search: " + query)

            # Print the filtered list of items
            for i, item in enumerate(selected_items[: h - 2]):
                if i == current_index:
                    stdscr.addstr(i + 1, 0, item, curses.A_REVERSE)
                else:
                    stdscr.addstr(i + 1, 0, item)

            stdscr.refresh()

            # Wait for user input
            key = stdscr.getch()

            if key == 27:  # ESC key to quit
                break
            elif key == curses.KEY_UP and current_index > 0:
                current_index -= 1
            elif key == curses.KEY_DOWN and current_index < len(selected_items) - 1:
                current_index += 1
            elif key == 10:  # Enter key to select an item
                selected_item = selected_items[current_index]
                return selected_item
                # stdscr.addstr(h - 2, 0, f"Selected: {selected_item}")
                # stdscr.refresh()
                # stdscr.getch()  # Wait for another key press to return to search mode
            elif key == curses.KEY_BACKSPACE:  # Backspace key to delete last character
                query = query[:-1]
            else:
                query += chr(key) if key >= 32 and key <= 126 else ""

            # Perform fuzzy search and update the filtered list
            selected_items = fuzzy_search(query, items)

            # Handle case where no items match the query
            if not selected_items:
                selected_items = ["No matches found"]

            # Ensure that current_index is within the bounds of the filtered list
            current_index = min(current_index, len(selected_items) - 1)

    return curses.wrapper(draw_cli)


def find_common_prefix_and_strip_paths(paths: List[Path]) -> Tuple[str, List[Path]]:
    if not paths:
        return "", paths

    common_prefix = paths[0]
    for path in paths[1:]:
        while not path.is_relative_to(common_prefix):
            common_prefix = Path(common_prefix.parent)
            if str(common_prefix) == "":
                return "", paths

    stripped_paths = [path.relative_to(common_prefix) for path in paths]

    return str(common_prefix), stripped_paths


def parse_dir(dir_path: Optional[Path] = None, rule: str = "*.gitignore") -> List:
    if not dir_path:
        dir_path = GITIGNORE_DIR

    if not dir_path.exists() or not dir_path.is_dir():
        logger.error(f"Path {dir_path} does not exists or is not directory.")
        return []

    gitignore_files = []
    for file in dir_path.rglob(rule):
        gitignore_files.append(file)

    return gitignore_files


def clone_repo_if_not_exists(repo_url: str, force: bool = False):
    gitignore_dir = GITIGNORE_DIR

    if _ := not gitignore_dir.exists() or force:
        if _ and gitignore_dir.is_dir():
            logger.info(f"{gitignore_dir} exists. Removing it...")
            shutil.rmtree(gitignore_dir)
            logger.info(f"Existing {gitignore_dir} was removed.")

        logger.info(
            f"The directory {gitignore_dir} does not exists. Cloning {repo_url}."
        )
        try:
            cmd = ["git", "clone", repo_url, gitignore_dir]
            subprocess.run(cmd, check=True)
            logger.info(f"Repository {repo_url} cloned into {gitignore_dir}.")
        except subprocess.CalledProcessError as e:
            logger.info(f"Error while cloning the repository {repo_url}: {e}.")
        except Exception as e:
            logger.info(f"Unknown error while cloning {repo_url}: {e}.")


def copy_file_to_current_directory(source_path: Path):
    current_dir = os.getcwd()

    destination_path = os.path.join(current_dir, ".gitignore")

    try:
        shutil.copy(source_path, destination_path)
        logger.info(f"File {source_path} was copied into {destination_path}")
    except FileNotFoundError:
        logger.info(f"Error: The file at {source_path} was not found.")
    except PermissionError:
        logger.info(f"Error: Permission denied while copying {source_path}.")
    except Exception as e:
        logger.info(f"Error: {e}")


if __name__ == "__main__":
    gitignore_repo_url = "https://github.com/github/gitignore.git"
    clone_repo_if_not_exists(gitignore_repo_url)
    gitignore_files = parse_dir()

    logger.info(f"Parsed {len(gitignore_files)} files.")

    common_prefix, stripped_paths = find_common_prefix_and_strip_paths(gitignore_files)

    logger.info(
        f"Common prefix is: {common_prefix}. Stripped paths: {stripped_paths[:5]}, ..."
    )

    selected_item = cli([str(path) for path in stripped_paths])
    selected_item_path = common_prefix / Path(selected_item or "")
    logger.info(f"Selected item: {selected_item_path}")

    copy_file_to_current_directory(selected_item_path)
