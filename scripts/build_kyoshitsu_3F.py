# 教室棟 3F 廊下（ロビー＋吹き抜け）を組み立てるスクリプト
# Blender の Python コンソールか MCP から exec(open(path, encoding="utf-8").read()) で実行する。
# 何度実行しても、コレクション「06_内装_教室棟3F」の中身を作り直すだけ。
#
# 座標は「教室棟_基準」エンプティ基準のローカル座標（メートル）
#   X: 建物の長手方向（南西端 -42 → 北東端 +42）
#   Y: +側が北西（道路側・教室側）、-側が南東（中庭側・ロビー側）
#   Z: 各階の床(FL)からの高さ
# 寸法は 2008 年の学会案内の 3F/4F 平面図と PLATEAU/OSM から読み取った推定値。
import bpy, bmesh, math
from mathutils import Vector, Matrix

COL_NAME = "06_内装_教室棟3F"

# ---------- レイアウト定数 ----------
X0, X1 = -42.0, 42.0          # 建物の長手方向の端
YSE, YNW = -11.75, 11.5       # 南東面（ロビー側ガラス） / 北西面（教室の外壁）
YCW = -0.9                    # 教室と廊下の間の壁
YCOR = -3.9                   # 廊下と吹き抜け（手すり）の境目
CORE_L, CORE_R = -35.3, 36.1  # 両端の階段・トイレのコア
ROOMS = [(-34.35, -18.6), (-18.6, -2.2), (-2.2, 12.2), (12.2, 24.85), (24.85, 36.05)]
VOID3 = (-21.45, -11.15)      # 3F の床にあいている 2F への吹き抜け（X範囲）
ATR = (-16.35, 13.35)         # 4F から上の大きな吹き抜け（X範囲。上りエスカレーターの降り口の手前まで）
ESC_DN = (-11.15, -0.05)      # 3F→2F の下りエスカレーター（X範囲）
ESC_UP = (3.25, 14.55)        # 3F→4F の上りエスカレーター（X範囲）
ESC_Y = (-7.0, -4.6)
FLOOR_H = 5.0                 # 階高（エスカレーター 11.1m・30° から逆算）
CEIL = 3.0                    # 天井高
FL3_WORLD_Z = 11.0            # 3F の床の高さ（地上から）
SLAB = 0.3
FLOORS = {2: -FLOOR_H, 3: 0.0, 4: FLOOR_H, 5: 2 * FLOOR_H, 6: 3 * FLOOR_H}


def bsdf(m):
    for n in m.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            return n


def mat(name, rgb, rough=0.6, metal=0.0, trans=0.0, emit=0.0, alpha=1.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = (*rgb, alpha)
    b = bsdf(m)
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Transmission Weight"].default_value = trans
    if trans > 0:
        b.inputs["IOR"].default_value = 1.45
    if emit > 0:
        b.inputs["Emission Color"].default_value = (*rgb, 1)
        b.inputs["Emission Strength"].default_value = emit
    return m


M = dict(
    floor=mat("内装_床カーペット", (0.07, 0.07, 0.08), 0.95),
    wall=mat("内装_壁", (0.82, 0.82, 0.80), 0.7),
    ceil=mat("内装_天井", (0.88, 0.88, 0.87), 0.8),
    door=mat("内装_ドア", (0.30, 0.31, 0.33), 0.5),
    frame=mat("内装_金属枠", (0.55, 0.56, 0.58), 0.35, 1.0),
    glass=mat("内装_ガラス", (0.75, 0.85, 0.85), 0.05, alpha=0.25),
    light=mat("内装_照明", (1.0, 0.97, 0.92), 0.5, emit=15.0),
    col=mat("内装_柱", (0.78, 0.78, 0.78), 0.5),
    esc=mat("内装_エスカレーター", (0.22, 0.22, 0.24), 0.4, 0.6),
    slab=mat("内装_スラブ", (0.6, 0.6, 0.6), 0.8),
    sign=mat("内装_室名札", (0.1, 0.25, 0.45), 0.5),
)
# ガラスはアルファで半透明にする（EEVEE で軽く、確実に透けて見える）
bsdf(M["glass"]).inputs["Alpha"].default_value = 0.12
if hasattr(M["glass"], "surface_render_method"):
    M["glass"].surface_render_method = 'BLENDED'

# ---------- 準備：コレクションを空にする ----------
scene = bpy.context.scene
col = bpy.data.collections.get(COL_NAME)
if col is None:
    col = bpy.data.collections.new(COL_NAME)
    scene.collection.children.link(col)
base = bpy.data.objects["教室棟_基準"]
for o in list(col.objects):
    if o is base:
        continue
    data = o.data
    bpy.data.objects.remove(o)
    if data is not None and data.users == 0:
        if isinstance(data, bpy.types.Mesh):
            bpy.data.meshes.remove(data)
        elif isinstance(data, bpy.types.Light):
            bpy.data.lights.remove(data)
        elif isinstance(data, bpy.types.Camera):
            bpy.data.cameras.remove(data)


def empty(name, parent, z):
    e = bpy.data.objects.new(name, None)
    col.objects.link(e)
    e.parent = parent
    e.matrix_parent_inverse = Matrix()
    e.location = (0, 0, z)
    e.empty_display_size = 1.5
    return e


fl = {k: empty(f"教室棟{k}F_FL", base, FL3_WORLD_Z + z) for k, z in FLOORS.items()}


def box(name, x0, x1, y0, y1, z0, z1, m, parent):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    for v in bm.verts:
        v.co.x = x0 if v.co.x < 0 else x1
        v.co.y = y0 if v.co.y < 0 else y1
        v.co.z = z0 if v.co.z < 0 else z1
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    col.objects.link(o)
    o.parent = parent
    o.matrix_parent_inverse = Matrix()
    return o


def cut(target, rects, z0=-5, z1=5):
    """target から XY の矩形 (x0,x1,y0,y1) をくり抜く"""
    for i, (x0, x1, y0, y1) in enumerate(rects):
        c = box(f"_cut{i}", x0, x1, y0, y1, z0, z1, M["slab"], target.parent)
        md = target.modifiers.new("cut", 'BOOLEAN')
        md.operation = 'DIFFERENCE'
        md.object = c
        md.solver = 'EXACT'
        with bpy.context.temp_override(object=target, active_object=target, selected_objects=[target]):
            bpy.ops.object.modifier_apply(modifier=md.name)
        me = c.data
        bpy.data.objects.remove(c)
        bpy.data.meshes.remove(me)


def array(o, count, dx=0.0, dy=0.0):
    md = o.modifiers.new("Array", 'ARRAY')
    md.count = count
    md.use_relative_offset = False
    md.use_constant_offset = True
    md.constant_offset_displace = (dx, dy, 0)
    return md


# ---------- 各階共通のパーツ ----------
def floor_level(k):
    p = fl[k]
    tag = f"{k}F"
    # 床スラブ（ロビー＋廊下）。床の開口：3F は 2F への吹き抜けと下りエスカレーター、4F 以上は大吹き抜け
    slab = box(f"{tag}_床", CORE_L, CORE_R, YSE, YCW, -SLAB, 0, M["floor"], p)
    if k == 3:
        cut(slab, [(VOID3[0], VOID3[1], YSE + 0.8, YCOR),
                   (ESC_DN[0], ESC_DN[1], ESC_Y[0], ESC_Y[1])])
    elif k >= 4:
        cut(slab, [(ATR[0], ATR[1], YSE + 0.8, YCOR)])
    # 床の側面と裏面は天井と同じ白にする（上面だけカーペット）
    slab.data.materials.append(M["ceil"])
    for poly in slab.data.polygons:
        if poly.normal.z < 0.5:
            poly.material_index = 1
    # 天井（下の階の吹き抜けと同じ位置をあける）
    if k < 6:
        ceil = box(f"{tag}_天井", CORE_L, CORE_R, YSE, YCW, CEIL, CEIL + 0.05, M["ceil"], p)
        if k >= 3:
            cut(ceil, [(ATR[0], ATR[1], YSE + 0.8, YCOR)])
    # 教室側の壁（ドア開口つき）
    wall = box(f"{tag}_教室壁", CORE_L, CORE_R, YCW - 0.08, YCW + 0.08, 0, FLOOR_H - SLAB, M["wall"], p)
    doors = []
    for (a, b) in ROOMS:
        for dx in (a + 1.2, b - 2.4):          # 各教室に前後2か所のドア（幅1.2m）
            doors.append((dx, dx + 1.2, YCW - 0.5, YCW + 0.5))
    cut(wall, doors, 0.0, 2.3)
    for i, (x0, x1, _, _) in enumerate(doors):
        d = box(f"{tag}_ドア_{i:02d}", x0 + 0.03, x1 - 0.03, YCW - 0.02, YCW + 0.02, 0, 2.27, M["door"], p)
        box(f"{tag}_ドア窓_{i:02d}", x0 + 0.45, x1 - 0.45, YCW - 0.04, YCW + 0.04, 1.2, 1.9, M["glass"], p)
        box(f"{tag}_ドア枠_{i:02d}", x0 - 0.05, x1 + 0.05, YCW - 0.1, YCW - 0.06, 2.3, 2.38, M["frame"], p)
    # 室名札（教室ごと）
    for j, (a, b) in enumerate(ROOMS):
        box(f"{tag}_室名札_{k}0{j + 1}", a + 2.6, a + 3.2, YCW - 0.12, YCW - 0.09, 2.0, 2.3, M["sign"], p)
    # 教室の反対側の外壁（北西面）と、教室間の仕切り（ドアを閉めているので中は作らない）
    box(f"{tag}_北西外壁", CORE_L, CORE_R, YNW - 0.2, YNW, 0, FLOOR_H - SLAB, M["wall"], p)
    # 両端のコア（階段・トイレ）
    box(f"{tag}_コア左", X0, CORE_L, YSE, YNW, 0, FLOOR_H - SLAB, M["wall"], p)
    box(f"{tag}_コア右", CORE_R, X1, YSE, YNW, 0, FLOOR_H - SLAB, M["wall"], p)
    # 南東面のガラスカーテンウォール（方立て 1.75m ピッチ）
    box(f"{tag}_ガラス面", CORE_L, CORE_R, YSE, YSE + 0.02, 0, FLOOR_H - SLAB, M["glass"], p)
    mul = box(f"{tag}_方立て", CORE_L, CORE_L + 0.06, YSE + 0.02, YSE + 0.14, 0, FLOOR_H - SLAB, M["frame"], p)
    array(mul, int((CORE_R - CORE_L) / 1.75) + 1, dx=1.75)
    box(f"{tag}_腰見切り", CORE_L, CORE_R, YSE + 0.02, YSE + 0.2, 0, 0.1, M["frame"], p)
    # 丸柱（南東面の内側、7m ピッチ）
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.35, depth=FLOOR_H - SLAB,
                                        location=(0, 0, 0))
    c = bpy.context.active_object
    for uc in list(c.users_collection):
        uc.objects.unlink(c)
    col.objects.link(c)
    c.name = f"{tag}_丸柱"
    c.data.materials.append(M["col"])
    c.parent = p
    c.matrix_parent_inverse = Matrix()
    c.location = (-35.0 + 3.5, YSE + 1.3, (FLOOR_H - SLAB) / 2)
    array(c, 10, dx=7.0)
    # 天井照明（ダウンライト 2.4m ピッチ：廊下に1列、ロビーに2列）
    if k < 6:
        for row, y in enumerate((YCW - 1.5, YSE + 3.0, YSE + 5.5)):
            lt = box(f"{tag}_照明_{row}", CORE_L + 1.0, CORE_L + 1.4, y - 0.2, y + 0.2, CEIL - 0.02, CEIL, M["light"], p)
            array(lt, int((CORE_R - CORE_L - 2) / 2.4), dx=2.4)
        # 実際に部屋を照らすのは細長い面光源（見た目のダウンライトは発光面だけ）
        for nm, y, wd, en in ((f"{tag}_面光源_廊下", YCW - 1.5, 2.0, 2500),
                              (f"{tag}_面光源_ロビー", YSE + 4.2, 4.0, 4000)):
            ld = bpy.data.lights.get(nm) or bpy.data.lights.new(nm, 'AREA')
            ld.shape = 'RECTANGLE'
            ld.size = CORE_R - CORE_L - 2
            ld.size_y = wd
            ld.energy = en
            ld.color = (1.0, 0.95, 0.88)
            lo = bpy.data.objects.new(nm, ld)
            col.objects.link(lo)
            lo.parent = p
            lo.matrix_parent_inverse = Matrix()
            lo.location = ((CORE_L + CORE_R) / 2, y, CEIL - 0.05)
    return p


def railing(p, tag, x0, x1, y0, y1):
    """吹き抜けのまわりのガラス手すり（高さ1.1m）"""
    H_R = 1.1
    sides = [
        (x0, x1, y1 - 0.02, y1 + 0.02),   # 廊下側
        (x0 - 0.02, x0 + 0.02, y0, y1),   # 左
        (x1 - 0.02, x1 + 0.02, y0, y1),   # 右
    ]
    for i, (a, b, c, d) in enumerate(sides):
        box(f"{tag}_手すりガラス_{i}", a, b, c, d, 0.05, H_R - 0.05, M["glass"], p)
        box(f"{tag}_手すり笠木_{i}", a - 0.03, b + 0.03, c - 0.03, d + 0.03, H_R - 0.05, H_R, M["frame"], p)
        box(f"{tag}_手すり下枠_{i}", a - 0.01, b + 0.01, c - 0.01, d + 0.01, 0.0, 0.05, M["frame"], p)


def escalator(p, name, x0, x1, going_up):
    """30° のエスカレーター（簡略形：本体＋ステップ面＋ガラスの欄干）"""
    rise = FLOOR_H if going_up else -FLOOR_H
    land = 1.2
    run = (x1 - x0) - 2 * land
    y0, y1 = ESC_Y
    bm = bmesh.new()
    # 側面形状（X-Z）をつくって Y 方向に押し出す。x0 側がこの階、x1 側が上（下）の階
    prof = [(x0, 0), (x0 + land, 0), (x1 - land, rise), (x1, rise),
            (x1, rise - 1.0), (x1 - land, rise - 1.0), (x0 + land, -1.0), (x0, -1.0)]
    vs = [bm.verts.new((x, y0, z)) for x, z in prof]
    f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, verts=[v for v in r['geom'] if isinstance(v, bmesh.types.BMVert)], vec=(0, y1 - y0, 0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(M["esc"])
    o = bpy.data.objects.new(name, me)
    col.objects.link(o)
    o.parent = p
    o.matrix_parent_inverse = Matrix()
    # 欄干ガラス（両側）
    for side, y in (("L", y0 + 0.05), ("R", y1 - 0.05)):
        bm = bmesh.new()
        pr = [(x0, 0.1), (x0 + land, 0.1), (x1 - land, rise + 0.1), (x1, rise + 0.1),
              (x1, rise + 1.0), (x1 - land, rise + 1.0), (x0 + land, 1.0), (x0, 1.0)]
        vs = [bm.verts.new((x, y - 0.01, z)) for x, z in pr]
        f = bm.faces.new(vs)
        r = bmesh.ops.extrude_face_region(bm, geom=[f])
        bmesh.ops.translate(bm, verts=[v for v in r['geom'] if isinstance(v, bmesh.types.BMVert)], vec=(0, 0.02, 0))
        me = bpy.data.meshes.new(f"{name}_欄干{side}")
        bm.to_mesh(me)
        bm.free()
        me.materials.append(M["glass"])
        g = bpy.data.objects.new(f"{name}_欄干{side}", me)
        col.objects.link(g)
        g.parent = p
        g.matrix_parent_inverse = Matrix()


# ---------- 組み立て ----------
for k in FLOORS:
    floor_level(k)
# 吹き抜けの手すり
railing(fl[3], "3F", VOID3[0], VOID3[1], YSE + 0.8, YCOR)
for k in (4, 5, 6):
    railing(fl[k], f"{k}F", ATR[0], ATR[1], YSE + 0.8, YCOR)
# 下りエスカレーターの開口の手すり（3F）
railing(fl[3], "3F_ESC", ESC_DN[0], ESC_DN[1], ESC_Y[0], ESC_Y[1])
# エスカレーター
escalator(fl[3], "エスカレーター_3F→2F", ESC_DN[0], ESC_DN[1], going_up=False)
escalator(fl[3], "エスカレーター_3F→4F", ESC_UP[0], ESC_UP[1], going_up=True)
# 6F の天井（屋根スラブ）
box("RF_屋根スラブ", CORE_L, CORE_R, YSE, YNW, FLOOR_H - SLAB, FLOOR_H, M["slab"], fl[6])

# ---------- カメラ（廊下の端から吹き抜けを見る） ----------
cam_data = bpy.data.cameras.new("Cam_教室棟3F廊下")
cam_data.lens = 18
cam_data.clip_start = 0.1
cam = bpy.data.objects.new("Cam_教室棟3F廊下", cam_data)
col.objects.link(cam)
cam.parent = fl[3]
cam.matrix_parent_inverse = Matrix()
cam.location = (CORE_R - 1.0, YCW - 1.4, 1.5)   # 北東端から南西方向を見る（写真「内観02」と同じ向き）
direction = Vector((-1.0, -0.16, 0.06))
cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

# 2台目：吹き抜けと下りエスカレーターのそばから見る
cam2_data = bpy.data.cameras.new("Cam_教室棟3F吹き抜け")
cam2_data.lens = 16
cam2_data.clip_start = 0.1
cam2 = bpy.data.objects.new("Cam_教室棟3F吹き抜け", cam2_data)
col.objects.link(cam2)
cam2.parent = fl[3]
cam2.matrix_parent_inverse = Matrix()
cam2.location = (-1.5, -2.4, 1.5)
cam2.rotation_euler = Vector((-1.0, -0.28, 0.02)).to_track_quat('-Z', 'Y').to_euler()

print("教室棟3F: objects =", len(col.objects))
