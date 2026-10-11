import json
import os

base = "images/images"

with open("filenames.json", "r") as f:
    filenames = json.load(f)

with open("image_ids.json", "r") as f:
    ids = json.load(f)

on_disk = set(os.listdir(base))

print("Filenames:", len(filenames))
print("Image IDs:", len(ids))
print("Files on disk:", len(on_disk))
print("Duplicate filenames:", len(filenames) - len(set(filenames)))

missing = [f for f in filenames if f not in on_disk]
print("Missing by exact name:", len(missing), missing[:5])

if missing:
    stems = {
        os.path.splitext(f)[0]: f
        for f in on_disk
    }
    by_stem = [
        f for f in missing
        if os.path.splitext(f)[0] in stems
    ]
    print("Matches by filename without extension:", len(by_stem))
    print(
        "Examples:",
        [(f, stems[os.path.splitext(f)[0]]) for f in by_stem[:3]]
    )
