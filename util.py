import math
def mapval(value,istart,istop,ostart,ostop):
    return ostart + (ostop - ostart) * ((value - istart)*1.0 / (istop - istart))

def midpt(*args):
    xs,ys = 0,0
    for p in args:
        xs += p[0]
        ys += p[1]
    return xs/len(args),ys/len(args)

def distsum(*args):
    return sum([ ((args[i][0]-args[i-1][0])**2 + (args[i][1]-args[i-1][1])**2)**0.5 for i in range(1,len(args))])

def distance(p0,p1):
    return (float(p0[0]-p1[0])**2 + float(p0[1]-p1[1])**2 )**0.5

def lerp(p0,p1,t):
    return (p0[0]*(1-t)+p1[0]*t,p0[1]*(1-t)+p1[1]*t)

def eqline(p0,p1):
    return float(p1[1]-p0[1]),\
           float(p0[0]-p1[0]),\
           float(p1[0]*p0[1]-p1[1]*p0[0])

def vecang(seg0,seg1):
    u = [seg0[1][0]-seg0[0][0],seg0[1][1]-seg0[0][1]]
    v = [seg1[1][0]-seg1[0][0],seg1[1][1]-seg1[0][1]]
    def dot(u,v):
        return u[0]*v[0] + u[1]*v[1]
    angcos = dot(u,v)\
           / (distance(seg0[0],seg0[1])
           * distance(seg1[0],seg1[1]))
    try:
        return math.acos(angcos)
    except:
        return math.pi/2

def intersect(seg0,seg1):
    # { ax + by + c = 0 (1)
    # { dx + ey + f = 0 (2)
    # d(1)-a(2) => adx + bdy + cd - dax - eay - fa = 0
    #           => (bd-ea) y = fa - cd
    a,b,c = eqline(seg0[0],seg0[1])
    d,e,f = eqline(seg1[0],seg1[1])
    if (d*b - a*e) == 0:
        return None
    y = float(f*a-c*d)/(d*b - a*e)
    if a != 0:
        x = (-b*y-c)/float(a)
    else:
        x = (-e*y-f)/float(d)
    od0 = online((x,y),seg0[0],seg0[1])
    od1 = online((x,y),seg1[0],seg1[1])
    return ((x,y),(od0,od1))

def online(p0,p1,p2):
    od = 0
    ep = 1
    d0 = distance(p1,p2)
    d1 = distance(p0,p1)
    d2 = distance(p0,p2)
    if abs(d0 + d1 - d2) < ep:
        od = d1
    elif abs(d0 + d2 - d1) < ep:
        od = d2
    elif abs(d1 + d2 - d0) < ep:
        od = 0
    else:
        print p0,p1,p2,d0,d1,d2

    return od

def pt2seg(p0,seg):
    p1,p2=seg
    a,b,c = eqline(p1,p2)
    x0,y0 = p0
    a2b2 = a**2+b**2
    d = abs(a*x0+b*y0+c)/math.sqrt(a2b2)
    x = (b*(b*x0-a*y0)-a*c)/(a2b2)
    y = (a*(-b*x0+a*y0)-b*c)/(a2b2)

    return ((x,y),d,online((x,y),p1,p2))
