# 検証に使う航空写真をタイルで取得してつなぎ、四隅のローカル座標を JSON に書く
#   python fetch_aerial.py
# 出力:
#   toyosu_aerial_z18.jpg / .json : 国土地理院 シームレス空中写真（2019年以前・正射。位置合わせの基準）
#   esri_z19.jpg / .json          : Esri World Imagery（新しい。高い建物は屋根が倒れ込んで写る）
# ※ 画像そのものはリポジトリに入れない（Esri は再配布不可）。個人の確認用に手元でだけ使う
import json
import math
import os
import sys
import urllib.request

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "09_OpenStreetMap"))
from tm import to_plane  # noqa: E402

OFF = (-3322.0, -37645.0)
UA = {"User-Agent": "toyosu-campus-blender/1.0"}
SOURCES = {
    "toyosu_aerial_z18": dict(z=18, xs=range(232865, 232871), ys=range(103242, 103247),
                              url="https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg"),
    "esri_z19": dict(z=19, xs=range(465732, 465741), ys=range(206486, 206493),
                     url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"),
}


def px_to_local(z, x0, y0, px, py):
    n = 2 ** z
    lon = (x0 + px / 256) / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y0 + py / 256) / n))))
    x, y = to_plane(lat, lon)
    return x - OFF[0], y - OFF[1]


for name, s in SOURCES.items():
    tile_dir = f"tiles_{name}"
    os.makedirs(tile_dir, exist_ok=True)
    W, H = 256 * len(s["xs"]), 256 * len(s["ys"])
    mosaic = Image.new("RGB", (W, H))
    for i, tx in enumerate(s["xs"]):
        for j, ty in enumerate(s["ys"]):
            path = os.path.join(tile_dir, f"{s['z']}_{tx}_{ty}.jpg")
            if not os.path.exists(path):
                url = s["url"].format(z=s["z"], x=tx, y=ty)
                open(path, "wb").write(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read())
            mosaic.paste(Image.open(path), (i * 256, j * 256))
    corners = {k: px_to_local(s["z"], s["xs"][0], s["ys"][0], *p)
               for k, p in {"tl": (0, 0), "tr": (W, 0), "bl": (0, H), "br": (W, H)}.items()}
    mosaic.save(f"{name}.jpg", quality=92)
    json.dump({"size": [W, H], "corners_local": corners}, open(f"{name}.json", "w"), indent=1)
    print(name, W, H)
