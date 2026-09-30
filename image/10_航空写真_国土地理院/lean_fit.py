# Esri 航空写真の「倒れ込み」を、位置が正しい建物から推定し、本部棟の位置ずれを測る
import json, numpy as np
from PIL import Image, ImageFilter, ImageDraw
RES=0.25
X0,X1,Y0,Y1=-260,-30,-130,100          # 解析範囲（ローカル座標）
W=int((X1-X0)/RES); H=int((Y1-Y0)/RES)
# Esri のエッジ画像をローカル格子にリサンプル
meta=json.load(open('esri_z19.json'))['corners_local']
src=Image.open('esri_z19.jpg').convert('L').filter(ImageFilter.GaussianBlur(1.0))
a=np.asarray(src,dtype=float); gy,gx=np.gradient(a); g=np.hypot(gx,gy); sh,sw=g.shape
xs=X0+(np.arange(W)+0.5)*RES; ys=Y1-(np.arange(H)+0.5)*RES
XX,YY=np.meshgrid(xs,ys)
px=np.clip(((XX-meta['tl'][0])/(meta['tr'][0]-meta['tl'][0])*sw).astype(int),0,sw-1)
py=np.clip(((YY-meta['tl'][1])/(meta['bl'][1]-meta['tl'][1])*sh).astype(int),0,sh-1)
E=g[py,px]; E=(E-E.mean())/E.std()
roofs=json.load(open('blender_roofs.json',encoding='utf-8'))
def polys(prefix):
    out=[]
    for n,v in roofs.items():
        if n.startswith(prefix):
            for t in v['tops']:
                if t['z']>4: out.append((t['z'],np.array(t['poly'])))
    return out
def raster(items,vx,vy,sx=0,sy=0):
    im=Image.new('L',(W,H),0); d=ImageDraw.Draw(im)
    for z,p in items:
        q=p+np.array([vx*z+sx,vy*z+sy])
        pts=[((x-X0)/RES,(Y1-y)/RES) for x,y in q]
        d.line(pts+[pts[0]],fill=255,width=3)
    r=np.asarray(im.filter(ImageFilter.GaussianBlur(2)),dtype=float)/255
    return r
def score(items,vx,vy,sx=0,sy=0):
    r=raster(items,vx,vy,sx,sy); m=r>0.02
    return float((E*r).sum()/np.sqrt((r*r).sum()))
known=polys('研究棟')+polys('教室棟')+polys('交流棟')
best=None
for vx in np.arange(-0.40,0.401,0.04):
    for vy in np.arange(-0.40,0.401,0.04):
        s=score(known,vx,vy)
        if best is None or s>best[0]: best=(s,vx,vy)
s0,vx,vy=best
for vx2 in np.arange(vx-0.04,vx+0.041,0.01):
    for vy2 in np.arange(vy-0.04,vy+0.041,0.01):
        s=score(known,vx2,vy2)
        if s>best[0]: best=(s,vx2,vy2)
s0,vx,vy=best
print(f'倒れ込み係数: vx={vx:.3f}, vy={vy:.3f} m/m  (高さ64mで {64*vx:.1f},{64*vy:.1f} m)  score={s0:.2f}  (v=0のscore={score(known,0,0):.2f})')
# 建物ごとに個別に確認
for pre in ('研究棟','教室棟','交流棟'):
    it=polys(pre); r=[]
    for sx in np.arange(-4,4.1,0.5):
        for sy in np.arange(-4,4.1,0.5):
            r.append((score(it,vx,vy,sx,sy),sx,sy))
    r.sort(reverse=True); print(f'  {pre}: 補正後の残りのずれ ({r[0][1]:+.1f},{r[0][2]:+.1f}) m')
# 本部棟の残りのずれ
hb=polys('本部棟'); r=[]
for sx in np.arange(-15,15.1,0.5):
    for sy in np.arange(-15,15.1,0.5):
        r.append((score(hb,vx,vy,sx,sy),sx,sy))
r.sort(reverse=True)
print('本部棟: 補正後の位置ずれ候補', [(round(a,2),b,c) for a,b,c in r[:5]], ' ずれ0の場合', round(score(hb,vx,vy),2))
json.dump({'vx':vx,'vy':vy,'honbu_shift':[r[0][1],r[0][2]],'honbu_top5':[list(map(float,x)) for x in r[:5]]},open('lean_fit_result.json','w'),indent=1)
