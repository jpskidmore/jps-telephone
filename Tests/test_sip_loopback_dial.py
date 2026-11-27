"""Exercise the vendored arm64 SIP stack against answered loopback calls."""
import pathlib
import socket
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class LoopbackDialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scratch = tempfile.TemporaryDirectory()
        cls.addClassCleanup(scratch.cleanup)
        cls.caller = pathlib.Path(scratch.name) / "loopback-caller"
        libraries = [
            str(archive)
            for vendor in ("PJSIP", "LibreSSL", "Opus")
            for archive in sorted((ROOT / "ThirdParty" / vendor / "lib").glob("*.a"))
        ]
        frameworks = [
            "CoreAudio", "AudioToolbox", "CoreFoundation", "AVFoundation",
            "Security", "CFNetwork", "SystemConfiguration", "CoreServices",
        ]
        subprocess.run([
            "xcrun", "clang", "-arch", "arm64", "-DPJ_AUTOCONF=1",
            "-ITelephone", "-IThirdParty/PJSIP/include", "Tests/sip-loopback-dial.c",
            *libraries, *(arg for name in frameworks for arg in ("-framework", name)),
            "-o", str(cls.caller),
        ], cwd=ROOT, check=True)

    def test_ipv4_only_peer(self):
        self.answer_call(socket.AF_INET, "127.0.0.1", "127.0.0.1", b"IP4")

    def test_ipv6_peer(self):
        self.answer_call(socket.AF_INET6, "::1", "[::1]", b"IP6")

    def test_dual_stack_hostname_prefers_ipv6(self):
        self.answer_call(socket.AF_INET6, "::1", "localhost", b"IP6")

    def answer_call(self, family, address, destination, address_type):
        with socket.socket(family, socket.SOCK_DGRAM) as sip, socket.socket(family, socket.SOCK_DGRAM) as rtp:
            sip.bind((address, 0))
            sip.settimeout(8)
            rtp.bind((address, 0))
            port = sip.getsockname()[1]
            uri = f"sip:5550100@{destination}:{port}"
            contact = f"sip:5550100@{'[::1]' if family == socket.AF_INET6 else address}:{port}"
            host = destination.strip("[]")
            with tempfile.TemporaryFile() as output:
                caller = subprocess.Popen([str(self.caller), host, uri], stdout=output, stderr=output)
                try:
                    invite, remote = sip.recvfrom(65535)
                    self.assertEqual(remote[0], address)
                    self.assertTrue(invite.startswith(b"INVITE "))
                    head, offer = invite.split(b"\r\n\r\n", 1)
                    self.assertIn(b"c=IN " + address_type + b" ", offer)
                    self.assertIn(b"\r\nm=audio ", offer)
                    headers = dict(line.split(b": ", 1) for line in head.split(b"\r\n")[1:])
                    family_name = address_type.decode()
                    sdp = (
                        f"v=0\r\no=- 1 1 IN {family_name} {address}\r\ns=Loopback\r\n"
                        f"c=IN {family_name} {address}\r\nt=0 0\r\n"
                        f"m=audio {rtp.getsockname()[1]} RTP/AVP 0\r\na=rtpmap:0 PCMU/8000\r\n"
                    ).encode()
                    response = [
                        b"SIP/2.0 200 OK", b"Via: " + headers[b"Via"], b"From: " + headers[b"From"],
                        b"To: " + headers[b"To"] + b";tag=loopback", b"Call-ID: " + headers[b"Call-ID"],
                        b"CSeq: " + headers[b"CSeq"], f"Contact: <{contact}>".encode(),
                        b"Content-Type: application/sdp", f"Content-Length: {len(sdp)}".encode(),
                    ]
                    sip.sendto(b"\r\n".join(response) + b"\r\n\r\n" + sdp, remote)
                    ack, _ = sip.recvfrom(65535)
                    self.assertTrue(ack.startswith(b"ACK "))
                    self.assertEqual(caller.wait(timeout=8), 0)
                except Exception:
                    output.seek(0)
                    print(output.read().decode(errors="replace"))
                    raise
                finally:
                    if caller.poll() is None:
                        caller.terminate()
                        caller.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
