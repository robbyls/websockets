import unittest
import zlib

from ..framing import (
    OP_BINARY, OP_CLOSE, OP_CONT, OP_PING, OP_PONG, OP_TEXT, Frame,
    serialize_close
)
from .permessage_deflate import *


class PerMessageDeflateTests(unittest.TestCase):

    def setUp(self):
        # Set up an instance of the permessage-deflate extension with the most
        # common settings. Since the extension is symmetrical, this instance
        # may be used for testing both encoding and decoding.
        self.extension = PerMessageDeflate(False, False, 15, 15)

    def test_name(self):
        assert self.extension.name == 'permessage-deflate'

    # Control frames aren't encoded or decoded.

    def test_no_encode_decode_ping_frame(self):
        frame = Frame(True, OP_PING, b'')

        self.assertEqual(self.extension.encode(frame), frame)

        self.assertEqual(self.extension.decode(frame), frame)

    def test_no_encode_decode_pong_frame(self):
        frame = Frame(True, OP_PONG, b'')

        self.assertEqual(self.extension.encode(frame), frame)

        self.assertEqual(self.extension.decode(frame), frame)

    def test_no_encode_decode_close_frame(self):
        frame = Frame(True, OP_CLOSE, serialize_close(1000, ''))

        self.assertEqual(self.extension.encode(frame), frame)

        self.assertEqual(self.extension.decode(frame), frame)

    # Data frames are encoded and decoded.

    def test_encode_decode_text_frame(self):
        frame = Frame(True, OP_TEXT, 'café'.encode('utf-8'))

        enc_frame = self.extension.encode(frame)

        self.assertEqual(enc_frame, frame._replace(
            rsv1=True,
            data=b'JNL;\xbc\x12\x00',
        ))

        dec_frame = self.extension.decode(enc_frame)

        self.assertEqual(dec_frame, frame)

    def test_encode_decode_binary_frame(self):
        frame = Frame(True, OP_BINARY, b'tea')

        enc_frame = self.extension.encode(frame)

        self.assertEqual(enc_frame, frame._replace(
            rsv1=True,
            data=b'*IM\x04\x00',
        ))

        dec_frame = self.extension.decode(enc_frame)

        self.assertEqual(dec_frame, frame)

    def test_encode_decode_fragmented_text_frame(self):
        frame1 = Frame(False, OP_TEXT, 'café'.encode('utf-8'))
        frame2 = Frame(False, OP_CONT, ' & '.encode('utf-8'))
        frame3 = Frame(True, OP_CONT, 'croissants'.encode('utf-8'))

        enc_frame1 = self.extension.encode(frame1)
        enc_frame2 = self.extension.encode(frame2)
        enc_frame3 = self.extension.encode(frame3)

        self.assertEqual(enc_frame1, frame1._replace(
            rsv1=True,
            data=b'JNL;\xbc\x12\x00\x00\x00\xff\xff',
        ))
        self.assertEqual(enc_frame2, frame2._replace(
            rsv1=True,
            data=b'RPS\x00\x00\x00\x00\xff\xff',
        ))
        self.assertEqual(enc_frame3, frame3._replace(
            rsv1=True,
            data=b'J.\xca\xcf,.N\xcc+)\x06\x00',
        ))

        dec_frame1 = self.extension.decode(enc_frame1)
        dec_frame2 = self.extension.decode(enc_frame2)
        dec_frame3 = self.extension.decode(enc_frame3)

        self.assertEqual(dec_frame1, frame1)
        self.assertEqual(dec_frame2, frame2)
        self.assertEqual(dec_frame3, frame3)

    def test_encode_decode_fragmented_binary_frame(self):
        frame1 = Frame(False, OP_TEXT, b'tea ')
        frame2 = Frame(True, OP_CONT, b'time')

        enc_frame1 = self.extension.encode(frame1)
        enc_frame2 = self.extension.encode(frame2)

        self.assertEqual(enc_frame1, frame1._replace(
            rsv1=True,
            data=b'*IMT\x00\x00\x00\x00\xff\xff',
        ))
        self.assertEqual(enc_frame2, frame2._replace(
            rsv1=True,
            data=b'*\xc9\xccM\x05\x00',
        ))

        dec_frame1 = self.extension.decode(enc_frame1)
        dec_frame2 = self.extension.decode(enc_frame2)

        self.assertEqual(dec_frame1, frame1)
        self.assertEqual(dec_frame2, frame2)

    def test_no_decode_text_frame(self):
        frame = Frame(True, OP_TEXT, 'café'.encode('utf-8'))

        # Try decoding a frame that wasn't encoded.
        self.assertEqual(self.extension.decode(frame), frame)

    def test_no_decode_binary_frame(self):
        frame = Frame(True, OP_TEXT, b'tea')

        # Try decoding a frame that wasn't encoded.
        self.assertEqual(self.extension.decode(frame), frame)

    def test_no_decode_fragmented_text_frame(self):
        frame1 = Frame(False, OP_TEXT, 'café'.encode('utf-8'))
        frame2 = Frame(False, OP_CONT, ' & '.encode('utf-8'))
        frame3 = Frame(True, OP_CONT, 'croissants'.encode('utf-8'))

        dec_frame1 = self.extension.decode(frame1)
        dec_frame2 = self.extension.decode(frame2)
        dec_frame3 = self.extension.decode(frame3)

        self.assertEqual(dec_frame1, frame1)
        self.assertEqual(dec_frame2, frame2)
        self.assertEqual(dec_frame3, frame3)

    def test_no_decode_fragmented_binary_frame(self):
        frame1 = Frame(False, OP_TEXT, b'tea ')
        frame2 = Frame(True, OP_CONT, b'time')

        dec_frame1 = self.extension.decode(frame1)
        dec_frame2 = self.extension.decode(frame2)

        self.assertEqual(dec_frame1, frame1)
        self.assertEqual(dec_frame2, frame2)

    def test_context_takeover(self):
        frame = Frame(True, OP_TEXT, 'café'.encode('utf-8'))

        enc_frame1 = self.extension.encode(frame)
        enc_frame2 = self.extension.encode(frame)

        self.assertEqual(enc_frame1.data, b'JNL;\xbc\x12\x00')
        self.assertEqual(enc_frame2.data, b'J\x06\x11\x00\x00')

    def test_remote_no_context_takeover(self):
        # No context takeover when decoding messages.
        self.extension = PerMessageDeflate(True, False, 15, 15)

        frame = Frame(True, OP_TEXT, 'café'.encode('utf-8'))

        enc_frame1 = self.extension.encode(frame)
        enc_frame2 = self.extension.encode(frame)

        self.assertEqual(enc_frame1.data, b'JNL;\xbc\x12\x00')
        self.assertEqual(enc_frame2.data, b'J\x06\x11\x00\x00')

        dec_frame1 = self.extension.decode(enc_frame1)
        self.assertEqual(dec_frame1, frame)

        with self.assertRaises(zlib.error) as exc:
            self.extension.decode(enc_frame2)
        self.assertIn("invalid distance too far back", str(exc.exception))

    def test_local_no_context_takeover(self):
        # No context takeover when encoding and decoding messages.
        self.extension = PerMessageDeflate(True, True, 15, 15)

        frame = Frame(True, OP_TEXT, 'café'.encode('utf-8'))

        enc_frame1 = self.extension.encode(frame)
        enc_frame2 = self.extension.encode(frame)

        self.assertEqual(enc_frame1.data, b'JNL;\xbc\x12\x00')
        self.assertEqual(enc_frame2.data, b'JNL;\xbc\x12\x00')

        dec_frame1 = self.extension.decode(enc_frame1)
        dec_frame2 = self.extension.decode(enc_frame2)

        self.assertEqual(dec_frame1, frame)
        self.assertEqual(dec_frame2, frame)

    # Continuation frames are encoded and decoded like inital frames.

    # def test_deflate_decode_uncompressed_fragments(self):
    #     deflate = PerMessageDeflate(False, False, 15, 15)
    #     data = "Hello world".encode('utf-8')

    #     frame = Frame(True, OP_TEXT, data)
    #     frag1 = deflate.decode(
    #         frame._replace(fin=False, data=frame.data[:5])
    #     )
    #     frag2 = deflate.decode(
    #         frame._replace(opcode=OP_CONT, data=frame.data[5:])
    #     )
    #     result = frag1.data + frag2.data
    #     self.assertEqual(result, data)

    # def test_deflate_fragment(self):
    #     deflate = PerMessageDeflate(False, False, 15, 15)
    #     data = "I love websockets, especially RFC 7692".encode('utf-8')

    #     frame = deflate.encode(Frame(True, OP_TEXT, data))
    #     frag1 = deflate.decode(
    #         frame._replace(fin=False, data=frame.data[:5])
    #     )
    #     frag2 = deflate.decode(
    #         frame._replace(fin=False, rsv1=False, opcode=OP_CONT,
    #                        data=frame.data[5:10])
    #     )
    #     frag3 = deflate.decode(
    #         frame._replace(rsv1=False, opcode=OP_CONT, data=frame.data[10:])
    #     )
    #     result = frag1.data + frag2.data + frag3.data
    #     self.assertEqual(result, data)

    # # Manually configured items

    # def test_deflate_response_server_no_context_takeover(self):
    #     deflate = PerMessageDeflate(False, False, None, None, server_no_context_takeover=True)
    #     self.assertIn('server_no_context_takeover', deflate.response())

    # def test_deflate_response_client_no_context_takeover(self):
    #     deflate = PerMessageDeflate(False, False, None, None, client_no_context_takeover=True)
    #     self.assertIn('client_no_context_takeover', deflate.response())

    # def test_deflate_response_client_max_window_bits(self):
    #     deflate = PerMessageDeflate(False, False, None, None, client_max_window_bits=10)
    #     self.assertIn('client_max_window_bits=10', deflate.response())

    # def test_deflate_response_server_max_window_bits(self):
    #     deflate = PerMessageDeflate(False, False, None, None, server_max_window_bits=8)
    #     self.assertIn('server_max_window_bits=8', deflate.response())

    # # Taking requested params into account

    # def test_deflate_server_max_window_bits_same(self):
    #     deflate = PerMessageDeflate(False, {
    #         'server_max_window_bits': 10
    #     }, server_max_window_bits=10)
    #     self.assertIn('server_max_window_bits=10', deflate.response())

    # def test_deflate_server_max_window_bits_higher(self):
    #     deflate = PerMessageDeflate(False, {
    #         'server_max_window_bits': 12
    #     }, server_max_window_bits=10)
    #     self.assertIn('server_max_window_bits=10', deflate.response())

    # def test_deflate_server_max_window_bits_lower(self):
    #     deflate = PerMessageDeflate(False, {
    #         'server_max_window_bits': 8
    #     }, server_max_window_bits=10)
    #     self.assertIn('server_max_window_bits=8', deflate.response())

    # def test_deflate_client_max_window_bits_same(self):
    #     deflate = PerMessageDeflate(False, {
    #         'client_max_window_bits': 10
    #     }, client_max_window_bits=10)
    #     self.assertIn('client_max_window_bits=10', deflate.response())

    # def test_deflate_client_max_window_bits_higher(self):
    #     deflate = PerMessageDeflate(False, {
    #         'client_max_window_bits': 12
    #     }, client_max_window_bits=10)
    #     self.assertIn('client_max_window_bits=10', deflate.response())

    # def test_deflate_client_max_window_bits_lower(self):
    #     deflate = PerMessageDeflate(False, {
    #         'client_max_window_bits': 8
    #     }, client_max_window_bits=10)
    #     self.assertIn('client_max_window_bits=8', deflate.response())

    # def test_deflate_server_no_context_takeover(self):
    #     deflate = PerMessageDeflate(False, {
    #         'server_no_context_takeover': None
    #     })
    #     self.assertIn('server_no_context_takeover', deflate.response())

    # def test_deflate_server_no_context_takeover_invalid(self):
    #     with self.assertRaises(Exception):
    #         PerMessageDeflate(False, {
    #             'server_no_context_takeover': 42
    #         })

    # def test_deflate_client_no_context_takeover(self):
    #     deflate = PerMessageDeflate(False, {
    #         'client_no_context_takeover': None
    #     })
    #     self.assertIn('client_no_context_takeover', deflate.response())

    # def test_deflate_client_no_context_takeover_invalid(self):
    #     with self.assertRaises(Exception):
    #         PerMessageDeflate(False, {
    #             'client_no_context_takeover': 42
    #         })

    # def test_deflate_invalid_parameter(self):
    #     with self.assertRaises(Exception):
    #         PerMessageDeflate(False, {
    #             'websockets_are_great': 42
    #         })
