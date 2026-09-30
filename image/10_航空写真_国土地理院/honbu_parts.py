import json, numpy as np
exec(open('lean_fit.py',encoding='utf-8').read().split("known=polys")[0])
res=json.load(open('lean_fit_result.json')); vx,vy=res['vx'],res['vy']
out={}
for n,v in roofs.items():
    if not n.startswith('本部棟'): continue
    it=[(t['z'],np.array(t['poly'])) for t in v['tops'] if t['z']>4]
    r=[(score(it,vx,vy,sx,sy),sx,sy) for sx in np.arange(-8,8.1,0.5) for sy in np.arange(-8,8.1,0.5)]
    r.sort(reverse=True); z0=score(it,vx,vy)
    out[n]={'z':it[0][0],'shift':[r[0][1],r[0][2]],'score':round(r[0][0],1),'score0':round(z0,1)}
    print(n[-10:], 'z=%.1f'%it[0][0], 'shift',r[0][1],r[0][2], 'score',round(r[0][0],1),'at0',round(z0,1))
# scale test for whole building about its centroid
hb=polys('本部棟'); c=np.mean(np.vstack([p for _,p in hb]),axis=0)
for s in (0.94,0.97,1.0,1.03,1.06):
    it=[(z,c+(p-c)*s) for z,p in hb]
    best=max((score(it,vx,vy,sx,sy),sx,sy) for sx in np.arange(-4,4.1,0.5) for sy in np.arange(-4,4.1,0.5))
    print('scale',s,'best',[round(float(x),2) for x in best])
json.dump(out,open('honbu_parts_result.json','w'),indent=1)
