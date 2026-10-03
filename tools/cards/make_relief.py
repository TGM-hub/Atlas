import json,numpy as np
from PIL import Image, ImageFilter
Image.MAX_IMAGE_PIXELS=None
s,tx,ty=json.load(open('proj.json'))
rgb=Image.open('bm/shadedrelief.jpg').resize((5400,2700),Image.LANCZOS)
SW,SH=rgb.size
a=np.asarray(rgb,dtype=np.int16)
land=~((a[...,2]>a[...,0]+18)&(a[...,2]>a[...,1]))      # océan/lacs = bleu dominant
src=rgb.convert('L')
L=np.asarray(src,dtype=np.float32)+1
m=land.astype(np.float32)
from scipy.ndimage import gaussian_filter
blur=lambda arr: gaussian_filter(arr.astype(np.float32),10)
def hp(sig):
    g=lambda a: gaussian_filter(a.astype(np.float32),sig)
    return L/np.maximum(g(L*m)/np.maximum(g(m),1e-3),1)
shade=np.where(land,0.5*hp(4)+0.5*hp(16),1.0)          # deux échelles : crêtes fines + grands massifs                                   # ~1 neutral ; <1 ombre ; >1 lumière
K=2   # facteur de résolution
OW,OH=2000*K,1040*K
X,Y=np.meshgrid((np.arange(OW)+.5)/K,(np.arange(OH)+.5)/K)
xn=(X-tx)/s; yn=(ty-Y)/s
p=yn/1.007226
for _ in range(25):
    p2=p*p;p4=p2*p2
    f=p*(1.007226+p2*(0.015085+p4*(-0.044475+0.028874*p2-0.005916*p4)))-yn
    df=1.007226+p2*(3*0.015085+p4*(7*-0.044475+9*0.028874*p2-11*0.005916*p4))
    p=p-f/df
p2=p*p;p4=p2*p2
lam=xn/(0.8707-0.131979*p2+p4*(-0.013791+p4*(0.003971*p2-0.001529*p4)))
valid=(np.abs(lam)<=np.pi)&(np.abs(p)<=np.pi/2)
col=np.clip(((lam+np.pi)/(2*np.pi)*SW).astype(int),0,SW-1)
row=np.clip(((np.pi/2-p)/np.pi*SH).astype(int),0,SH-1)
v=np.where(valid,shade[row,col],1.0)
d=(v-1)*3.2                                            # <0 ombre, >0 lumière
alpha=np.clip(np.abs(d),0,1)**0.85*255
col=np.where(d<0,0,255)
from PIL import ImageDraw
import json,re
Wm=open('/mnt/user-data/uploads/Atlas/map.js').read(); Wm=json.loads(Wm[Wm.index('{'):Wm.rstrip().rstrip(';').rindex('}')+1])
mask=Image.new('L',(OW,OH),0); dr=ImageDraw.Draw(mask)
for c in Wm['countries']:
    for sub in re.findall(r'M[^MZ]+Z?',c['d']):
        pts=[(float(a)*K,float(b)*K) for a,b in re.findall(r'(-?[\d.]+),(-?[\d.]+)',sub)]
        if len(pts)>2: dr.polygon(pts,fill=255)
mask=mask.filter(ImageFilter.MaxFilter(3))
alpha=alpha*(np.asarray(mask)/255.0)
rgba=np.dstack([col,col,col,alpha]).astype(np.uint8)
im=Image.fromarray(rgba,'RGBA')
im.save('relief.webp','WEBP',quality=72,method=6)
import os;print(os.path.getsize('relief.webp')/1e6,'MB', np.percentile(alpha[valid],[50,90,99]))
