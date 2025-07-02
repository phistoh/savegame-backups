#!/usr/bin/env python3

import hashlib
import logging
import os
import re
import shutil
import sys
import tarfile
import textwrap
import tomllib
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s]\t%(asctime)s %(message)s",
    datefmt="%H:%M",
)


def hash_from_file(filename):
    with open(filename, "rb", buffering=0) as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def make_filesystem_suitable(s):
    substitutions = {
        " ": "-",
        "&": "-and-",
        "~": "-",
    }
    s = s.lower()
    suitable = "".join(
        substitutions.get(c, c) if c.isalnum() or c in substitutions else "" for c in s
    )
    if not suitable:
        return "_"
    return re.sub(r"-{2,}", "-", suitable)


def get_newest_file_in_folder(path, inverse=False):
    # convert str to Path object
    if isinstance(path, str):
        path = Path(path)
    paths = [p for p in path.iterdir() if p.is_file()]
    if paths and inverse:
        return min(paths, key=os.path.getctime)
    elif paths:
        return max(paths, key=os.path.getctime)
    else:
        return None


def get_files_sorted_by_ctime(directory):
    return sorted(
        [p for p in Path(directory).iterdir() if p.is_file()],
        key=lambda f: f.stat().st_ctime,
    )


def count_files(path):
    # convert str to Path object
    if isinstance(path, str):
        path = Path(path)
    files = os.listdir(path)
    return len([f for f in files if os.path.isfile(os.path.join(path, f))])


def generate_archive(source, target):
    if not os.path.exists(os.path.dirname(target)):
        os.makedirs(os.path.dirname(target))

    # use bzip2 for consistent hashes
    with tarfile.open(target, "w:bz2") as tar:
        tar.add(source, arcname=os.path.basename(source))
        logger.info("Created %s.", target)


def move_to_trash(file_path):
    trash_dir = Path.home() / ".local/share/Trash"
    files_dir = trash_dir / "files"
    info_dir = trash_dir / "info"
    files_dir.mkdir(parents=True, exist_ok=True)
    info_dir.mkdir(parents=True, exist_ok=True)

    file_path = Path(file_path).resolve()
    dest = files_dir / file_path.name

    # Avoid overwriting files in Trash
    counter = 1
    while dest.exists():
        dest = files_dir / f"{file_path.stem} ({counter}){file_path.suffix}"
        counter += 1

    shutil.move(str(file_path), str(dest))

    info_content = textwrap.dedent(
        f"""\
        [Trash Info]
        Path={file_path}
        DeletionDate={datetime.now().isoformat()}
    """
    )

    info_file = info_dir / (dest.name + ".trashinfo")
    with open(info_file, "w") as f:
        f.write(info_content)

    logger.info("Moved %s to trash.", file_path)


if __name__ == "__main__":
    # setup global variables
    cwd = Path(__file__).resolve().parent
    with open(cwd / "games.toml", "rb") as toml:
        toml_as_dict = tomllib.load(toml)
        games = sorted(toml_as_dict.get("games", []), key=lambda d: d["name"])
        backup_folder = Path(
            toml_as_dict.get("settings", {}).get("backup_folder", None)
        )
    now = datetime.now()
    date = str(now.date())
    timestamp = int(now.timestamp())
    if not backup_folder:
        logger.warning("No backup folder set. Aborting script...")
        sys.exit(1)

    readme = "# Savegame Backups\n"

    for game in games:
        # setup loop-specific variables
        name = game.get("name")
        suitable_name = make_filesystem_suitable(name)
        path = game.get("path")
        comment = game.get("comment")
        if not (name and path):
            continue
        path = Path(path)

        archive = cwd / f"tmp/{suitable_name}.tar.bz2"
        generate_archive(path, archive)

        current_hash = hash_from_file(archive)

        (backup_folder / suitable_name).mkdir(parents=True, exist_ok=True)

        files = get_files_sorted_by_ctime(backup_folder / suitable_name)
        last_file = files[-1] if files else None

        if last_file:
            last_hash = hash_from_file(last_file)

        if not last_file or current_hash != last_hash:
            dest_path = (
                backup_folder
                / suitable_name
                / f"{date}-{suitable_name}-{timestamp}.tar.bz2"
            )
            shutil.move(archive, dest_path)
            logger.info("Moved archive to '%s'", dest_path)

            if len(files) > 10:
                oldest_file = files[0]
                logger.info(
                    "More than 10 files found. Deleting oldest one: %s", oldest_file
                )
                move_to_trash(oldest_file)

        readme += f"\n## {name}\n\n- *Path*: `{path}`"
        if comment:
            readme += f"\n- *Comment*: {comment}"
        readme += f"\n- *Last update*: {now.strftime("%Y-%m-%d, %H:%M")}\n"

    readme += f"\n(Last run: {now.strftime("%Y-%m-%d, %H:%M")})\n"
    with open(backup_folder / "SAVEGAMES.md", "w") as readme_file:
        readme_file.write(readme)

    logger.debug("==========\n%s\n==========\n", readme)
    logger.info("Backup finished on %s", now.strftime("%Y-%m-%d, %H:%M"))
