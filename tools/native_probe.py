#!/usr/bin/env python3
"""Bounded binary-mode 6502 replay for isolated interpreter handlers.
Not an Apple II emulator: no ROM, devices, timing, interrupts or unknown-memory
model. Only opcodes needed by the selected native probes are admitted. Unsupported
instructions fail explicitly. Synthetic RAM/stack inputs are declared by callers.
"""
class UnsupportedInstruction(ValueError):
    pass

class CPU:
    def __init__(self, memory=None):
        self.memory=bytearray(65536) if memory is None else bytearray(memory)
        if len(self.memory)!=65536:raise ValueError('expected 64KB controlled test memory')
        self.a=self.x=self.y=0;self.sp=255;self.pc=0;self.c=self.z=self.n=0
        self.steps=0;self.visited=set();self.writes=[]
    def read(self,p):return self.memory[p&65535]
    def write(self,p,value):
        p&=65535;self.memory[p]=value&255;self.writes.append((p,value&255))
    def word(self,p):return self.read(p)|(self.read(p+1)<<8)
    def zpword(self,p):return self.read(p)|(self.read((p+1)&255)<<8)
    def nz(self,v):
        v&=255;self.z=int(v==0);self.n=(v>>7)&1;return v
    def push(self,v):self.write(0x100+self.sp,v);self.sp=(self.sp-1)&255
    def pop(self):self.sp=(self.sp+1)&255;return self.read(0x100+self.sp)
    def push_word(self,v):self.push(v>>8);self.push(v&255)
    def pop_word(self):return self.pop()|(self.pop()<<8)
    def fetch(self):
        v=self.read(self.pc);self.pc=(self.pc+1)&65535;return v
    def fetch_word(self):return self.fetch()|(self.fetch()<<8)
    def run(self,stop_at,max_steps=500):
        for _ in range(max_steps):
            self.step()
            if self.pc in stop_at:return self.pc
        raise ValueError('native probe instruction budget exceeded')
    def step(self):
        address=self.pc;op=self.fetch();self.steps+=1;self.visited.add(address)
        if op==0xea:return
        if op==0x18:self.c=0;return
        if op==0x38:self.c=1;return
        if op==0x48:self.push(self.a);return
        if op==0x68:self.a=self.nz(self.pop());return
        transfers={0xaa:('x','a'),0xa8:('y','a'),0x8a:('a','x'),0x98:('a','y'),0xba:('x','sp')}
        if op in transfers:
            dest,src=transfers[op];setattr(self,dest,self.nz(getattr(self,src)));return
        if op==0x9a:self.sp=self.x;return
        increments={0xe8:('x',1),0xca:('x',-1),0xc8:('y',1),0x88:('y',-1)}
        if op in increments:
            name,delta=increments[op];setattr(self,name,self.nz(getattr(self,name)+delta));return
        if op in (0x0a,0x4a,0x2a,0x6a):
            value=self.a;carry=self.c
            if op in (0x0a,0x2a):self.c=value>>7;value=(value<<1)|(carry if op==0x2a else 0)
            else:self.c=value&1;value=(value>>1)|((carry<<7) if op==0x6a else 0)
            self.a=self.nz(value);return
        if op in (0xe6,0xc6,0xee,0xce,0x26,0x06,0x46,0x66):
            p=self.fetch_word() if op in (0xee,0xce) else self.fetch();v=self.read(p);carry=self.c
            if op in (0xe6,0xee):v+=1
            elif op in (0xc6,0xce):v-=1
            elif op in (0x26,0x06):self.c=v>>7;v=(v<<1)|(carry if op==0x26 else 0)
            else:self.c=v&1;v=(v>>1)|((carry<<7) if op==0x66 else 0)
            self.write(p,self.nz(v));return
        if op in (0xd0,0xf0,0x10,0x30,0x90,0xb0):
            displacement=self.fetch();take={0xd0:not self.z,0xf0:bool(self.z),0x10:not self.n,0x30:bool(self.n),0x90:not self.c,0xb0:bool(self.c)}[op]
            if take:self.pc=(self.pc+(displacement if displacement<128 else displacement-256))&65535
            return
        if op==0x4c:self.pc=self.fetch_word();return
        if op==0x6c:
            p=self.fetch_word();self.pc=self.read(p)|(self.read((p&0xff00)|((p+1)&255))<<8);return
        if op==0x20:
            dest=self.fetch_word();self.push_word((self.pc-1)&65535);self.pc=dest;return
        if op==0x60:self.pc=(self.pop_word()+1)&65535;return
        loads={0xa9:('a','imm'),0xa5:('a','zp'),0xad:('a','abs'),0xb1:('a','indy'),0xb5:('a','zpx'),0xbd:('a','absx'),0xb9:('a','absy'),0xa2:('x','imm'),0xa6:('x','zp'),0xa0:('y','imm'),0xa4:('y','zp')}
        stores={0x85:('a','zp'),0x8d:('a','abs'),0x91:('a','indy'),0x95:('a','zpx'),0x99:('a','absy'),0x86:('x','zp'),0x84:('y','zp')}
        arithmetic={0x69:('adc','imm'),0x65:('adc','zp'),0xe9:('sbc','imm'),0xe5:('sbc','zp'),0xc9:('cmp','imm'),0xc5:('cmp','zp'),0xe0:('cpx','imm'),0xc0:('cpy','imm'),0x29:('and','imm'),0x25:('and','zp'),0x09:('or','imm'),0x05:('or','zp'),0x49:('xor','imm'),0x45:('xor','zp')}
        arithmetic[0xf1]=('sbc','indy')
        if op in loads:
            reg,mode=loads[op];v=self.fetch() if mode=='imm' else self.read(self.operand_address(mode));setattr(self,reg,self.nz(v));return
        if op in stores:
            reg,mode=stores[op];self.write(self.operand_address(mode),getattr(self,reg));return
        if op in arithmetic:
            kind,mode=arithmetic[op];v=self.fetch() if mode=='imm' else self.read(self.operand_address(mode))
            if kind=='adc':
                result=self.a+v+self.c;self.c=int(result>255);self.a=self.nz(result)
            elif kind=='sbc':
                result=self.a-v-(1-self.c);self.c=int(result>=0);self.a=self.nz(result)
            elif kind in ('cmp','cpx','cpy'):
                reg=self.a if kind=='cmp' else self.x if kind=='cpx' else self.y;self.c=int(reg>=v);self.nz(reg-v)
            elif kind=='and':self.a=self.nz(self.a&v)
            elif kind=='or':self.a=self.nz(self.a|v)
            else:self.a=self.nz(self.a^v)
            return
        raise UnsupportedInstruction(f'unsupported native opcode {op:02x} at {address:04x}')
    def operand_address(self,mode):
        if mode=='zp':return self.fetch()
        if mode=='zpx':return (self.fetch()+self.x)&255
        if mode=='abs':return self.fetch_word()
        if mode=='absx':return (self.fetch_word()+self.x)&65535
        if mode=='absy':return (self.fetch_word()+self.y)&65535
        if mode=='indy':return (self.zpword(self.fetch())+self.y)&65535
        raise ValueError('unsupported addressing mode '+mode)

def handler_probe(snapshot,stream,stack=(),pc=0x4000,local_frame=0x6000,global_frame=0x7000,words=(),stop=0xd293,max_steps=500):
    if len(snapshot)!=0x3000:raise ValueError('expected interpreter-ready 12KB snapshot')
    if not 0<=pc<=65535-len(stream):raise ValueError('stream outside synthetic memory')
    cpu=CPU();cpu.memory[0xd000:]=snapshot;cpu.memory[pc:pc+len(stream)]=stream
    for p,value in ((0x58,pc),(0x52,local_frame),(0x50,global_frame)):
        cpu.memory[p]=value&255;cpu.memory[p+1]=value>>8
    for p,value in words:
        cpu.memory[p]=value&255;cpu.memory[(p+1)&65535]=value>>8
    for value in stack:cpu.push_word(value)
    initial_sp=cpu.sp;cpu.writes.clear();cpu.pc=0xd293;cpu.run({stop},max_steps=max_steps)
    return cpu,initial_sp
