# 建物ファイルを「建物の足元の中心が原点、長い辺が X 軸」の形に作り直し、建物の寸法の箱を置く
#   blender -b buildings/<建物>.blend --python scripts/make_building_boxes.py -- <建物>
#   blender -b toyosu_campus.blend --python scripts/make_building_boxes.py -- parent
#
# 寸法と、地図上の位置・向きは buildings/配置.json に書いてある。
# 建物ファイル:
#   - 今までの形は「旧ブロックアウト（参考）」コレクションに移し、建物の座標に合わせて動かして非表示にする
#   - 建物のコレクション（02_研究棟 など）には、寸法ぴったりの箱だけを置く
#   - 敷地の参考（site.blend）は、建物の座標に合わせて逆向きに置き直す
# 親ファイル:
#   - 各建物のコレクションを「コレクションインスタンス」で読み込み、配置.json の位置と向きに置く
import json
import math
import os
import sys

import bpy
from mathutils import Matrix

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = json.load(open(os.path.join(ROOT, "buildings", "配置.json"), encoding="utf-8"))
OLD_COL = "旧ブロックアウト（参考）"
SITE_REF_COL = "参考_敷地（site.blend からリンク）"
BOX_MAT = "建物の箱"


def placement(s):
    """建物の座標 → 地図の座標"""
    return Matrix.Translation((s["center"][0], s["center"][1], 0)) @ Matrix.Rotation(s["theta"], 4, "Z")


def box_mesh(name, L, W, H, x, y):
    me = bpy.data.meshes.new(name)
    v = [(x + sx * L / 2, y + sy * W / 2, z) for z in (0, H) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    me.from_pydata(v, [], f)
    me.update()
    return me


def box_material():
    m = bpy.data.materials.get(BOX_MAT) or bpy.data.materials.new(BOX_MAT)
    m.diffuse_color = (0.8, 0.8, 0.82, 1)
    return m


def layer_col(lc, name):
    if lc.name == name:
        return lc
    for c in lc.children:
        r = layer_col(c, name)
        if r:
            return r


def make_building(key):
    s = SPEC[key]
    M = placement(s)
    Minv = M.inverted()
    scene = bpy.context.scene
    main = bpy.data.collections[s["collection"]]

    # 1. 今までの形を「旧ブロックアウト（参考）」へ移し、建物の座標へ動かす
    old = bpy.data.collections.get(OLD_COL) or bpy.data.collections.new(OLD_COL)
    if old.name not in scene.collection.children:
        scene.collection.children.link(old)
    for o in list(main.objects):
        main.objects.unlink(o)
        old.objects.link(o)
    for o in old.objects:
        if o.parent is None:
            o.matrix_world = Minv @ o.matrix_world
        o.hide_select = True
    lc = layer_col(scene.view_layers[0].layer_collection, OLD_COL)
    lc.hide_viewport = True

    # 2. 寸法の箱
    mat = box_material()
    for b in s["boxes"]:
        me = box_mesh(b["name"], b["L"], b["W"], b["H"], 0, 0)
        me.materials.append(mat)
        o = bpy.data.objects.new(b["name"], me)
        o.location = (b["pos"][0], b["pos"][1], 0)  # 原点は箱の底面の中心
        o["長さ_X_m"] = round(b["L"], 2)
        o["幅_Y_m"] = round(b["W"], 2)
        o["高さ_Z_m"] = b["H"]
        main.objects.link(o)

    # 3. 敷地の参考を、建物の座標に合わせて置き直す（コレクションインスタンス）
    ref = bpy.data.collections.get(SITE_REF_COL)
    if ref:
        site = [c for c in ref.children if c.library]
        for c in site:
            ref.children.unlink(c)
            e = bpy.data.objects.new("敷地_参考", None)
            e.instance_type = "COLLECTION"
            e.instance_collection = c
            e.matrix_world = Minv
            e.hide_select = True
            ref.objects.link(e)

    # 4. 編集しやすい状態にそろえる
    scene["配置_地図上の中心_X"] = s["center"][0]
    scene["配置_地図上の中心_Y"] = s["center"][1]
    scene["配置_回転_度"] = math.degrees(s["theta"])
    scene.cursor.location = (0, 0, 0)
    scene.cursor.rotation_euler = (0, 0, 0)
    scene.transform_orientation_slots[0].type = "GLOBAL"
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    bpy.ops.wm.save_mainfile()
    print("DONE", key, [o.name for o in main.objects])


def make_parent():
    scene = bpy.context.scene
    for key, s in SPEC.items():
        name = s["collection"]
        linked = next((c for c in bpy.data.collections if c.name == name and c.library), None)
        if linked is None:
            print("NOT FOUND", name)
            continue
        if linked.name in [c.name for c in scene.collection.children if c.library]:
            scene.collection.children.unlink(linked)
        wrap_name = name + "_配置"
        wrap = bpy.data.collections.get(wrap_name) or bpy.data.collections.new(wrap_name)
        if wrap.name not in scene.collection.children:
            scene.collection.children.link(wrap)
        e = bpy.data.objects.get(key + "_配置") or bpy.data.objects.new(key + "_配置", None)
        e.instance_type = "COLLECTION"
        e.instance_collection = linked
        e.matrix_world = placement(s)
        if e.name not in wrap.objects:
            wrap.objects.link(e)
    # 内装ビューでは教室棟を除外（以前と同じ）
    vl = scene.view_layers.get("内装")
    if vl:
        lc = layer_col(vl.layer_collection, "03_教室棟_配置")
        if lc:
            lc.exclude = True
    bpy.ops.wm.save_mainfile()
    print("DONE parent", [c.name for c in scene.collection.children])


arg = sys.argv[sys.argv.index("--") + 1]
if arg == "parent":
    make_parent()
else:
    make_building(arg)
