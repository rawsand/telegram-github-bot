import requests

class PcloudHandler:
    def __init__(self, token):
        self.token = token

    def get_space(self):
        r = requests.get("https://api.pcloud.com/userinfo", params={"auth": self.token}).json()
        return r["quota"] - r["usedquota"]

    def list_files(self):
        r = requests.get("https://api.pcloud.com/listfolder", params={"auth": self.token, "folderid": 0}).json()
        files = []
        if "metadata" in r:
            for f in r["metadata"]["contents"]:
                if not f["isfolder"]:
                    files.append((f["name"], f["fileid"]))
        return files

    def delete_file(self, fileid):
        requests.get("https://api.pcloud.com/deletefile", params={"auth": self.token, "fileid": fileid})

    def upload_stream(self, response_stream, filename, progress_callback=None):
        url = "https://api.pcloud.com/uploadfile"
        with requests.post(url, params={"auth": self.token, "folderid": 0}, files={"file": (filename, StreamWrapper(response_stream, progress_callback))}) as r:
            return r.json()

class StreamWrapper:
    def __init__(self, response, progress_callback=None):
        self.response = response
        self.progress_callback = progress_callback

    def read(self, chunk_size=1024*1024):
        chunk = self.response.raw.read(chunk_size)
        if chunk and self.progress_callback:
            self.progress_callback(chunk)
        return chunk
