import requests


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


    # ================= LIST FILES =================

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

        # create upload session
        session = requests.get(
            "https://api.pcloud.com/upload_create",
            params={"auth": self.token}
        ).json()

        uploadid = session["uploadid"]

        uploaded = 0

        for chunk in response.iter_content(8 * 1024 * 1024):

            if not chunk:
                continue

            requests.post(
                "https://api.pcloud.com/upload_write",
                params={
                    "auth": self.token,
                    "uploadid": uploadid
                },
                data=chunk
            )

            uploaded += len(chunk)

            if progress_callback:
                progress_callback(uploaded)

        # save file
        r = requests.get(
            "https://api.pcloud.com/upload_save",
            params={
                "auth": self.token,
                "uploadid": uploadid,
                "folderid": 0,
                "name": filename
            }
        )

        return r.json()
