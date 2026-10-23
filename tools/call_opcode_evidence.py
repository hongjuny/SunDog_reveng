"""Native call/return checks on explicitly constructed p-machine frames, not a boot."""

def extend_calls(snapshot,records,check,describe):
    def fixture(proc=1,level=0,params=0,locals_size=0,native=False,segment=0x6700):
        trailer=0x6600;attr=trailer-8;entry=0x4800
        words=[(0x54,0x6200),(0x56,0x6700),(0x5c,0x6800),(0x5a,0x5000),
               (0x7000,0x5900),(0x6002,0x5800),(0x6004,0x6300),(0x6200,0x0001),(0x6300,0x0101),
               (segment-2*proc,(segment-2*proc-trailer)&65535),
               (trailer,(level<<8)|(0 if native else proc)),(attr,locals_size),
               (attr+2,params),(attr+6,(attr+6-entry)&65535)]
        return words,0x6800-locals_size-params-12,entry,trailer

    for op,rule in ((0xce,'call_current_dynamic_link'),(0xcf,'call_current_global_link'),
                    (0xc2,'call_current_new_global'),(0xae,'call_current_lexical_link'),(0xcd,'call_external_segment')):
        for proc in (1,2,7):
            for params in (0,2,4):
                level=(1 if proc==1 else 2) if op==0xae else (255 if proc==2 else 1 if proc==7 else 0) if op==0xcd else 0
                words,frame,entry,trailer=fixture(proc,level,params,16)
                if op==0xcd:
                    slot=3;words +=[(0xbd1e+2*slot,1),(0xbd9e+2*slot,0x6700)]
                    stream=bytes([op,slot,proc])
                else:stream=bytes([op,proc])
                arguments=tuple(0xa000+n for n in range(params//2))
                new_global=op==0xc2 or (op==0xcd and not 0<level<128)
                c=check(op,rule,stream,arguments,delta=params//2-int(new_global),
                        advance=None,words=words,max_steps=3000)
                if c.word(0x58)!=entry or c.word(0x52)!=frame or c.word(0x5c)!=frame-2:
                    raise AssertionError('call entry/frame/allocation differs')
                if c.word(frame-2)!=0x6800 or c.word(frame+2)!=0x6000 or c.word(frame+8)!=0x40ff+len(stream):
                    raise AssertionError('saved caller context differs')
                if c.word(frame+4)!=0x6200 or c.word(frame+6)!=0x6700 or c.word(0x54)!=trailer:
                    raise AssertionError('saved procedure/segment context differs')
                expected_link=0x6000 if op==0xce else (0x6000 if level==1 else 0x5800) if op==0xae else 0x5900 if new_global else 0x6000 if op==0xcd else 0x7000
                if c.word(frame)!=expected_link:raise AssertionError(f'{op:02x} static link {c.word(frame):04x} != {expected_link:04x}')
                expected_global=frame if new_global else 0x7000
                if c.word(0x50)!=expected_global:raise AssertionError('global frame differs')
                data=[c.word(frame+12+2*n) for n in range(params//2)]
                if data!=list(arguments[::-1]):raise AssertionError('parameter order differs')
                if op==0xcd and c.word(0xbd1e+6)!=2:raise AssertionError('resident segment reference increment differs')
        describe([op],rule,{'call_current_dynamic_link':'call current segment procedure; static link is saved caller local frame',
                           'call_current_global_link':'call current segment procedure; static link is current global frame',
                           'call_current_new_global':'call current segment procedure; push old global and establish new global frame',
                           'call_current_lexical_link':'call current segment procedure; search dynamic chain by lexical level then select its predecessor',
                           'call_external_segment':'acquire nonzero segment slot, resolve procedure and select lexical/global calling path'}[rule],
                 'u8 segment slot, u8 procedure' if op==0xcd else 'u8 procedure',None,'procedure entry',
                 'Parameters/locals determine allocation; native procedures bypass frame allocation. Nonresident segment I/O remains an explicit service boundary.')
    words,_,_,_=fixture(params=256)
    check(0xce,'call_parameter_size_error',b'\xce\x01',delta=0,words=words,stop=0xd20a,memory_result=(0xbdde,104))

    # External nonresident unit: stop before loader effects, preserving actual prefix.
    words,_,_,_=fixture()
    c=check(0xcd,'external_nonresident_boundary',b'\xcd\x03\x01',delta=-1,advance=0,
            words=words,stop=0xe502)
    if c.read(0x90)!=3:raise AssertionError('segment request differs')
    # Native procedure metadata, with an actual data-derived synthetic return.
    for op in (0xae,0xce,0xcf,0xc2,0xcd):
        words,_,entry,_=fixture(native=True)
        words +=[(entry,0x0060)]  # Synthetic native callee consists only of RTS.
        if op==0xcd:words +=[(0xbd9e,0x6700)];stream=b'\xcd\x00\x01'
        else:stream=bytes([op,1])
        c=check(op,'native_procedure_boundary',stream,delta=-1,advance=len(stream),words=words,stop=entry,max_steps=1000)
        if c.pop_word()!=0xe17d:raise AssertionError('native procedure synthetic return differs')
        c.push_word(0xe17d)
        if c.read(0xe18b)!=(0 if op==0xcd else 255):raise AssertionError('native return segment marker differs')
        records[op]['native_call_boundary']='target derived from tag-zero metadata; return E17E; segment-release may run before fetch'
        c.step()  # Execute only the declared synthetic RTS, never game callee code.
        c.run({0xd293,0xe646},max_steps=50)
        expected=0xe646 if op==0xcd else 0xd293
        if c.pc!=expected:raise AssertionError('native return trampoline routing differs')
        records[op].setdefault('extra_native_addresses',[]).extend(a for a in c.visited if a>=0xd000)
        records[op]['synthetic_native_callee']=dict(address='0x4800',instruction='RTS',scope='Declared test fixture only; not shipped callee code')
    for op in (0xad,0xc1):
        for count in (0,1,2,8):
            values=tuple(0xa100+n for n in range(count))
            words=[(0x600a,0xf9),(0x5ffe,0x6800),(0x7000,0x5900),(0x6002,0x5800),(0x6004,0x6200),
                   (0x6006,0x6700),(0x6008,0x4800),(0x56,0x6700),(0x1fa,0x7100)]
            words +=[(0x600c+2*n,value) for n,value in enumerate(values)]
            c=check(op,'return_restore_context',bytes([op,count]),delta=None,words=words,max_steps=3000)
            expected_sp=(0xf9+(2 if op==0xc1 else 0)-2*count)&255
            if c.sp!=expected_sp:raise AssertionError('return native stack differs')
            if [c.pop_word() for _ in range(count)]!=list(values):raise AssertionError('return value order differs')
            if (c.word(0x52),c.word(0x54),c.word(0x56),c.word(0x58),c.word(0x5c))!=(0x5800,0x6200,0x6700,0x4800,0x6800):
                raise AssertionError('return context restoration differs')
            if c.word(0x50)!=(0x7100 if op==0xc1 else 0x7000):raise AssertionError('return global restoration differs')
        describe([op],'return_restore_context','restore native SP from frame+10, '+('pop old global, ' if op==0xc1 else '')+
                 'push result words, restore allocation/local/branch/segment/PC context',
                 'u8 result word count',None,'saved caller PC','Results start frame+12, copied so the first result is on top. Different first-byte segment identifiers invoke E646 before final restoration; high-count Y wrapping is raw native behavior, not a validated language range.')
        words=[(0x600a,0xf9),(0x5ffe,0x6800),(0x6006,0x6700),(0x56,0x6800),
               (0x6700,1),(0x6800,2),(0x1fa,0x7100)]
        c=check(op,'return_segment_boundary',bytes([op,0]),delta=None,words=words,stop=0xe646)
        if c.word(0x7e)!=0x6700 or c.word(0x5c)!=0x6800:raise AssertionError('segment return preparation differs')
