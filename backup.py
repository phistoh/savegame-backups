import hashlib
import logging
import os
import re
import shutil
import sys
import tarfile
import tomllib
from datetime import datetime
from os import path
from pathlib import Path

logger = logging.getLogger(__name__)


def hash_from_file(filename):
    with open(filename, "rb", buffering=0) as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def make_filesystem_suitable(s):
    suitable_string = ""
    for char in s:
        char = char.lower()
        if char.isalnum():
            suitable_string += char
        elif char.isspace():
            suitable_string += "-"
        elif char == "&":
            suitable_string += "-and-"
    if suitable_string == "":
        suitable_string = "_"

    return re.sub(r"(\-)\1+", r"\1", suitable_string)


def get_newest_file_in_folder(path, inverse=False):
    # convert str to Path object
    if isinstance(path, str):
        path = Path(path)
    files = os.listdir(path)
    # append paths to basenames
    paths = [os.path.join(path, basename) for basename in files]
    if paths and inverse:
        return min(paths, key=os.path.getctime)
    elif paths:
        return max(paths, key=os.path.getctime)
    else:
        return None


def count_files(path):
    # convert str to Path object
    if isinstance(path, str):
        path = Path(path)
    files = os.listdir(path)
    return len([f for f in files if os.path.isfile(os.path.join(path, f))])


def generate_archive(source, target):
    if not os.path.exists(os.path.dirname(target)):
        os.makedirs(os.path.dirname(target))

    with tarfile.open(target, "w:gz") as tar:
        tar.add(source, arcname=os.path.basename(source))
        logger.info("Created %s.", target)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # setup global variables
    cwd = Path(os.getcwd())
    with open(cwd / "games.toml", "rb") as toml:
        toml_as_dict = tomllib.load(toml)
        games = toml_as_dict.get("games", [])
        backup_folder = Path(toml_as_dict.get("settings", {}).get("backup_folder", None))
    now = datetime.now()
    date = str(now.date())
    timestamp = int(now.timestamp())
    if not backup_folder:
        logger.warning("No backup folder set. Aborting script...")
        sys.exit(1)

    readme = "# Savegame Backups\n"

    for game in games:
        # setup loop-specific variables
        name = game.get("name", None)
        suitable_name = make_filesystem_suitable(name)
        path = game.get("path", None)
        comment = game.get("comment", None)
        if not (name and path):
            continue
        path = Path(path)

        archive = cwd / f"tmp/{suitable_name}.tar.gz"
        generate_archive(path, archive)

        # TODO: Fix hashing to ignore timestamps
        current_hash = hash_from_file(archive)
        if not os.path.exists(backup_folder / suitable_name):
            os.makedirs(backup_folder / suitable_name)
        last_file = get_newest_file_in_folder(backup_folder / suitable_name)
        if last_file:
            last_hash = hash_from_file(last_file)
        if not last_file or current_hash != last_hash:
            # TODO: add timestamp/number to archive
            shutil.move(archive, f"{backup_folder / suitable_name}/{date}-{suitable_name}-{timestamp}.tar.gz")
            if count_files(backup_folder / suitable_name) > 10:
                oldest_file = get_newest_file_in_folder(backup_folder / suitable_name, True)
                logger.info("More than 10 files found. Deleting oldest one: %s", oldest_file)
                logger.debug(f"TODO: rm {oldest_file}")
        readme += f"\n## {name}\n\n- *Path*: `{path}`"
        if comment:
            readme += f"\n- *Comment*: {comment}"
        readme += f"\n- *Last update*: {now.strftime("%Y-%m-%d, %H:%M")}\n"

    readme += f"\n(Last run: {now.strftime("%Y-%m-%d, %H:%M")})\n"
    logger.debug(f"TODO: save readme as {backup_folder / 'SAVEGAMES.md'}")
    logger.debug(readme)
