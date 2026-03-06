import requests

class PcloudHandler:

    def __init__(self, token):
        self.token = token
        self.base = "https://api.pcloud.com"

    def get_free_space(self):
        url = f"{self.base}/userinfo"
        params = {"access_token": self.token}

        r = requests.get(url, params=params).json()

        quota = r["quota"]
        used = r["usedquota"]

        free = quota - used
        return free

    def upload_file(self, file_stream, filename):
        url = f"{self.base}/uploadfile"

        params = {
            "access_token": self.token,
            "filename": filename,
            "folderid": 0
        }

        files = {
            "file": (filename, file_stream)
        }

        r = requests.post(url, params=params, files=files)

        return r.json()
