import subprocess

def get_download_speed(download_info):
    bytes = download_info.bytes
    elapsed = download_info.elapsed
    return bytes/elapsed

def get_upload_speed(upload_info):
    bytes = upload_info.bytes
    elapsed = upload_info.elapsed
    return bytes/elapsed
    

def get_internet_speed():
    output = subprocess.run(["speedtest", "--format=json"])
    download_speed = get_download_speed(output.download)
    upload_speed = get_upload_speed(output.upload)
    return (download_speed, upload_speed)

if __name__ == "__main__":
    (download_speed, upload_speed) = get_internet_speed()
    print(download_speed)
    print(upload_speed)