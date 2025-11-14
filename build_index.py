from pathlib import Path
import pocketsearch
import tempfile
import urllib.request
import zipfile
import os

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
reader = pocketsearch.FileSystemReader(base_dir=str(tmpdir + "/001/"))
with pocketsearch.PocketWriter(db_name=str(base_dir / "data" / "index.db"), schema=reader.FSSchema) as writer:
    writer.build(reader,verbose=True)
    print("Building spell checker index")
    writer.spell_checker().build()

# delete zip
os.remove(zip_path)