#!/usr/bin/env python3
"""Validate selected p-code semantics by replaying actual bounded 6502 handlers.
Produces a snapshot-specific catalogue, not a p-code disassembler or boot trace.
"""
import hashlib,json,pathlib
from native_probe import handler_probe
ROOT=pathlib.Path(__file__).resolve().parents[1]

def index_operand(value,wide=False):
    if not 0<=value<=32767:raise ValueError('index must fit 15 bits')
    if value<128 and not wide:return bytes([value])
    return bytes([0x80|(value>>8),value&255])

def investigate(snapshot,dispatch):
    records={x['opcode']:dict(opcode=x['opcode'],handler=x['handler'],source=x['handler_source'],status='unresolved') for x in dispatch['primary']}
    counters={};visited={};low_count=0
    def check(op,rule,stream,stack=(),result=None,delta=0,advance=None,words=(),memory_result=None,stop=0xd293):
        nonlocal low_count
        cpu,initial_sp=handler_probe(snapshot,stream,stack,pc=0x40ff,words=words,stop=stop)
        if cpu.sp!=(initial_sp+delta*2)&255:raise AssertionError(f'{op:02x} unexpected stack change')
        if advance is not None and cpu.word(0x58)!=(0x40ff+advance)&65535:raise AssertionError(f'{op:02x} unexpected next p-code address')
        if result is not None:
            actual=cpu.pop_word()
            if actual!=result:raise AssertionError(f'{op:02x} {rule}: {actual:04x} != {result:04x}')
        if memory_result is not None:
            address,value=memory_result
            if cpu.word(address)!=value:raise AssertionError(f'{op:02x} store differs')
        if op>=128:
            if cpu.read(0xd29e)!=(op*2)&255:raise AssertionError('primary dispatch operand differs')
            visited.setdefault(op,set()).update(cpu.visited)
        else:low_count+=1
        counters[rule]=counters.get(rule,0)+1
        return cpu
    def describe(ops,rule,semantic,operand,stack_words,advance,notes=''):
        for op in ops:
            records[op].update(status='verified_selected_semantics',rule=rule,semantic=semantic,operands=operand,stack_word_delta=stack_words,advance=advance,notes=notes)
    values=(0,1,2,0x7f,0x80,0xff,0x100,0x7fff,0x8000,0x8001,0xff00,0xffff)
    arithmetic={0x80:('absolute16',lambda a:((-a)&65535) if a&0x8000 else a),0x91:('negate16',lambda a:(-a)&65535),0x93:('bitwise_not16',lambda a:a^65535)}
    for op,(rule,oracle) in arithmetic.items():
        for v in values:check(op,rule,bytes([op]),(v,),oracle(v),0,1)
        describe([op],rule,rule+' on one 16-bit stack word','none',0,1,'Binary arithmetic; 8000 absolute/negate wraps to 8000, with no modeled overflow trap.')
    binary={0x82:('add16',lambda a,b:(a+b)&65535),0x95:('subtract16',lambda a,b:(a-b)&65535),0x84:('bitwise_and16',lambda a,b:a&b),0x8d:('bitwise_or16',lambda a,b:a|b)}
    for op,(rule,oracle) in binary.items():
        for a in values:
            for b in values:check(op,rule,bytes([op]),(a,b),oracle(a,b),1,1)
        describe([op],rule,rule+' on the lower word and top word; top is right operand','none',-1,1)
    for op in range(128):check(op,'short_immediate',bytes([op]),result=op,delta=-1,advance=1)
    for op in (0xd2,0xd7):
        check(op,'advance_only',bytes([op]),(0x1234,),0x1234,0,1)
    describe((0xd2,0xd7),'advance_only','advance p-code pointer without changing stack','none',0,1)
    check(0x9f,'zero_word',bytes([0x9f]),result=0,delta=-1,advance=1)
    describe([0x9f],'zero_word','push zero word','none',1,1)
    for v in values:check(0xc7,'literal_word',bytes([0xc7,v&255,v>>8]),result=v,delta=-1,advance=3)
    describe([0xc7],'literal_word','push a literal 16-bit word','little-endian u16',1,3)
    for first,last,base,rule in ((0xd8,0xe7,0x6000,'load_local_short'),(0xe8,0xf7,0x7000,'load_global_short')):
        for op in range(first,last+1):
            offset=12+2*(op-first)
            check(op,rule,bytes([op]),result=0xa000|op,delta=-1,advance=1,words=[(base+offset,0xa000|op)])
        describe(range(first,last+1),rule,f'push word at frame + 12 + 2*(opcode-{first:02X}); base '+('$52/$53' if base==0x6000 else '$50/$51'),'none',1,1,'Handler uses A=2*opcode mod 256 and Carry=1 left by dispatch; aliases are not semantically identical.')
    for op in range(0xf8,0x100):
        address=0x6500+2*(op-0xf8)
        check(op,'load_indirect_short',bytes([op]),(0x6500,),0x5a00|op,0,1,words=[(address,0x5a00|op)])
    describe(range(0xf8,0x100),'load_indirect_short','replace pointer by word at pointer + 2*(opcode-F8)','none',0,1,'F8 enters D4AB with Y=0; F9..FF enter D4A8 and depend on dispatch A/Carry.')
    frame_ops={0xca:('load_local',0x6000,'load'),0xa9:('load_global',0x7000,'load'),0xcc:('store_local',0x6000,'store'),0xab:('store_global',0x7000,'store'),0xc6:('address_local',0x6000,'address'),0xa5:('address_global',0x7000,'address')}
    for op,(rule,base,kind) in frame_ops.items():
        for index,wide in ((0,False),(1,False),(5,False),(127,False),(128,False),(255,False),(256,False),(4095,False),(32767,False),(1,True)):
            operand=index_operand(index,wide);address=(base+10+index*2)&65535;stream=bytes([op])+operand
            if kind=='load':check(op,rule,stream,result=0x5aa5,delta=-1,advance=len(stream),words=[(address,0x5aa5)])
            elif kind=='store':check(op,rule,stream,(0x1234,),delta=1,advance=len(stream),memory_result=(address,0x1234))
            else:check(op,rule,stream,result=address,delta=-1,advance=len(stream))
        describe([op],rule,kind+' word/address at frame + 10 + 2*index; base '+('$52/$53' if base==0x6000 else '$50/$51'),'index: one byte <80, or ((first&7F)<<8)|second',-1 if kind=='store' else 1,'2 or 3','D155 scales the index and advances the pointer an extra byte in the long form. Non-minimal two-byte form is accepted.')
    for op,rule,kind in ((0xb6,'load_nonlocal','load'),(0xb2,'address_nonlocal','address'),(0xb8,'store_nonlocal','store')):
        for depth in (0,1,2):
            for index in (1,127,128):
                base=0x6000+depth*0x200;address=base+10+index*2
                operand=index_operand(index);stream=bytes([op,depth])+operand
                words=[(0x6000,0x6200),(0x6200,0x6400)]
                if kind=='load':check(op,rule,stream,result=0xabcd,delta=-1,advance=len(stream),words=words+[(address,0xabcd)])
                elif kind=='store':check(op,rule,stream,(0xabcd,),delta=1,advance=len(stream),words=words,memory_result=(address,0xabcd))
                else:check(op,rule,stream,result=address,delta=-1,advance=len(stream),words=words)
        describe([op],rule,kind+' after following depth links at frame offset zero, then adding 10+2*index','u8 depth, then index operand',-1 if kind=='store' else 1,'3 or 4','Static links followed by D171; initial base $52/$53.')
    for op,rule,pointer_offset in ((0xa6,'inline_length_pointer',1),(0xd0,'inline_payload_pointer',2)):
        for length in (0,1,127,255):
            stream=bytes([op,length])+bytes((n&255 for n in range(length)))
            check(op,rule,stream,result=0x40ff+pointer_offset,delta=-1,advance=length+2)
        describe([op],rule,'push address of '+('length byte' if pointer_offset==1 else 'payload')+' and skip inline byte payload','u8 length followed by length bytes',1,'length+2','No assumption about text encoding or payload data type.')
    for left in values:
        for right in values:
            check(0x8f,'multiply16',bytes([0x8f]),(left,right),(left*right)&65535,1,1)
    describe([0x8f],'multiply16','replace two words by low 16 bits of their product','none',-1,1,
             'D786 uses the 16-step D75F shift/add helper. Sampled sign and overflow boundaries; no overflow exception on these paths.')
    for value in values:
        check(0x98,'square16',bytes([0x98]),(value,),(value*value)&65535,0,1)
    describe([0x98],'square16','replace top word by low 16 bits of its square','none',0,1,
             'D7CD duplicates the stack word then enters D786; sampled sign and overflow boundaries.')
    for pointer in (0x6500,0x65ff,0xffff):
        for value in values:
            check(0x9a,'store_indirect_word',bytes([0x9a]),(pointer,value),delta=2,advance=1,
                  memory_result=(pointer,value))
    describe([0x9a],'store_indirect_word','pop value then pointer and store the word at that pointer','none',-2,1,
             'Little-endian word store, including address FFFF wrapping high byte to 0000 in the synthetic model.')
    for base in (0x6500,0x65ff,0xffff):
        for index in (0,1,255,256,65535):
            address=(base+index)&65535
            for value in (0,0x7f,0x80,0xff):
                check(0xbe,'load_indexed_byte',bytes([0xbe]),(base,index),value,1,1,
                      words=[(address,0xa500|value)])
            for value in (0,0x80,0x1234,0xff00,0xffff):
                check(0xbf,'store_indexed_byte',bytes([0xbf]),(base,index,value),delta=3,advance=1,
                      words=[(address,0xa5cc)],memory_result=(address,0xa500|(value&255)))
    describe([0xbe],'load_indexed_byte','pop index and base, push zero-extended byte at (base+index)&FFFF','none',-1,1,
             'Byte offsets are unscaled; synthetic boundary addresses include page and 16-bit wrap.')
    describe([0xbf],'store_indexed_byte','pop value, index, base; store low byte at (base+index)&FFFF','none',-3,1,
             'High byte of value discarded; neighboring byte checked unchanged.')
    for op,rule,kind in ((0x9d,'load_table_indexed','load'),(0xd1,'store_table_indexed','store'),(0xa7,'address_table_indexed','address')):
        for selector in (0,1,31,127,128,255):
            for index,wide in ((0,False),(127,False),(128,False),(32767,False),(1,True)):
                table=0xbd9e+2*(selector&127);base=0x6500;address=(base+2*index)&65535
                stream=bytes([op,selector])+index_operand(index,wide)
                words=[(table,base)]
                if kind=='load':check(op,rule,stream,result=0x5aa5,delta=-1,advance=len(stream),words=words+[(address,0x5aa5)])
                elif kind=='store':check(op,rule,stream,(0x1234,),delta=1,advance=len(stream),words=words,memory_result=(address,0x1234))
                else:check(op,rule,stream,result=address,delta=-1,advance=len(stream),words=words)
        describe([op],rule,kind+' at word(BD9E+2*(selector&7F)) + 2*index, modulo 65536',
                 'u8 selector, then encoded index',-1 if kind=='store' else 1,'3 or 4',
                 'Selector ASL wraps to 8 bits, so bit 7 is ignored in this path. Table ownership/allocation bounds not established.')
    # A high-bit branch operand selects a backward self-relative table cell;
    # it is not a signed relative displacement from the p-code PC.
    for op,rule in ((0xb9,'jump_encoded'),(0xa1,'branch_even_word')):
        for operand in (0,1,127,128,129,254,255):
            targets=[(0x6200,0x4300)] if operand<128 else [(base,target) for base in (0x6200,0x40,0xfff0) for target in (0x4300,0x4080,0xfff0)]
            for base,target in targets:
                if operand<128:
                    target=(0x40ff+2+operand)&65535;words=[]
                else:
                    cell=(base+operand-256)&65535
                    words=[(0x54,base),(cell,(cell-target)&65535)]
                if op==0xb9:
                    check(op,rule,bytes([op,operand]),(0x5aa5,),0x5aa5,0,(target-0x40ff)&65535,words=words)
                else:
                    for condition in (0,1,2,3,0x100,0x101,0x8000,0xffff):
                        expected=0x4101 if condition&1 else target
                        check(op,rule,bytes([op,operand]),(condition,),delta=1,
                              advance=(expected-0x40ff)&65535,words=words)
    branch_rule='u8 b: if b<0x80 target=PC+2+b; otherwise cell=word(0x54)+b-256, target=cell-word(cell), all modulo 65536'
    describe([0xb9],'jump_encoded','set p-code pointer to decoded branch target',branch_rule,0,'branch target',
             'Negative-form operands index a self-relative word table through 54/55; not a negative PC displacement.')
    describe([0xa1],'branch_even_word','pop condition; branch when bit 0 is clear, otherwise advance 2',branch_rule,-1,'2 or branch target',
             'Only low-word bit 0 is tested; nonzero even values also branch. Table read is skipped when bit 0 is set.')
    trapped=[op for op,x in records.items() if x['handler']==0xd1ef]
    for op in trapped:
        check(op,'shared_error_111',bytes([op]),delta=0,advance=0,stop=0xd20a,memory_result=(0xbdde,111))
    describe(trapped,'shared_error_111','enter common error path and store 111 at BDDE/BDDF; stop before error procedure call','unestablished',None,'no normal continuation','Only the path through D20A is checked; not a complete exception implementation or proof these slots are universally invalid.')
    for op,x in records.items():
        x['native_instruction_addresses']=[f'0x{a:04x}' for a in sorted(visited.get(op,()))]
    return dict(method='selected binary-mode 6502 replay of actual snapshot bytes with declared synthetic RAM/stack inputs; not Apple II execution, not REA Evidence',snapshot_sha256=hashlib.sha256(snapshot).hexdigest(),low_immediate_family=dict(opcode_first=0,opcode_last=127,semantic='push unsigned opcode as 16-bit word',advance=1,cases=low_count),primary=[records[n] for n in sorted(records)],probe_case_counts=counters,total_probe_cases=sum(counters.values()),verified_high_opcodes=sum(x['status']=='verified_selected_semantics' for x in records.values()),unresolved_high_opcodes=[x['opcode'] for x in records.values() if x['status']=='unresolved'],limitations=['Initial interpreter-ready snapshot only; future table or code modifications are not modeled.','No decimal arithmetic, V flag branches, ROM, devices, cycles, interrupts or complete CPU implementation.','Unsupported native instructions and excessive steps fail explicitly.','Sampled word values and page-boundary cases are checks, not exhaustive mathematical proof.','No p-code file or instruction-stream disassembler is implemented.'])

if __name__=='__main__':
    snapshot=(ROOT/'analysis/regions/interpreter-ready.bin').read_bytes()
    dispatch=json.loads((ROOT/'analysis/runtime-dispatch.json').read_text())
    for record in dispatch['primary']:
        p=record['table_address']-0xd000
        if int.from_bytes(snapshot[p:p+2],'little')!=record['handler']:raise ValueError('dispatch report differs from replay snapshot')
    report=investigate(snapshot,dispatch)
    crosscheck_path=ROOT/'analysis/rea-opcode-crosscheck.json'
    if crosscheck_path.exists():
        crosscheck=json.loads(crosscheck_path.read_text())
        if crosscheck.get('status')!='verified_bounded_native_handlers' or crosscheck.get('snapshot_sha256')!=report['snapshot_sha256']:
            raise ValueError('REA opcode cross-check belongs to a different snapshot')
        for row in report['primary']:
            links=[r for r in crosscheck['views'] if row['opcode'] in r['opcodes']]
            if links:
                row['rea_static_evidence_ids']=[r['evidence_ids']['assembly'] for r in links]
        report['rea_native_static_crosscheck']='analysis/rea-opcode-crosscheck.json'
    (ROOT/'analysis/opcode-evidence.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=report['total_probe_cases'],verified_high=report['verified_high_opcodes'],unresolved_high=len(report['unresolved_high_opcodes']))))
