import requests
import os

class PCloudHandler:
    def __init__(self, access_token):
        self.access_token = access_token
        self.api_url = "https://api.pcloud.com"

    def get_client(self):
        return self

    def get_space_info(self):
        """Return total and used bytes"""
        res = requests.get(f"{self.api_url}/userinfo", params={"access_token": self.access_token}).json()
        return res.get("quota", 0), res.get("used", 0)

    def upload_file(self, file_stream, filename, progress_callback=None):
        """Upload file to root folder"""
        url = f"{self.api_url}/uploadfile"
        files = {"file": (filename, file_stream)}
        params = {"access_token": self.access_token, "path": "/"}
        with requests.post(url, params=params, files=files, stream=True) as r:
            if r.status_code == 200:
                return r.json()
            else:
                return None

    def list_files(self, limit=5):
        """Return first `limit` files from root folder"""
        res = requests.get(f"{self.api_url}/listfolder", params={"access_token": self.access_token, "folderid": 0}).json()
        entries = res.get("metadata", {}).get("contents", [])
        return entries[:limit]

    def delete_file(self, fileid):
        """Delete file by pCloud fileid"""
        res = requests.get(f"{self.api_url}/deletefile", params={"access_token": self.access_token, "fileid": fileid}).json()
        return res.get("result") == 0
