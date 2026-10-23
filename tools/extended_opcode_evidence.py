"""Additional Apple II handlers. All fixtures are synthetic; bytes are original native code."""
def words_for(address,raw):
    return [(address+n,raw[n]|((raw[n+1] if n+1<len(raw) else 0)<<8)) for n in range(0,len(raw),2)]

def extend_data(snapshot,records,check,describe):
    from opcode_evidence import index_operand
    signed=lambda n:n-65536 if n&32768 else n
    values=(0,1,2,7,127,255,256,32767,32768,32769,65529,65535)
    for op,rule in ((0x86,'divide_signed16'),(0x8e,'remainder_magnitude16')):
        for left in values:
            for right in values[1:]:
                a,b=signed(left),signed(right)
                q=abs(a)//abs(b)
                if (a<0)!=(b<0):q=-q
                result=(q if op==0x86 else abs(a)%abs(b))&65535
                check(op,rule,bytes([op]),(left,right),result,1,1,max_steps=2000)
        check(op,rule+'_zero_error',bytes([op]),(7,0),delta=1,advance=0,stop=0xd20a,memory_result=(0xbdde,106))
        describe([op],rule,'pop divisor and dividend; push '+('signed quotient truncated toward zero' if op==0x86 else 'nonnegative remainder of operand magnitudes'),
                 'none',-1,1,'Zero divisor enters error 106; quotient overflow wraps, including 8000 / FFFF.')
    for lo,hi in ((0,0),(0,10),(-10,10),(-32768,32767)):
        for value in (-32768,-11,-10,-1,0,1,10,11,32767):
            valid=lo<=value<=hi
            check(0x88,'check_signed_range',b'\x88',(value&65535,lo&65535,hi&65535),
                  (value&65535) if valid else None,2,1 if valid else 0,
                  stop=0xd293 if valid else 0xd20a,
                  memory_result=None if valid else (0xbdde,101))
    describe([0x88],'check_signed_range','pop signed upper/lower bounds; retain checked value; error 101 outside inclusive range',
             'none',-2,1,'Error path stops before shared exception machinery.')
    for length in (0,1,127,255):
        for index in (0,1,127,255,256,65535):
            valid=1<=index<=length
            check(0x9b,'check_string_index',b'\x9b',(0x6500,index),delta=0,advance=1 if valid else 0,
                  words=[(0x6500,length)],stop=0xd293 if valid else 0xd20a,
                  memory_result=None if valid else (0xbdde,101))
    describe([0x9b],'check_string_index','retain pointer and index; require 1 <= index <= byte(pointer); otherwise error 101',
             'none',0,1,'Full index high byte must be zero; no character is loaded.')
    for capacity in (0,1,3,255):
        for data in (b'',b'A',b'ABC',bytes(range(255))):
            valid=len(data)<=capacity
            raw=bytes([len(data)])+data
            c=check(0xaa,'assign_length_string',bytes([0xaa,capacity]),(0x6800,0x6500),delta=2,
                    advance=2 if valid else 0,words=words_for(0x6500,raw),
                    stop=0xd293 if valid else 0xd20a,max_steps=4000,
                    memory_result=None if valid else (0xbdde,113))
            if valid and c.memory[0x6800:0x6800+len(raw)]!=raw:raise AssertionError('string copy differs')
        for character in (0,65,255):
            valid=capacity>=1
            c=check(0xaa,'assign_character_string',bytes([0xaa,capacity]),(0x6800,character),delta=2,
                    advance=2 if valid else 0,stop=0xd293 if valid else 0xd20a,
                    memory_result=(0x6800,0x100*character+1) if valid else (0xbdde,113))
    describe([0xaa],'assign_length_string','pop source then destination; copy length-prefixed string subject to u8 capacity',
             'u8 capacity',-2,2,'A source word with zero high byte is a single character; excess length enters error 113.')
    for count in (1,2,16,64):
        for pc in (0x40fe,0x40ff):
            aligned=pc+(pc&1)
            raw=bytearray(2+2*count+(pc&1));raw[0]=0xb3;raw[1]=count
            payload=bytes((n*31+7)&255 for n in range(count*2))
            raw[2+(pc&1):]=payload
            c=check(0xb3,'push_inline_words',raw,delta=-count,advance=2+2*count+(pc&1),pc=pc,max_steps=2000)
            expected=[int.from_bytes(payload[n:n+2],'little') for n in range(0,len(payload),2)]
            if [c.pop_word() for _ in range(count)]!=expected[::-1]:raise AssertionError('inline word order differs')
    for count in (0,127,128,255):
        for pc in (0x40fe,0x40ff):
            raw=bytearray((n*37+11)&255 for n in range(515));raw[0]=0xb3;raw[1]=count
            nwords=count or 256;shift=pc&1
            expected=[raw[shift+((2+2*n)&255)]|(raw[shift+((3+2*n)&255)]<<8) for n in range(nwords)]
            c=check(0xb3,'inline_words_u8_edges',raw,delta=-nwords,advance=(((count+1)*2)&255)+shift,pc=pc,max_steps=5000)
            if [c.pop_word() for _ in range(min(nwords,128))]!=expected[-128:][::-1]:raise AssertionError('inline u8 wrapping differs')
    describe([0xb3],'push_inline_words','push words from aligned inline byte window with u8 offsets; zero count runs 256 iterations',
             'u8 count, optional alignment byte when opcode PC is odd, then inline words','u8 loop count, zero=256','((2*(count+1))&FF)+(PC&1)',
             'Y wraps in a 256-byte window and hardware stack wraps. Edge counts 0/127/128/255 are checked as raw behavior, not legal Pascal programs.')
    for count in (0,1,2,16,64):
        payload=bytes((17+n*29)&255 for n in range(count*2))
        if count:
            c=check(0xbc,'load_multiple_words',bytes([0xbc,count]),(0x6500,),delta=1-count,advance=2,
                    words=words_for(0x6500,payload),max_steps=3000)
            expected=[int.from_bytes(payload[n:n+2],'little') for n in range(0,len(payload),2)]
            if [c.pop_word() for _ in range(count)]!=expected:raise AssertionError('multi-load order differs')
        stack=(0x6800,)+tuple(0x1000+n for n in range(count))
        c=check(0xbd,'store_multiple_words',bytes([0xbd,count]),stack,delta=count+1,advance=2,max_steps=3000)
        expected=b''.join(v.to_bytes(2,'little') for v in stack[:0:-1])
        if c.memory[0x6800:0x6800+len(expected)]!=expected:raise AssertionError('multi-store order differs')
    describe([0xbc],'load_multiple_words','replace pointer with count words; highest memory word pushed first',
             'u8 count','count-1',2,'Preflight native stack-space check enters error 104; count zero wraps the decrement loop and is not a zero-length load.')
    check(0xbc,'multi_load_stack_error',bytes([0xbc,127]),(0x6500,),delta=0,advance=0,stop=0xd20a,memory_result=(0xbdde,104))
    for count in (0,128):
        payload=bytes((n*17+29)&255 for n in range(256));nwords=count or 256
        c=check(0xbc,'multi_load_u8_edges',bytes([0xbc,count]),(0x6500,),delta=1-nwords,advance=2,
                words=words_for(0x6500,payload),max_steps=5000)
        expected=[int.from_bytes(payload[n:n+2],'little') for n in range(0,256,2)]
        if [c.pop_word() for _ in range(128)]!=expected:raise AssertionError('multi-load wrap differs')
    describe([0xbd],'store_multiple_words','pop count words into increasing destination addresses, then remove destination pointer',
             'u8 count','-(count+1)',2,'Top word stored first; count zero removes only the pointer.')
    for op,rule in ((0xba,'load_packed_field'),(0xbb,'store_packed_field')):
        for width in (1,2,4,7,8,12,16):
            for shift in (0,1,7,8,9,15):
                if width+shift>16:continue
                mask=(1<<width)-1
                for value in (0,1,0xa55a,0xffff):
                    original=0x96a5
                    if op==0xba:
                        check(op,rule,bytes([op]),(0x6500,width,shift),(original>>shift)&mask,2,1,words=[(0x6500,original)])
                    else:
                        expected=(original&~(mask<<shift))|((value&mask)<<shift)
                        check(op,rule,bytes([op]),(0x6500,width,shift,value),delta=4,advance=1,
                              words=[(0x6500,original)],memory_result=(0x6500,expected&65535))
        describe([op],rule,('load' if op==0xba else 'store')+' masked field from a memory word using stacked width and bit offset',
                 'none',-2 if op==0xba else -4,1,'Masks come from DDD6. Tests cover fields within a 16-bit word; invalid widths/offsets are not checked by a language-level oracle.')
    for count in (1,2,3,7,8):
        for width in (1,2,4,8):
            for index in (0,1,count-1,count,count+1,127,0x8000,0xffff):
                q,r=divmod(abs(signed(index)),count)
                c=check(0xc0,'packed_array_descriptor',bytes([0xc0,count,width]),(0x6500,index),delta=-1,advance=3,max_steps=2000)
                if [c.pop_word() for _ in range(3)]!=[(r*width)*257,width,(0x6500+2*q)&65535]:
                    raise AssertionError('packed descriptor differs')
    describe([0xc0],'packed_array_descriptor','replace base/index by base+2*(abs(signed index) div count), width, and duplicated low byte of magnitude remainder*width',
             'u8 elements-per-word count, u8 bit width',1,3,'Native low-byte product is pushed twice. For ordinary bit positions this leaves a nonzero ignored high byte; count zero errors via division.')
    check(0xc0,'packed_descriptor_zero_error',b'\xc0\x00\x01',(0x6500,3),delta=0,advance=0,stop=0xd20a,memory_result=(0xbdde,106))
    for pc in (0x40fe,0x40ff):
        anchor=pc|1
        lo,hi=-2,2
        raw=bytearray(40);raw[0]=0xac
        p=anchor-pc
        raw[p+1:p+5]=(lo&65535).to_bytes(2,'little')+(hi&65535).to_bytes(2,'little')
        for value in (-3,-2,0,2,3):
            target=0x4600+2*(value-lo)
            cell=(anchor+7+2*(value-lo))&65535
            words=[] if value<lo or value>hi else [(cell,(cell-target)&65535)]
            c=check(0xac,'case_table_branch',raw,(value&65535,),delta=1,pc=pc,
                    advance=((anchor+5 if value<lo or value>hi else target)-pc)&65535,words=words)
    describe([0xac],'case_table_branch','pop signed selector, align PC with OR 1; inclusive bounds select backward self-relative target, else continue at aligned PC+5',
             'alignment-dependent signed lower/upper words; branch cells start aligned PC+7',-1,'table target or aligned PC+5',
             'Target cell is aligned PC+7+2*(value-lower), target=cell-word(cell).')
    for index,wide in ((0,False),(127,False),(128,False),(32767,False),(1,True)):
        stream=bytes([0xd5])+index_operand(index,wide)
        check(0xd5,'consume_ignored_index',stream,(0x1234,),0x1234,0,len(stream))
    describe([0xd5],'consume_ignored_index','decode scaled index into scratch 68/69 and advance without changing stack',
             'encoded index',0,'2 or 3','No native call or value load occurs in this snapshot.')
    c=check(0xd6,'reset_via_generated_stub',b'\xd6',(0x1234,),0x1234,0,0,stop=0)
    if c.memory[:6]!=bytes.fromhex('ad8ac06cfcff'):raise AssertionError('reset stub differs')
    describe([0xd6],'reset_via_generated_stub','write LDA C08A / JMP (FFFC) at 0000 and jump there',
             'none',0,'no normal continuation','Stopped before executing generated MMIO/ROM-vector stub; original Apple II ROM behavior not observed.')
    for selector in range(256):
        c=check(0x9e,'secondary_dispatch',bytes([0x9e,selector]),delta=0,advance=0,stop=0xe687)
        c.step()
        target=int.from_bytes(snapshot[0x100+2*(selector&127):0x102+2*(selector&127)],'little')
        if c.pc!=target:raise AssertionError('secondary dispatch target differs')
    describe([0x9e],'secondary_dispatch','read u8 selector, double modulo 256, patch E688 and jump through D100+2*(selector&7F)',
             'u8 selector','service-dependent','service-dependent','All selectors mapped without executing their targets; only the first 41 cells are directory-shaped. Service semantics are a separate layer.')
    records[0x9e]['extra_native_addresses']=[0xe687]
    extend_typed(records,check,describe)

def extend_typed(records,check,describe):
    from opcode_evidence import index_operand
    relations={0xaf:('equal',lambda a,b:a==b),0xb7:('not_equal',lambda a,b:a!=b),
               0xb5:('less',lambda a,b:a<b),0xb1:('greater',lambda a,b:a>b),
               0xb4:('less_equal',lambda a,b:a<=b),0xb0:('greater_equal',lambda a,b:a>=b)}
    for op,(name,relation) in relations.items():
        rule='typed_compare_'+name
        for left in (0,1,2,3,0x100,0xffff):
            for right in (0,1,2,3,0x100,0xffff):
                check(op,rule,bytes([op,6]),(left,right),int(relation(left&1,right&1)),1,2)
        for left in (0,1,0x3f800000,0x80000000,0xbf800000,0xffffffff):
            for right in (0,1,0x3f800000,0x80000000,0xbf800000,0xffffffff):
                key=lambda v:(0,-(v&0x7fffffff)) if v&0x80000000 else (1,v)
                check(op,rule,bytes([op,2]),(left>>16,left&65535,right>>16,right&65535),int(relation(key(left),key(right))),3,2,max_steps=1500)
        strings=(b'',b'A',b'B',b'AA',b'AB',b'A'*127,b'A'*255)
        for left in strings:
            for right in strings:
                words=words_for(0x6500,bytes([len(left)])+left)+words_for(0x6800,bytes([len(right)])+right)
                check(op,rule,bytes([op,4]),(0x6500,0x6800),int(relation(left,right)),1,2,words=words,max_steps=6000)
        for left in (0,65,255):
            for right in (0,65,255):
                check(op,rule,bytes([op,4]),(left,right),int(relation(bytes([left]),bytes([right]))),1,2)
                raw=bytes([1,right])
                check(op,rule,bytes([op,4]),(left,0x6800),int(relation(bytes([left]),bytes([right]))),1,2,words=words_for(0x6800,raw))
        for kind in (0,1,10):
            for size in (0,1,2,127,128):
                length=size if kind==10 else size*2
                for ordering in (-1,0,1):
                    a=bytearray(b'\x55'*length);b=bytearray(a)
                    if length:
                        a[-1]=0x54 if ordering<0 else 0x56 if ordering>0 else 0x55
                    stream=bytes([op,kind])+index_operand(size)
                    check(op,rule,stream,(0x6500,0x6800),int(relation(bytes(a),bytes(b))),1,len(stream),
                          words=words_for(0x6500,a)+words_for(0x6800,b),max_steps=8000)
        # Set representation: most-significant words first on stack, then word count.
        for left in ((),(0,),(1,),(3,),(1,2)):
            for right in ((),(0,),(1,),(3,),(1,2)):
                a=sum(v<<(16*(len(left)-1-n)) for n,v in enumerate(left));b=sum(v<<(16*(len(right)-1-n)) for n,v in enumerate(right))
                expected=(a==b if name=='equal' else a!=b if name=='not_equal' else (a&~b)==0 if name=='less_equal' else (b&~a)==0)
                stack=tuple(left)+(len(left),)+tuple(right)+(len(right),)
                check(op,rule,bytes([op,8]),stack,int(expected),len(stack)-1,2,max_steps=2000)
        describe([op],rule,'type-dependent '+name+' relation; canonical boolean result',
                 'u8 kind; kind 0A uses encoded byte count, other unrecognized kinds encoded word count',None,'2 or 2+encoded-index-width',
                 'Kind 02 compares four-byte sign-magnitude ordering, 04 strings/chars, 06 low-bit booleans, 08 variable bitmap sets. Set kinds with less/greater masks follow the >= path; legal language combinations unestablished.')
        records[op]['tested_kind_variants']={
            '02':dict(layout='four stack words, high word then low word per operand',relation='four-byte sign-magnitude ordering',advance=2),
            '04':dict(layout='two string pointers or zero-high-byte character words',relation=name,advance=2),
            '06':dict(layout='two words, only bit zero compared',relation=name,advance=2),
            '08':dict(layout='most-significant bitmap words first, followed by count word per operand',
                      relation=name if name in ('equal','not_equal','less_equal','greater_equal') else 'greater_equal fallback',advance=2),
            '0A':dict(layout='two pointers; encoded byte count follows kind',relation='unsigned byte lexicographic '+name,advance='2+index-width'),
            'default':dict(layout='two pointers; encoded word count follows kind',relation='unsigned byte lexicographic '+name,advance='2+index-width')}
