import math
a=6378137.0; f=1/298.257222101; k0=0.9999; lat0=math.radians(36); lon0=math.radians(139+50/60)
e2=f*(2-f); ep2=e2/(1-e2)
def M(p):
    return a*((1-e2/4-3*e2**2/64-5*e2**3/256)*p-(3*e2/8+3*e2**2/32+45*e2**3/1024)*math.sin(2*p)+(15*e2**2/256+45*e2**3/1024)*math.sin(4*p)-(35*e2**3/3072)*math.sin(6*p))
def to_plane(lat,lon):
    p=math.radians(lat); l=math.radians(lon)
    N=a/math.sqrt(1-e2*math.sin(p)**2); T=math.tan(p)**2; C=ep2*math.cos(p)**2; A=(l-lon0)*math.cos(p)
    x=k0*N*(A+(1-T+C)*A**3/6+(5-18*T+T*T+72*C-58*ep2)*A**5/120)
    y=k0*(M(p)-M(lat0)+N*math.tan(p)*(A*A/2+(5-T+9*C+4*C*C)*A**4/24+(61-58*T+T*T+600*C-330*ep2)*A**6/720))
    return x,y  # easting, northing
