# PLATEAU 東京都23区（2020年度）の巨大な zip から、キャンパスのある地域メッシュだけを取り出す
#   python fetch_plateau.py
# zip 全体（OBJ 約2.1GB / CityGML）はダウンロードせず、HTTP の Range で必要な部分だけ読む。
# 取り出すもの:
#   OBJ    : 53393693（キャンパス）と 53393694（東隣）の建物・地形・橋 → このフォルダに展開
#   CityGML: 53393693 の建物（計測高さなどの属性つき） → citygml/
import io
import os
import urllib.request
import zipfile

BASE = "https://gsic-opendata.s3.ap-northeast-1.amazonaws.com/national-gov/mlit/city-bureau/3d-city-model/2020/plateau-tokyo23ku/"
OBJ_ZIP = BASE + "13100_tokyo23-ku_2020_obj_3_op.zip"
GML_ZIP = BASE + "13100_tokyo23-ku_2020_citygml_3_2_op.zip"


class HTTPRangeFile(io.RawIOBase):
    """zipfile から seek/read できる、Range リクエストで読むファイル"""

    def __init__(self, url):
        self.url, self.pos = url, 0
        head = urllib.request.urlopen(urllib.request.Request(url, method="HEAD"))
        self.size = int(head.headers["Content-Length"])

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else (self.pos + offset if whence == 1 else self.size + offset)
        return self.pos

    def readinto(self, buf):
        if self.pos >= self.size:
            return 0
        end = min(self.pos + len(buf), self.size) - 1
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}"})
        data = urllib.request.urlopen(req).read()
        buf[:len(data)] = data
        self.pos += len(data)
        return len(data)


def extract(url, match, dest, flatten=False):
    z = zipfile.ZipFile(io.BufferedReader(HTTPRangeFile(url), buffer_size=1 << 20))
    for info in z.infolist():
        if info.is_dir() or not match(info.filename):
            continue
        rel = os.path.basename(info.filename) if flatten else info.filename.split("/", 1)[1]
        path = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        open(path, "wb").write(z.read(info))
        print("saved", path)


if __name__ == "__main__":
    extract(OBJ_ZIP, lambda n: "53393693" in n or "53393694" in n, ".")
    extract(GML_ZIP, lambda n: "53393693" in n and "/bldg/" in n and n.endswith(".gml"), "citygml", flatten=True)
