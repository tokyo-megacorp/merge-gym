import base64
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def keypair(directory):
    directory.mkdir()
    private, public = directory / 'private.pem', directory / 'public.pem'
    subprocess.run(['openssl', 'genpkey', '-algorithm', 'RSA', '-pkeyopt', 'rsa_keygen_bits:2048',
                    '-out', str(private)], check=True, capture_output=True)
    subprocess.run(['openssl', 'pkey', '-in', str(private), '-pubout', '-out', str(public)],
                   check=True, capture_output=True)
    return private, public


def sign(private, payload):
    result = subprocess.run(['openssl', 'dgst', '-sha256', '-sign', str(private)],
                            input=payload.encode('utf-8'), check=True, capture_output=True)
    return base64.b64encode(result.stdout).decode('ascii')


def report():
    return {'run_id': 'gym-001', 'status': 'pass', 'duration_seconds': 42,
            'scenarios': [{'id': 'happy-path', 'status': 'pass', 'prs': [7]}]}


class SignedReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.private, cls.public = keypair(cls.root / 'valid')
        cls.other_private, cls.other_public = keypair(cls.root / 'other')

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def invoke(self, inputs):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            telemetry = root / 'trusted/telemetry'
            telemetry.mkdir(parents=True)
            for name in ('render_report.py', 'public_fields.py'):
                shutil.copyfile(ROOT / 'telemetry' / name, telemetry / name)
            verifier = ROOT / 'telemetry/report_signature.py'
            if verifier.exists(): shutil.copyfile(verifier, telemetry / verifier.name)
            shutil.copyfile(self.public, telemetry / 'report-public-key.pem')
            shutil.copyfile(self.other_public, root / 'report-public-key.pem')
            event = root / 'event.json'
            event.write_text(json.dumps({'inputs': inputs}))
            return subprocess.run([sys.executable, str(telemetry / 'render_report.py'), str(event), '--dispatch-event'],
                                  cwd=root, capture_output=True, text=True)

    def signed(self, payload):
        return {'sanitized_json': payload, 'signature': sign(self.private, payload)}

    def assertRejected(self, inputs):
        result = self.invoke(inputs)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')
        self.assertNotIn('Traceback', result.stderr)
        self.assertNotIn(inputs.get('signature', 'never-echo-signature'), result.stderr)

    def test_signed_valid_payload_preserves_existing_report(self):
        result = self.invoke(self.signed(json.dumps(report())))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('External controller result: **pass**', result.stdout)
        self.assertIn('gym-001', result.stdout)

    def test_missing_or_malformed_signature_rejected(self):
        payload = json.dumps(report())
        self.assertRejected({'sanitized_json': payload})
        for signature in ('not base64!', 'eA==', None, 12, []):
            with self.subTest(signature=signature):
                result = self.invoke({'sanitized_json': payload, 'signature': signature})
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, '')

    def test_changed_payload_and_equivalent_reserialization_rejected(self):
        signed = self.signed(json.dumps(report(), separators=(',', ':')))
        for payload in (json.dumps(report()), signed['sanitized_json'].replace('gym-001', 'gym-002')):
            with self.subTest(payload=payload):
                self.assertRejected(signed | {'sanitized_json': payload})

    def test_wrong_key_rejected_despite_working_directory_key(self):
        payload = json.dumps(report())
        self.assertRejected({'sanitized_json': payload, 'signature': sign(self.other_private, payload)})

    def test_event_cannot_override_public_key(self):
        inputs = self.signed(json.dumps(report())) | {'public_key': str(self.other_public)}
        self.assertRejected(inputs)

    def test_signed_payload_still_requires_sanitized_schema(self):
        self.assertRejected(self.signed(json.dumps(report() | {'transcript': 'never-publish-this'})))


if __name__ == '__main__':
    unittest.main()
