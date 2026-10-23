#!/usr/bin/env python3
"""Compare native Swift map selection with bounded original P21/P40 fragments."""
import hashlib,itertools,json,platform,random,subprocess
from pathlib import Path
from event_contract import load_inputs
from native_probe import CPU
ROOT=Path(__file__).resolve().parents[1]
SHA=lambda b:hashlib.sha256(b).hexdigest()
def s16(v):return ((v+32768)&65535)-32768
def div16(a,b):return s16((abs(a)//abs(b))*(-1 if (a<0)!=(b<0) else 1))
def selected(origin_x,origin_y,cursor_x,cursor_y,divisor):
    if divisor==0:raise ZeroDivisionError
    col=abs(s16(origin_x+div16(s16(cursor_x+3),28)))%40
    row=abs(s16(origin_y+div16(s16(cursor_y-3),divisor)))%24
    return col,row

def probe(snapshot,archive,values,data,fragment):
    ox,oy,cx,cy,d=values;c=CPU();c.memory[0xd000:]=snapshot;c.memory[0x4800:0x4800+len(archive)]=archive
    def word(p,v):c.memory[p:p+2]=(v&65535).to_bytes(2,'little')
    word(0x52,0x7200);word(0x7200,0x7000)
    for index,value in [(2,0x7502),(5,0x750a),(6,0x750c),(21,d),(25,cy),(26,cx),(55,0x8000)]:word(0x700a+index*2,value)
    word(0x750a,oy);word(0x750c,ox);c.memory[0x8000:0x83c0]=data
    start,end=fragment;word(0x58,0x4800+start)
    visits=set()
    for _ in range(100):
        pc=c.word(0x58)
        if pc==0x4800+end:
            if c.sp!=255 or bytes(c.memory[0x8000:0x83c0])!=data:raise AssertionError('Fragment stack/map effects changed')
            return dict(value=c.word(0x7502),column=c.word(0x720e),row=c.word(0x720c),visited=visits)
        if not 0x4800+start<=pc<0x4800+end:raise ValueError('Selection fragment escaped bounds')
        c.pc=0xd293;c.run({0xd293,0xd20a},max_steps=5000);visits.update(c.visited)
        if c.pc==0xd20a:return dict(error=c.word(0xbdde),visited=visits)
    raise ValueError('Selection fragment budget exceeded')

def main():
    output=ROOT/'analysis/local/native-selection';output.mkdir(parents=True,exist_ok=True)
    source,archive,procedures=load_inputs()[21]
    snapshot=(ROOT/'analysis/regions/interpreter-ready.bin').read_bytes()
    if SHA(snapshot)!='fbb9094b9dd0e11eadcc91351cc2ebdb9c65739762072b2cf14e291b99907f7b':raise ValueError('Interpreter source changed')
    defined={int(line[:4],16) for line in (ROOT/'ghidra/exports/interpreter-ready.txt').read_text().splitlines() if len(line)>6 and line[4:6]=='  ' and all(c in '0123456789abcdef' for c in line[:4])}
    data=bytes((i*37+i//40*11+7)&255 for i in range(960))
    values=list(itertools.product((0,39,-1),(0,23,-1),(0,27,279),(0,191),(1,8,-1)))
    rng=random.Random(0x215e1ec7)
    values += [tuple(rng.randint(-32768,32767) for _ in range(4))+(rng.choice((-32768,-32767,-28,-8,-1,1,8,28,32767)),) for _ in range(128)]
    values += [(32767,-32768,32767,-32768,-1),(-32768,32767,-32768,-32765,-1),(0,0,-4,-4,8)]
    fixtures=[];visits=set()
    for v in values:
        col,row=selected(*v);expected=data[row*40+col]
        a=probe(snapshot,archive,v,data,(0xaea,0xb18));b=probe(snapshot,archive,v,data,(0x1b9c,0x1bce))
        if a.get('error') or b.get('error') or (a['column'],a['row'],a['value'])!=(col,row,expected) or b['value']!=expected%16:raise AssertionError('Original native selection differs')
        visits.update(a['visited']);visits.update(b['visited'])
        fixtures.append(dict(zip(('originX','originY','cursorX','cursorY','verticalDivisor'),v),column=col,row=row,value=expected))
    errors=[]
    for fragment in ((0xaea,0xb18),(0x1b9c,0x1bce)):
        a=probe(snapshot,archive,(0,0,0,0,0),data,fragment)
        if a.get('error')!=106:raise AssertionError('Zero divisor did not enter original error106')
        visits.update(a['visited']);errors.append(dict(start=fragment[0],error=106))
    if not visits<=defined:raise AssertionError('Native selection left Ghidra instruction boundaries')
    case_path=output/'cases.json';case_path.write_text(json.dumps(dict(map=list(data),cases=fixtures),separators=(',',':'))+'\n')
    compiler=subprocess.check_output(['xcrun','--find','swiftc'],text=True).strip();sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
    sources=[ROOT/'native/SunDogLogic/TileSelection.swift',ROOT/'tests/native/VerifyTileSelection.swift'];binary=output/'verify-tile-selection'
    subprocess.run([compiler,'-swift-version','6','-O','-parse-as-library','-sdk',sdk,'-target',platform.machine()+'-apple-macosx14.0','-module-cache-path',str(output/'module-cache'),*map(str,sources),'-o',str(binary)],check=True)
    report=json.loads(subprocess.check_output([str(binary),str(case_path)],text=True))
    report.update(method='Compiled native Swift rule versus original p-code fragments through bounded original native handlers; synthetic frame and byte map',
                  original_archive_sha256=source['sha256'],snapshot_sha256=SHA(snapshot),source_files={str(p.relative_to(ROOT)):SHA(p.read_bytes()) for p in sources},
                  cases_sha256=SHA(case_path.read_bytes()),fragments=[dict(procedure=n,start=a,end_exclusive=b,sha256=SHA(archive[a:b])) for n,a,b in ((21,0xaea,0xb18),(40,0x1b9c,0x1bce))],
                  zero_divisor_cases=errors,native_instruction_count=len(visits),ghidra_boundaries_match=True,
                  contract='Signed16 wrapping addition/subtraction and division truncated toward zero; remainder of magnitudes; exact960-byte map',
                  limitations=['No scene initialization, assets, physical input mapping, window clipping or whole event loop is implemented.',
                               'P40 later conditions and exceptional override255 are outside this lookup helper.'])
    (ROOT/'analysis/native-selection-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
if __name__=='__main__':main()
