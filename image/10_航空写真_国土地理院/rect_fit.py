# 倒れ込みを補正した Esri 写真の輪郭に長方形を当てはめて、本部棟の屋根の位置と寸法を測る
import json, numpy as np, math
exec(open('lean_fit_honbu.py', encoding='utf-8').read().split("known=polys")[0])
v = json.load(open('lean_fit_result.json')); vx, vy = v['vx'], v['vy']
roofs = json.load(open('blender_roofs.json', encoding='utf-8'))


def ang_of(poly):
    p = np.array(poly); best = None
    for i in range(len(p)):
        d = p[(i + 1) % len(p)] - p[i]; L = np.hypot(*d)
        if best is None or L > best[0]:
            best = (L, math.atan2(d[1], d[0]))
    return best[1]


th = ang_of(roofs['本部棟_OSM_1326184670']['tops'][0]['poly'])
u = np.array([math.cos(th), math.sin(th)]); w = np.array([-u[1], u[0]])


def rect(cx, cy, a, b):
    c = np.array([cx, cy])
    return np.array([c - u * a / 2 - w * b / 2, c + u * a / 2 - w * b / 2, c + u * a / 2 + w * b / 2, c - u * a / 2 + w * b / 2])


def fit(h, p0, a0, b0, span=6, sspan=8):
    best = None
    for dcx in np.arange(-span, span + .1, 2):
        for dcy in np.arange(-span, span + .1, 2):
            for da in np.arange(-sspan, sspan + .1, 4):
                for db in np.arange(-sspan, sspan + .1, 4):
                    s = score([(h, rect(p0[0] + dcx, p0[1] + dcy, a0 + da, b0 + db))], vx, vy)
                    if best is None or s > best[0]:
                        best = (s, p0[0] + dcx, p0[1] + dcy, a0 + da, b0 + db)
    for st, rg in ((1.0, 2.0), (0.5, 0.5)):
        s, cx, cy, a, b = best
        for dcx in np.arange(-rg, rg + .01, st):
            for dcy in np.arange(-rg, rg + .01, st):
                for da in np.arange(-rg, rg + .01, st):
                    for db in np.arange(-rg, rg + .01, st):
                        s2 = score([(h, rect(cx + dcx, cy + dcy, a + da, b + db))], vx, vy)
                        if s2 > best[0]:
                            best = (s2, cx + dcx, cy + dcy, a + da, b + db)
    return best


def osm_rect(names):
    pts = np.vstack([np.array(roofs['本部棟_OSM_' + n]['tops'][0]['poly']) for n in names])
    pu = pts @ u; pw = pts @ w
    c = u * (pu.max() + pu.min()) / 2 + w * (pw.max() + pw.min()) / 2
    return c, pu.max() - pu.min(), pw.max() - pw.min()


print('本部棟の軸の角度', round(math.degrees(th), 1))
res = {'theta': th}
c, a, b = osm_rect(['1326184670', '1326275835', '1326275836'])
print('高層部 Blender(OSM): 中心(%.1f,%.1f) 長さ%.1f 幅%.1f' % (c[0], c[1], a, b))
s, cx, cy, A, B = fit(67.5, c, a, b)
print('高層部 写真から:     中心(%.1f,%.1f) 長さ%.1f 幅%.1f score%.0f' % (cx, cy, A, B, s))
res['tower'] = {'osm': [float(c[0]), float(c[1]), float(a), float(b)], 'photo': [float(cx), float(cy), float(A), float(B), float(s)]}
c, a, b = osm_rect(['1326275838', '1326275839'])
print('南西低層部 Blender(OSM): 中心(%.1f,%.1f) 長さ%.1f 幅%.1f' % (c[0], c[1], a, b))
res['sw_osm'] = [float(c[0]), float(c[1]), float(a), float(b)]
for h in (30.0, 35.0, 40.8, 45.0):
    s, cx, cy, A, B = fit(h, c, a, b, span=8, sspan=8)
    print('  h=%.1f 写真から: 中心(%.1f,%.1f) 長さ%.1f 幅%.1f score%.0f' % (h, cx, cy, A, B, s))
    res[f'sw_{h}'] = [float(cx), float(cy), float(A), float(B), float(s)]
json.dump(res, open('rect_fit_result.json', 'w'), indent=1)
