#!/usr/bin/env python3
"""Conservation/refusal tests for the unsupported-hardware boot experiment."""
import copy
from pathlib import Path
import unittest
import whyred_boot_profile as h


class ProfileTest(unittest.TestCase):
    def baseline(self):
        native = {h.DAEMONS + filename: dict(Label=label, ProgramArguments=['/fixture/' + label],
                  MachServices={label: True}, LaunchEvents={'fixture': {'preserve': [1, 2]}},
                  KeepAlive={'SuccessfulExit': False}) for label, filename, _ in h.HARDWARE_JOBS}
        cache = {'LaunchDaemons': copy.deepcopy(native), 'Other': {'preserved': [1, 2, 3]}}
        # Actual critical API, UI and remote-access jobs must remain equal.
        for label in ['SpringBoard', 'backboardd', 'lsd', 'pkd', 'containermanagerd',
                      'MobileGestaltHelper', 'mediaserverd', 'locationd', 'CommCenter',
                      'logd', 'UserEventAgent', 'org.whyred.display', 'org.whyred.ssh']:
            cache['LaunchDaemons']['/critical/' + label] = {'Label': label, 'Program': '/keep/' + label}
        for n in range(532 - len(cache['LaunchDaemons'])):
            cache['LaunchDaemons']['/other/' + str(n)] = {'Label': 'other.' + str(n)}
        return cache, native

    def test_only_nineteen_disabled_flags(self):
        cache, native = self.baseline()
        before = copy.deepcopy((cache, native))
        updated, files = h.merge(cache, native)
        self.assertEqual((cache, native), before)
        expected_cache, expected_native = copy.deepcopy(before)
        for path in native:
            expected_cache['LaunchDaemons'][path]['Disabled'] = True
            expected_native[path]['Disabled'] = True
        self.assertEqual((updated, files), (expected_cache, expected_native))
        self.assertEqual(len(files), 19)

    def test_explicit_false_and_cache_extra_keys(self):
        cache, native = self.baseline()
        path = next(iter(native))
        cache['LaunchDaemons'][path]['Disabled'] = False
        cache['LaunchDaemons'][path]['CacheSpecific'] = {'keep': True}
        native[path]['Disabled'] = False
        updated, files = h.merge(cache, native)
        self.assertTrue(files[path]['Disabled'])
        self.assertEqual(updated['LaunchDaemons'][path]['CacheSpecific'], {'keep': True})

    def test_refuse_missing_extra_mislabelled_and_reenabled_baselines(self):
        for defect in ['missing', 'extra', 'label', 'program', 'cache-disabled', 'native-disabled', 'count']:
            with self.subTest(defect=defect):
                cache, native = self.baseline()
                path = next(iter(native))
                if defect == 'missing': del native[path]
                if defect == 'extra': native['/unexpected'] = {}
                if defect == 'label': cache['LaunchDaemons'][path]['Label'] = 'wrong'
                if defect == 'program': native[path]['ProgramArguments'] = ['/wrong']
                if defect == 'cache-disabled': cache['LaunchDaemons'][path]['Disabled'] = True
                if defect == 'native-disabled': native[path]['Disabled'] = True
                if defect == 'count': cache['LaunchDaemons'].pop('/other/0')
                before = copy.deepcopy((cache, native))
                with self.assertRaises(ValueError): h.merge(cache, native)
                self.assertEqual((cache, native), before)

    def test_independent_comparator_has_exact_same_paths(self):
        source = Path(__file__).with_name('whyred-display-image-compare.c').read_text()
        section = source.split('static const char *hardware_paths[] = {', 1)[1].split('};', 1)[0]
        import re
        paths = re.findall(r'"([^"]+)"', section)
        self.assertEqual(paths, [h.DAEMONS + filename for _, filename, _ in h.HARDWARE_JOBS])
        self.assertEqual(len(paths), len(set(paths)))


if __name__ == '__main__':
    unittest.main()
