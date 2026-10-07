import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import i2map_hashing as hashing
import integrity_check as check
from run_tests import decide_verdict

class FakeChain:
    def store_baseline_hash(self, record_id, value): self.value = value
    def get_baseline_hash(self, record_id): return self.value

class IntegrationTests(unittest.TestCase):
    def test_canonical_hash_and_names(self):
        a=hashing.build_integrity_map([('x',{'b':2,'a':1})])
        b=hashing.build_integrity_map([('x',{'a':1,'b':2})])
        self.assertEqual(a['root_hash'],b['root_hash'])
        self.assertNotEqual(hashing.build_integrity_map([('a','12'),('b','3')])['root_hash'],hashing.build_integrity_map([('a','1'),('b','23')])['root_hash'])
        self.assertNotEqual(hashing.build_integrity_map([('a',1)])['root_hash'],hashing.build_integrity_map([('b',1)])['root_hash'])

    def test_clean_changed_alert_and_chain_reference(self):
        with tempfile.TemporaryDirectory() as d:
            baseline=Path(d)/'baseline.json'; sample=Path(d)/'params.json'
            chain=FakeChain(); original={'hostname':'pi','cpu_usage':'Standard'}
            sample.write_text(json.dumps(original))
            check.save_baseline(hashing.build_integrity_map([('hostname','pi')]), baseline_file=baseline, client=chain, sample=True)
            with patch.object(check,'raise_alert',return_value=True) as alert:
                result=check.check(baseline_file=baseline,client=chain,params_file=sample)
                self.assertEqual(result[0],'verified'); alert.assert_not_called()
                sample.write_text(json.dumps({'hostname':'changed','cpu_usage':'99%'}))
                result=check.check(baseline_file=baseline,client=chain,params_file=sample)
                self.assertEqual(result[0],'flagged'); self.assertEqual(result[1]['changed'],['hostname']); alert.assert_called_once()
            chain.value='0'*64
            self.assertEqual(check.check(baseline_file=baseline,client=chain,params_file=sample)[0],'unknown')

    def test_corrupt_baseline_and_policy(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'baseline.json'
            check.save_baseline(hashing.build_integrity_map([('hostname','pi')]),baseline_file=p,backend='local')
            self.assertEqual(check.check(excluded=(),baseline_file=p,backend='local')[0],'unknown')
            raw=json.loads(p.read_text()); raw['param_values']['hostname']='changed'; p.write_text(json.dumps(raw))
            with self.assertRaises(ValueError): check.load_baseline(baseline_file=p)

    def test_sensor_rejection(self):
        baseline=hashing.build_integrity_map([('hostname','pi')])
        with patch.object(hashing,'generate_runtime_map',return_value=hashing.build_integrity_map([('hostname','changed')])):
            self.assertFalse(hashing.sensor_data_check({'value':42},baseline)['data_accepted'])

    def test_error_not_detection(self):
        self.assertEqual(decide_verdict(0,''),'ok')
        self.assertEqual(decide_verdict(1,''),'flagged')
        self.assertEqual(decide_verdict(2,''),'unclear')
        self.assertEqual(decide_verdict(99,''),'unclear')

    def test_discord_payload_and_missing_configuration(self):
        from AlertingTest import Aleting
        with patch.dict('os.environ', {'DISCORD_WEBHOOK_URL': 'https://example.invalid/test'}):
            with patch.object(Aleting.requests, 'post') as post:
                post.return_value.status_code = 204
                self.assertTrue(Aleting.send_discord_alert('state changed', severity='high', source='CyberScope'))
                self.assertEqual(post.call_args.kwargs['json']['embeds'][0]['description'], 'state changed')
        with patch.dict('os.environ', {}, clear=True), patch.object(Aleting, 'WEBHOOK_URL', None), patch.object(Aleting.requests, 'post') as post:
            self.assertFalse(Aleting.send_discord_alert('state changed'))
            post.assert_not_called()

    def test_pip_sorted_inventory_and_failure(self):
        import pi_device_params as collector
        import subprocess
        with patch.object(collector.subprocess, 'check_output', return_value='[{"name":"Z_pkg","version":"2"},{"name":"a","version":"1"}]') as command:
            self.assertEqual(collector.get_pip_packages(), ['a==1', 'z-pkg==2'])
            self.assertIsInstance(command.call_args.args[0], list)
        with patch.object(collector.subprocess, 'check_output', side_effect=subprocess.CalledProcessError(1, 'pip')):
            with self.assertRaises(RuntimeError): collector.get_pip_packages()

if __name__=='__main__': unittest.main()
