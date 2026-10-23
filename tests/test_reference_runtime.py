import json
from pathlib import Path
import socket
import struct
import sys
import tempfile
import threading
import unittest
import zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from reference_runtime import Control,capture_frame,png_rgba

class ReferenceProtocolTests(unittest.TestCase):
    def exchange(self,reply):
        client,server=socket.socketpair()
        def serve():
            try:
                server.recv(1024)
                for byte in reply:server.sendall(bytes([byte]))
            finally:server.close()
        thread=threading.Thread(target=serve);thread.start()
        return Control(client),thread

    def test_fragmented_binary_and_events(self):
        c,t=self.exchange(b'0 event changed\n1 data memory 4 mode=main\n\x00\x0a\xff\x01\n')
        try:
            r=c.command('get-memory $0000 4 main')
            self.assertEqual(r['data'],b'\0\n\xff\x01');self.assertEqual(len(c.events),1)
        finally:c.connection.close();t.join()

    def test_wrong_request_id_is_rejected(self):
        c,t=self.exchange(b'2 ok wrong\n')
        try:
            with self.assertRaises(ValueError):c.command('hello')
        finally:c.connection.close();t.join()

    def test_partial_payload_is_not_zero_filled(self):
        c,t=self.exchange(b'1 data memory 4\n\x01\x02')
        try:
            with self.assertRaises(EOFError):c.command('read')
        finally:c.connection.close();t.join()

    def test_multiline_command_is_rejected(self):
        a,b=socket.socketpair()
        try:
            with self.assertRaises(ValueError):Control(a).command('hello\nrun')
        finally:a.close();b.close()

    def test_bgra_wire_channels_are_explicit(self):
        class Fixture:
            def command(self,command):
                return dict(metadata='width=1 height=1 stride=4 format=argb8888',data=bytes([30,20,10,255]))
        with tempfile.TemporaryDirectory() as d:
            r=capture_frame(Fixture(),Path(d),'fixture')
            self.assertEqual((Path(d)/'fixture.rgba').read_bytes(),bytes([10,20,30,255]))
            self.assertEqual(r['wire_format'],'argb8888-bgra-little-endian')

    def test_png_payload_and_crc(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixture.png';png_rgba(p,1,1,bytes([10,20,30,255]));raw=p.read_bytes()
            self.assertEqual(raw[:8],b'\x89PNG\r\n\x1a\n')
            offset=8;payload=[]
            while offset<len(raw):
                n=struct.unpack_from('>I',raw,offset)[0];kind=raw[offset+4:offset+8];value=raw[offset+8:offset+8+n]
                self.assertEqual(struct.unpack_from('>I',raw,offset+8+n)[0],zlib.crc32(kind+value)&0xffffffff)
                if kind==b'IDAT':payload.append(value)
                offset+=12+n
            self.assertEqual(zlib.decompress(b''.join(payload)),bytes([0,10,20,30,255]))
