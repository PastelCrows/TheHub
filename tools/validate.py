import zipfile,tomllib,os,re,io,json,sys
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
import sys as _s
# was hardcoded to Skyblock, which silently validated the WRONG pack when run from
# another project folder. Takes the mods folder as argv[1] now.
MODS = _s.argv[1] if len(_s.argv) > 1 else r"C:\Users\Fejcr\AppData\Roaming\PrismLauncher\instances\Skyblock\minecraft\mods"
def vtok(v):
    v=re.sub(r'^[vV]','',str(v))
    parts=re.split(r'[.\-+_]',v)
    t=[]
    for p in parts:
        m=re.match(r'^(\d+)$',p)
        if m: t.append((0,int(m.group(1))))
        elif p: t.append((1,p.lower()))
    return t
def cmp(a,b):
    A,B=vtok(a),vtok(b)
    for i in range(max(len(A),len(B))):
        x=A[i] if i<len(A) else (0,0); y=B[i] if i<len(B) else (0,0)
        if x==y: continue
        if x[0]!=y[0]: return -1 if x[0]<y[0] else 1
        return -1 if x[1]<y[1] else 1
    return 0
def in_range(ver,rng):
    rng=(rng or "").strip().replace(" ","")
    if not rng or rng=="*": return True
    if rng[0] not in "[(":
        return cmp(ver,rng)>=0
    for part in re.findall(r'[\[\(][^\]\)]*[\]\)]',rng):
        lo_inc=part[0]=='['; hi_inc=part[-1]==']'; body=part[1:-1]
        if ',' not in body:
            if cmp(ver,body)==0: return True
            continue
        lo,hi=body.split(',',1); ok=True
        if lo.strip():
            c=cmp(ver,lo.strip()); ok&= (c>0 or (c==0 and lo_inc))
        if hi.strip():
            c=cmp(ver,hi.strip()); ok&= (c<0 or (c==0 and hi_inc))
        if ok: return True
    return False

provides={"minecraft":"1.21.1","neoforge":"21.1.265","java":"21","forge":"0","fml":"4.0"}
reqs=[]; jarinfo={}
def scan(data,label,top,depth=0):
    try: z=zipfile.ZipFile(io.BytesIO(data))
    except Exception as e: print(f"  BADJAR {label}: {e}"); return
    names=z.namelist()
    t=next((x for x in ("META-INF/neoforge.mods.toml","META-INF/mods.toml") if x in names),None)
    jarver=None
    if "META-INF/MANIFEST.MF" in names:
        m=re.search(r'Implementation-Version:\s*(\S+)',z.read("META-INF/MANIFEST.MF").decode("utf-8","replace"))
        if m: jarver=m.group(1)
    if t:
        try: d=tomllib.loads(z.read(t).decode("utf-8","replace"))
        except Exception as e: d=None
        if d:
            for mo in d.get("mods",[]):
                mid=mo.get("modId"); v=str(mo.get("version","0"))
                if "${" in v: v=jarver or "0"
                if mid and (mid not in provides or depth==0): provides[mid]=v
                if mid: jarinfo.setdefault(mid,(v,top,depth))
            for owner,dl in d.get("dependencies",{}).items():
                for dep in (dl if isinstance(dl,list) else [dl]):
                    mand = (dep.get("type","required")=="required") if "type" in dep else dep.get("mandatory",True)
                    if mand and dep.get("modId"):
                        reqs.append((top,owner,dep["modId"],dep.get("versionRange","")))
    # recurse JarJar
    for n in names:
        if n.startswith("META-INF/jarjar/") and n.endswith(".jar"):
            scan(z.read(n),n,top,depth+1)

files=sorted(f for f in os.listdir(MODS) if f.endswith(".jar"))
for fn in files:
    scan(open(os.path.join(MODS,fn),'rb').read(),fn,fn,0)
print(f"scanned {len(files)} top-level jars -> {len(provides)} modIds available (incl. JarJar)\n")
missing=[];badver=[]
for top,owner,dep,rng in reqs:
    if dep in ("forge",): continue
    if dep not in provides: missing.append((top,dep,rng))
    elif not in_range(provides[dep],rng): badver.append((top,dep,rng,provides[dep]))
print(f"--- MISSING REQUIRED DEPS ({len(missing)}) ---")
for t,d,r in sorted(set(missing)): print(f"  {t[:50]:50s} needs {d:24s} {r}")
print(f"\n--- VERSION RANGE MISMATCH ({len(badver)}) ---")
for t,d,r,h in sorted(set(badver)): print(f"  {t[:46]:46s} needs {d:20s} {r:22s} have={h}")
json.dump({"provides":provides},open("provides2.json","w"),indent=1)
