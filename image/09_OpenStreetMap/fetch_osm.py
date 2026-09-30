# OpenStreetMap からキャンパス周辺の建物・道路などを取得して、ローカル座標(m)の JSON にする
#   python fetch_osm.py
# 出力: campus_geom.json（Overpass の生データ） / campus_features_local.json（ローカル座標）
# ローカル座標 = 平面直角座標系 第IX系 (EPSG:6677) から (X=-3322, Y=-37645) を引いたもの。tm.py を参照
import json
import urllib.parse
import urllib.request

from tm import to_plane

OFF = (-3322.0, -37645.0)
BBOX = "35.6585,139.7925,35.6630,139.7980"  # 南, 西, 北, 東
QUERY = f"""[out:json][timeout:90];
(
  way({BBOX})["building:part"];
  way({BBOX})[building];
  way({BBOX})[highway];
  way({BBOX})[leisure];
  way({BBOX})[natural];
  way({BBOX})[landuse];
  way({BBOX})[amenity];
);
out geom;"""

req = urllib.request.Request(
    "https://overpass-api.de/api/interpreter",
    data=urllib.parse.urlencode({"data": QUERY}).encode(),
    headers={"User-Agent": "toyosu-campus-blender/1.0"},
)
raw = urllib.request.urlopen(req, timeout=120).read()
open("campus_geom.json", "wb").write(raw)

out = []
for e in json.loads(raw)["elements"]:
    if e["type"] != "way" or "geometry" not in e:
        continue
    poly = [tuple(round(v - o, 2) for v, o in zip(to_plane(g["lat"], g["lon"]), OFF)) for g in e["geometry"]]
    out.append({"id": e["id"], "tags": e.get("tags", {}), "poly": poly})
json.dump(out, open("campus_features_local.json", "w", encoding="utf-8"), ensure_ascii=False)
print("features:", len(out))
