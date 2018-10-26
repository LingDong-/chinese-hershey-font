# -*- coding: utf-8 -*-
import json
import sys

CH0 = 0x4e00 # unicode <CJK Ideograph, First>
CH1 = 0x9fef # unicode <CJK Ideograph, Last>

# Extension A-E
# CH0 = 131072
# CH1 = 183969

if __name__ == "__main__":

    data = json.loads(open(sys.argv[1],"r").read())

    w = 48
    k = 16
    for i in range(CH0,CH1+1):
        idx = "U+"+hex(i)[2:].upper()
        if idx not in data:
            continue

        res = chr(int(round(-(w+k)/2.0))+ord('R')) + chr(int(round((w+k)/2.0))+ord('R'))
        d = data[idx]
        for s in d:
            for p in s:
                x = int(round((p[0]-0.5)*w))
                y = int(round((p[1]-0.5)*w))
                res += chr(x+ord('R')) + chr(y+ord('R'))
            if s!=d[-1]:
                res += " R"

        result = str(i).rjust(5)+str(len(res)/2).rjust(3)+res
        print result
