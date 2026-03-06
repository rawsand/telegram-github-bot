import requests

class StreamWrapper:
    def __init__(self, response, progress_callback=None):
        self.response = response
        self.progress_callback = progress_callback

    def read(self, size=1024*1024):
        chunk = self.response.raw.read(size)

        if chunk and self.progress_callback:
            self.progress_callback(chunk)

        return chunk


class PcloudHandler:

    def __init__(self, token):
        self.token = token


    # ================= SPACE =================

    def get_space(self):

        r = requests.get(
            "https://api.pcloud.com/userinfo",
            params={"auth": self.token}
        ).json()

        return r["quota"] - r["usedquota"]


    # ================= FILE LIST =================

    def list_files(self):

        r = requests.get(
            "https://api.pcloud.com/listfolder",
            params={
                "auth": self.token,
                "folderid": 0
            }
        ).json()

        files = []

        if "metadata" in r:

            for f in r["metadata"]["contents"]:

                if not f["isfolder"]:

                    files.append((f["name"], f["fileid"]))

        return files


    # ================= DELETE =================

    def delete_file(self, fileid):

        requests.get(
            "https://api.pcloud.com/deletefile",
            params={
                "auth": self.token,
                "fileid": fileid
            }
        )


    # ================= STREAM UPLOAD =================

    def upload_stream(self, response, filename, progress_callback=None):

        stream = StreamWrapper(response, progress_callback)

        files = {
            "file": (filename, stream)
        }

        data = {
            "auth": self.token,
            "folderid": 0
        }

        r = requests.post(
            "https://api.pcloud.com/uploadfile",
            files=files,
            data=data
        )

        return r.json()
