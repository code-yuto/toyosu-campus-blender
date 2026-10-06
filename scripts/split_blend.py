# toyosu_campus.blend を、建物・内装・敷地ごとのファイルに分ける（1回だけ使ったスクリプト。記録として残す）
#
# 実行（バックグラウンドの Blender で、パートごとに1回ずつ）:
#   blender -b toyosu_campus.blend --python scripts/split_blend.py -- part <パート名>
#   blender -b toyosu_campus.blend --python scripts/split_blend.py -- parent
#
# パート: 元のファイルを開き、そのパートのコレクション以外を全部消して、別名で保存する。
#         建物と内装のファイルには、まわりを見るための site.blend をリンクで入れる
# parent: 元のファイルから建物・内装・敷地を消し、各ファイルのコレクションをリンクで読み込む。
#         カメラ・太陽・レンダー設定・ビューレイヤーは親に残す
import os
import sys

import bpy

ROOT = os.path.dirname(bpy.data.filepath)
PARTS = {
    "site": ("site.blend", ["00_Site", "01_PLATEAU参考", "01b_OSM参考"]),
    "研究棟": ("buildings/研究棟.blend", ["02_研究棟"]),
    "教室棟": ("buildings/教室棟.blend", ["03_教室棟"]),
    "交流棟": ("buildings/交流棟.blend", ["04_交流棟"]),
    "本部棟": ("buildings/本部棟.blend", ["05_本部棟"]),
    "教室棟_3F": ("interiors/教室棟_3F.blend", ["06_内装_教室棟3F"]),
}
KEEP_IN_PARENT = ["Cam_広場から研究棟ゲート", "Cam_通りから本部棟", "太陽"]
PARENT_COL = "00_カメラとライト"
SITE_REF_COL = "参考_敷地（site.blend からリンク）"
# 親ファイルで、ビューレイヤーごとに除外するコレクション
EXCLUDE = {"外観": ["01_PLATEAU参考", "01b_OSM参考", "06_内装_教室棟3F"],
           "内装": ["01_PLATEAU参考", "01b_OSM参考", "03_教室棟"]}


def all_objects(col):
    objs = set(col.objects)
    for c in col.children:
        objs |= all_objects(c)
    return objs


def all_children(col):
    cols = set(col.children)
    for c in col.children:
        cols |= all_children(c)
    return cols


def remove_collections(names, keep_objects=()):
    for name in names:
        col = bpy.data.collections.get(name)
        if col is None:
            continue
        for o in all_objects(col):
            if o.name not in keep_objects:
                bpy.data.objects.remove(o)
        for c in all_children(col) | {col}:
            bpy.data.collections.remove(c)


def link_collections(blend_rel, names, parent):
    path = os.path.join(ROOT, blend_rel)
    with bpy.data.libraries.load(path, link=True, relative=True) as (src, dst):
        dst.collections = [n for n in names if n in src.collections]
    for col in dst.collections:
        parent.children.link(col)
    return dst.collections


def save_as(rel):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path, relative_remap=True, compress=True)
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_mainfile(compress=True)


def find_layer_col(lc, name):
    if lc.name == name:
        return lc
    for c in lc.children:
        r = find_layer_col(c, name)
        if r:
            return r


args = sys.argv[sys.argv.index("--") + 1:]
scene = bpy.context.scene

if args[0] == "part":
    rel, keep = PARTS[args[1]]
    others = [c.name for c in scene.collection.children if c.name not in keep]
    remove_collections(others)
    # カメラとライトは親にだけ置く
    for n in KEEP_IN_PARENT:
        o = bpy.data.objects.get(n)
        if o:
            bpy.data.objects.remove(o)
    scene.camera = None
    # ビューレイヤーは1つにする
    for vl in list(scene.view_layers)[1:]:
        scene.view_layers.remove(vl)
    scene.view_layers[0].name = "ViewLayer"
    bpy.data.orphans_purge(do_recursive=True)
    save_as(rel)
    if args[1] != "site":
        # まわりを見るための敷地をリンクで入れる（読むだけ。編集は site.blend で）
        ref = bpy.data.collections.new(SITE_REF_COL)
        scene.collection.children.link(ref)
        site_rel = os.path.relpath(os.path.join(ROOT, "site.blend"), os.path.dirname(bpy.data.filepath))
        with bpy.data.libraries.load(os.path.join(os.path.dirname(bpy.data.filepath), site_rel), link=True, relative=True) as (src, dst):
            dst.collections = ["00_Site"]
        for c in dst.collections:
            ref.children.link(c)
        bpy.ops.wm.save_mainfile(compress=True)
    print("SAVED", bpy.data.filepath, "objects", len(bpy.data.objects))

elif args[0] == "parent":
    # カメラと太陽を親専用のコレクションへ
    pc = bpy.data.collections.new(PARENT_COL)
    scene.collection.children.link(pc)
    for n in KEEP_IN_PARENT:
        o = bpy.data.objects[n]
        for c in list(o.users_collection):
            c.objects.unlink(o)
        pc.objects.link(o)
    split_names = [n for _, (_, cols) in PARTS.items() for n in cols]
    remove_collections(split_names + ["Collection"], keep_objects=KEEP_IN_PARENT)
    bpy.data.orphans_purge(do_recursive=True)
    for key, (rel, cols) in PARTS.items():
        link_collections(rel, cols, scene.collection)
    for vl_name, excl in EXCLUDE.items():
        vl = scene.view_layers.get(vl_name)
        if vl is None:
            continue
        for n in excl:
            lc = find_layer_col(vl.layer_collection, n)
            if lc:
                lc.exclude = True
    bpy.ops.wm.save_mainfile(compress=True)
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_mainfile(compress=True)
    print("SAVED parent objects", len(bpy.data.objects), "libraries", [l.filepath for l in bpy.data.libraries])
