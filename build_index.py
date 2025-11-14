from pathlib import Path
import pocketsearch
import tempfile
import urllib.request
import zipfile
import os
import gzip
import shutil

base_dir = Path(__file__).parent

url = "https://s3.amazonaws.com/file.paulgp.com/30d/001-20251113t001852z-1-001.zip"
zip_path = "001-20251113t001852z-1-001.zip"

# download
urllib.request.urlretrieve(url, zip_path)

# make temp dir
tmpdir = tempfile.mkdtemp()

# extract into temp dir
with zipfile.ZipFile(zip_path, "r") as z:
    z.extractall(tmpdir)

# Index directories:
reader = pocketsearch.FileSystemReader(base_dir=str(Path(tmpdir) / "001"))
db_path = base_dir / "app" / "data" / "index.db"
gz_path = base_dir / "app" / "data" / "index.db.gz"

if os.path.exists(db_path):
    os.remove(db_path)
if os.path.exists(gz_path):
    os.remove(gz_path)

with pocketsearch.PocketWriter(db_name=str(db_path), schema=reader.FSSchema) as writer:
    writer.build(reader, verbose=True)
    print("Building spell checker index")
    writer.spell_checker().build()

# Compress DB
with open(db_path, "rb") as f_in, gzip.open(gz_path, "wb", compresslevel=9) as f_out:
    shutil.copyfileobj(f_in, f_out)

# remove original DB to save space
os.remove(db_path)
# delete zip
os.remove(zip_path)