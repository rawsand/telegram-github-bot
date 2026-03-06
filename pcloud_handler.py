import requests


class PcloudHandler:

    def __init__(self, token):
        self.token = token

    def get_space(self):

        r = requests.get(
            "https://api.pcloud.com/userinfo",
            params={"auth": self.token}
        ).json()

        quota = r["quota"]
        used = r["usedquota"]

        return quota - used

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

    def delete_file(self, fileid):

        requests.get(
            "https://api.pcloud.com/deletefile",
            params={
                "auth": self.token,
                "fileid": fileid
            }
        )

    def upload_stream(self, stream, filename):

        url = "https://api.pcloud.com/uploadfile"

        files = {
            "file": (filename, stream)
        }

        data = {
            "auth": self.token,
            "folderid": 0
        }

        r = requests.post(url, files=files, data=data)

        return r.json()
