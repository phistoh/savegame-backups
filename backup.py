from datetime import date
import os
from os import path
import tomllib
import hashlib
import re
from pathlib import Path

def hash_from_file(filename):
    # with open(filename, "rb", buffering=0) as f:
        # return hashlib.file_digest(f, "sha256").hexdigest()
    return hashlib.sha256(str(filename).encode()).hexdigest()

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

def get_newest_file_in_folder(path):
    # convert str to Path object
    if isinstance(path, str):
        path = Path(path)
    files = os.listdir(path)
    # append paths to basenames
    paths = [os.path.join(path, basename) for basename in files]
    if paths:
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

    # archive and zip files
    return target

if __name__ == "__main__":
    # setup variables
    cwd = Path(os.getcwd())
    print("TODO: Get backup folder from TOML?")
    backup_folder = cwd
    date = date.today().isoformat()
    games = []
    with open(cwd / "games.toml", "rb") as toml:
        toml_as_dict = tomllib.load(toml)
        games = toml_as_dict.get("games", [])

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

        current_hash = hash_from_file(archive)
        if not os.path.exists(backup_folder / suitable_name):
            os.makedirs(backup_folder / suitable_name)
        last_file = get_newest_file_in_folder(backup_folder / suitable_name)
        if last_file:
            last_hash = hash_from_file(last_file)
        if not last_file or current_hash != last_hash:
            print(f"TODO: mv {archive / suitable_name}.tar.gz {backup_folder / suitable_name}/{date}-{suitable_name}")
            if count_files(backup_folder / suitable_name) > 10:
                print(f"TODO: rm 'oldest archive in {backup_folder / suitable_name}/'")
        readme += f"\n## {name}\n\n- *Path*: `{path}`"
        if comment:
            readme += f"\n- *Comment*: {comment}"
        readme += f"\n- *Last update*: {date}\n"

    readme += f"\n(Last run: {date})\n"
    print(f"TODO: save readme as {backup_folder / 'README.md'}")
    print(readme)