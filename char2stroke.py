# -*- coding: utf-8 -*-
from PIL import Image, ImageFont, ImageDraw
import math
import random
import json
import time
import sys
from util import *
import argparse

CH0 = 0x4e00 # unicode <CJK Ideograph, First>
CH1 = 0x9fef # unicode <CJK Ideograph, Last>

# PIL image to matrix
def im2mtx(im):
    w,h = im.size
    data = list(im.getdata())
    mtx = {}
    for i in range(0,len(data)):
        mtx[i%w,i//w] = 1 if data[i]>250 else 0
    mtx['size']=(w,h)
    return mtx

# matrix to PIL image
def mtx2im(mtx,n=255):
    w,h = mtx['size']
    im = Image.new("L",(w,h))
    dr = ImageDraw.Draw(im)
    for x in range(w):
        for y in range(h):
            dr.point([(x,y)],fill=mtx[x,y]*n)
    return im

# create a matrix containing raster image of character
def rastBox(l,w=100,h=100,f="Heiti.ttc"):
    def getbound(im):
        px = im.load()
        xmin = im.size[0]
        xmax = 0
        ymin = im.size[1]
        ymax = 0
        for x in range(im.size[0]):
            for y in range(im.size[1]):
                if (px[x,y] > 128):
                    if x < xmin: xmin = x
                    if x > xmax: xmax = x
                    if y < ymin: ymin = y
                    if y > ymax: ymax = y
        return xmin,ymin,xmax,ymax

    font = ImageFont.truetype(f,h)
    im0 = Image.new("L",(int(w*1.5),int(h*1.5)))
    dr0 = ImageDraw.Draw(im0)
    dr0.text((int(w*0.1), int(h*0.1)),l,255,font=font)

    xmin,ymin,xmax,ymax = getbound(im0)
    xmin = min(xmin,int(w*0.25))
    xmax = max(xmax,int(w*0.75))
    ymin = min(ymin,int(h*0.25))
    ymax = max(ymax,int(h*0.75))

    im = Image.new("L",(w,h))
    im.paste(im0,box=(-xmin, -ymin))
    im = im.resize((int(w**2*1.0/(xmax-xmin)),int(h**2*1.0/(ymax-ymin))),resample=Image.BILINEAR)
    im = im.crop((0,0,w,h))
    return im2mtx(im)

# scan matrix containing raster image to estimate the strokes
def scanRast(mtx,strw=10,ngradient=2):
    w,h = mtx['size']
    segs = []

    steptypes = [
        (0,1),(1,0),
        (1,1),(-1,1),
        (1,2),(2,1),(-1,2),(-2,1),
        (1,3),(3,1),(-1,3),(-3,1),
        (1,4),(4,1),(-1,4),(-4,1),
    ][:ngradient*4]

    for step in steptypes:
        ini = []
        if step[0] < 0:
            ini += [(w-1,y) for y in range(h)]
        elif step[0] > 0:
            ini += [(0,y) for y in range(h)]

        if step[1] < 0:
            ini += [(x,h-1) for x in range(w)]
        elif step[1] > 0:
            ini += [(x,0) for x in range(w)]

        for i in range(0,len(ini)):
            x = ini[i][0]
            y = ini[i][1]
            flip = False
            while x < w and y < h and x >= 0 and y >= 0:
                if mtx[x,y] == 1:
                    if flip == False:
                        flip = True
                        segs.append([(x,y)])
                else:
                    if flip == True:
                        flip = False
                        segs[-1].append((x,y))
                x += step[0]
                y += step[1]
            if flip == True:
                segs[-1].append((x,y))

    def near(seg0,seg1):
        return distance(seg0[0],seg1[0]) < strw \
           and distance(seg0[1],seg1[1]) < strw

    def scal(seg,s):
        return [(seg[0][0]*s,seg[0][1]*s),
                (seg[1][0]*s,seg[1][1]*s)]

    def adds(seg0,seg1):
        return [(seg0[0][0]+seg1[0][0],seg0[0][1]+seg1[0][1]),
                (seg0[1][0]+seg1[1][0],seg0[1][1]+seg1[1][1])]

    def angs(seg):
        return math.atan2(seg[0][1]-seg[1][1],seg[0][0]-seg[1][0])

    segs = [s for s in segs if distance(s[0],s[1])>strw*0.5]

    gpsegs = []
    for i in range(len(segs)):
        grouped = False
        d = distance(segs[i][0],segs[i][1])
        for j in range(len(gpsegs)):
            if near(segs[i],gpsegs[j]['mean']):
                l = float(len(gpsegs[j]['list']))
                gpsegs[j]['list'].append(segs[i])
                gpsegs[j]['mean'] = adds(
                    scal(gpsegs[j]['mean'],l/(l+1)),
                    scal(segs[i],1/(l+1)))

                if d > gpsegs[j]['max'][1]:
                    gpsegs[j]['max']= (segs[i],d)

                grouped = True
        if grouped == False:
            gpsegs.append({
                'list':[segs[i]],
                'mean':segs[i],
                'max':(segs[i],d)
                })
    ssegs = []
    for i in range(0,len(gpsegs)):
        s = gpsegs[i]['max'][0]
        ssegs.append(s)

    # PASS 1

    for i in range(0,len(ssegs)):
        for j in range(0,len(ssegs)):
            if i != j and ssegs[j] != None:
                if distance(ssegs[i][0],ssegs[i][1]) < distance(ssegs[j][0],ssegs[j][1]):
                    (lx0,ly0),d0,b0=pt2seg(ssegs[i][0],ssegs[j])
                    (lx1,ly1),d1,b1=pt2seg(ssegs[i][1],ssegs[j])
                    m = 1
                    if d0 < strw*m and d1 < strw*m and (b0<strw*m and b1<strw*m):
                        ssegs[i] = None
                        break
    ssegs = [s for s in ssegs if s != None]

    # PASS 2

    for i in range(0,len(ssegs)):
        for j in range(0,len(ssegs)):
            if i != j and ssegs[j] != None:
                d0 = distance(ssegs[i][0],ssegs[j][0])
                d1 = distance(ssegs[i][1],ssegs[j][1])
                m = 1
                if d0 < strw*m and d1 < strw*m:
                    ssegs[i] = None
                    break
    ssegs = [s for s in ssegs if s != None]
    
    # PASS 3

    for i in range(0,len(ssegs)):
        for j in range(0,len(ssegs)):
            if i != j and ssegs[j] != None:
                
                seg0 = ssegs[i][-2:]
                seg1 = ssegs[j][:2]

                ir=intersect(seg0,seg1)
                if ir != None:
                    (x,y),(od0,od1) = ir
                ang = vecang(seg0,seg1)

                d = distance(ssegs[i][-1],ssegs[j][0])
                if d < strw or (ir != None and od0 == od1 == 0) or ang < math.pi/4:
                    (lx0,ly0),d0,b0=pt2seg(ssegs[i][-1],seg1)
                    (lx1,ly1),d1,b1=pt2seg(ssegs[j][0],seg0)
                    m = 1
                    if d0 < strw*m and d1 < strw*m and (b0<1 and b1<1):                   
                        ssegs[j] = ssegs[i][:-1] \
                                 + [lerp(ssegs[i][-1],ssegs[j][0],0.5)] \
                                 + ssegs[j][1:]
                        ssegs[i] = None

                        break
    
    ssegs = [s for s in ssegs if s != None]

    return ssegs

# visualize cv results
def visualize(mtx,ssegs):
    im = mtx2im(mtx,n=80).convert("RGB");
    dr = ImageDraw.Draw(im)
    for s in ssegs:
        dr.line(s,fill=(255,255,255),width=1)
        dr.ellipse((s[0][0]-2,s[0][1]-2,s[0][0]+2,s[0][1]+2),outline=(255,255,0))
        dr.ellipse((s[-1][0]-2,s[-1][1]-2,s[-1][0]+2,s[-1][1]+2),outline=(255,0,0))
        dr.text((s[0][0],s[0][1]),str(ssegs.index(s)))
    return im

class build_params:
    width = 100
    height = 100
    strw = 10
    ngradient = 2
    output = ""
    first = CH0
    last = CH1

# converts a range of characters to strokes (list of polylines)
# outputs in JSON format
def build(font = "fonts/Heiti.ttc"):
    w,h = build_params.width, build_params.height
    result = ""
    if not len(build_params.output):
        print "{"
    else:
        file = open(build_params.output,"w")
        file.close()
        file = open(build_params.output,"a")
        file.write("{\n")
    def perc(x):
        return float("%.3f" % x)
    for i in range(build_params.first,build_params.last+1):
        ch = unichr(i)
        ssegs = scanRast(rastBox(ch,
            w=w,h=h,f=font),
            strw=build_params.strw,
            ngradient=build_params.ngradient
        )
        for j in range (0,len(ssegs)):
            ssegs[j] = map(
                lambda x : (perc(x[0]/float(w)),perc(x[1]/float(h))),
                ssegs[j]
                )
        ind = "U+"+hex(i)[2:].upper()
        entry = "  \""+ind+"\":"+json.dumps(ssegs)+(
            "," if i != build_params.last else "")
        result += entry
        if not len(build_params.output):
            print entry
        else:
            print ch,
            file.write(entry+"\n")
        sys.stdout.flush()

    if not len(build_params.output):
        print "}"
    else:
        file.write("}")
        file.close()
    return "{"+result+"}"



class test_params:
    width = 100
    height = 100
    strw = 10
    ngradient = 2
    nsample = 8
    corpus = ""

# test algorithm on a random string
# and show result as image
def test(fonts = ["/System/Library/Fonts/STHeiti Light.ttc"]):
    w,h = test_params.width, test_params.height
    corpus = test_params.corpus if len(test_params.corpus) else open(
        "teststrings.txt",'r').readlines()[-1].decode('utf-8')
    IM = Image.new("RGB",(w*test_params.nsample,h*len(fonts)))
    DR = ImageDraw.Draw(IM)
    randidx = random.randrange(0,len(corpus)//test_params.nsample+1)
    for i in range(0,test_params.nsample):
        ch = corpus[(randidx*test_params.nsample+i)%len(corpus)]
        print ch,
        sys.stdout.flush()
        for j in range(0,len(fonts)):
            rbox = rastBox(ch,f=fonts[j],w=w,h=h)
            im = visualize(rbox,scanRast(
                rbox,
                strw=test_params.strw,
                ngradient=test_params.ngradient
            ))
            IM.paste(im,(i*w,j*h))
            if i == 0:
                DR.text((0,j*h),fonts[j],(255,255,255))
    IM.show()
    return IM


if __name__ == "__main__":
    if len(sys.argv) == 1:
        test()
        exit()

    parser = argparse.ArgumentParser(description='Convert Chinese font to strokes.')
    parser.add_argument("mode")

    def autoparse(params):
        arglist = [k for k in dir(params) if not k.startswith("_")]
        for k in arglist:
            parser.add_argument('--'+k,dest=k,
                default=getattr(params,k),action='store',nargs='?',type=str)
        args = parser.parse_args()
        for k in arglist:
            typ = type(getattr(params,k))
            setattr(params, k, typ(getattr(args, k)))
        return args

    if sys.argv[1] == "build":
        parser.add_argument("input")
        args = autoparse(build_params)
        build(args.input)

    elif sys.argv[1] == "test":
        parser.add_argument('fonts', metavar='input', type=str, nargs='+', action='store')
        args = autoparse(test_params)
        test(args.fonts)



