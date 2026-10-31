"""Source contract checks use synthetic public-source-shaped fixtures only."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('platform_audit', ROOT / 'tools/matisse-csf-platform-audit.py')
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def fixture():
    definitions, steps = [], []
    for index, (kind, setoff, clear, enable, status, mask) in enumerate(audit.EXPECTED_STEPS):
        name = 'MASK_' + str(index)
        expression = ' | '.join('(0x1 << %d)' % bit for bit in range(32) if mask & (1 << bit))
        definitions.append('#define ' + name + ' (' + expression + ')')
        steps.append('BUS_PROT_IGN(%s, %#x, %#x, %#x, %#x, %s),' %
                     (kind, setoff, clear, enable, status, name))
    domains = '\n'.join(definitions) + '\n[MT6983_POWER_DOMAIN_MFG0_DORMANT] = {\n' + \
        '.sram_slp_bits = GENMASK(9, 9),\n},\n\t[MT6983_POWER_DOMAIN_MFG1] = {\n' + \
        '\n'.join(steps) + '\n},\n\t[MT6983_POWER_DOMAIN_NEXT] = {}'
    sources = dict.fromkeys(audit.PINS, '')
    sources['mtk-scpsys-mt6983.c'] = domains
    sources['mtk-pd-chk-mt6983.c'] = '\n'.join(
        '{MT6983_POWER_DOMAIN_%s, XPU_PWR_STA, %#x},' % (name, mask)
        for name, mask in (('MFG0_DORMANT', 2), ('MFG1', 4), ('MFG2', 8)))
    sources['gpufreq_mt6983.h'] = '#define GPUFREQ_PDCv2_ENABLE (1)'
    snapshot = '\n'.join('s->%s=rd(io,%#x);' % pair for pair in audit.PATH_REGISTERS.items())
    return sources, snapshot


class OriginalPlatformTests(unittest.TestCase):
    def test_exact_masks_and_spm_status_do_not_claim_live_reachability(self):
        result = audit.audit(*fixture())
        self.assertEqual(result['observed_rpc_mfg1_status_bits'], '0x0')
        self.assertTrue(all(result['observed_spm_domain_bits'].values()))
        self.assertFalse(result['rpc_enable_and_infra_emi_observed'])
        self.assertFalse(result['hardware_power_or_memory_reachability_verified'])
        self.assertEqual(result['protection_release_table_indices'], list(range(6, -1, -1)))
        self.assertEqual(audit.audit(*fixture(), rpc_status=0x10000)
                         ['observed_rpc_mfg1_status_bits'], '0x10000')

    def test_wrong_masks_order_enable_status_or_domain_rejected(self):
        sources, snapshot = fixture()
        original = sources['mtk-scpsys-mt6983.c']
        for old, new in (('(0x1 << 16)', '(0x1 << 15)'), ('0x103c', '0x1048'),
                         ('0x1044', '0x103c'), ('[MT6983_POWER_DOMAIN_MFG1]', '[ABSENT]')):
            changed = dict(sources)
            changed['mtk-scpsys-mt6983.c'] = original.replace(old, new)
            with self.subTest(old=old), self.assertRaises(ValueError):
                audit.audit(changed, snapshot)
        for key in audit.PATH_REGISTERS:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'snapshot address'):
                audit.audit(sources, snapshot.replace('s->' + key, 's->absent'))

    def test_missing_and_tampered_source_pins_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            with self.assertRaises(OSError):
                audit.pinned_sources(path)
            for name in audit.PINS:
                (path / name).write_text('synthetic fixture')
            with self.assertRaisesRegex(ValueError, 'SHA256'):
                audit.pinned_sources(path)


if __name__ == '__main__':
    unittest.main()
