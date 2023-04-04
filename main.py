import os
import tempfile
import subprocess
from google.cloud import storage

def copy_file(data, context):
    file_name = data["name"]
    print(f"Processing file: {file_name}")
    client = storage.Client()
    bucket = client.bucket(data["bucket"])   
    blob = bucket.blob(file_name)

    
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:     
        blob.download_to_file(temp_file)
        temp_file_path = temp_file.name
        destination_path = f"/tmp/{file_name}"
        os.environ['FILEENV'] = f"{file_name}"
        os.rename(temp_file_path, destination_path)

    print(f"File {file_name} copied to {destination_path}")
    subprocess.call(["python", "process.py"])


