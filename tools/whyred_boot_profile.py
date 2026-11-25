"""Exact, opt-in launchd policy for hardware absent from the current whyred port.

Only Disabled changes. Stock API providers and UI/diagnostic jobs are preserved.
This is a hardware-test candidate, not evidence of faster boot or working clients.
"""
import copy

# label, exact native filename, reason; filenames are not inferred from labels.
HARDWARE_JOBS = (
    ('com.apple.wifi.hostapd', 'com.apple.wifi.hostapd.plist', 'Wi-Fi access point'),
    ('com.apple.wifi.wapic', 'com.apple.wifi.wapic.plist', 'Wi-Fi WAPI'),
    ('com.apple.wifiFirmwareLoader', 'com.apple.wifiFirmwareLoader.plist', 'Wi-Fi firmware'),
    ('com.apple.wifianalyticsd', 'com.apple.wifianalyticsd.plist', 'Wi-Fi analytics'),
    ('com.apple.wifid', 'com.apple.wifid.plist', 'Wi-Fi hardware manager'),
    ('com.apple.wifip2pd', 'com.apple.wifip2pd.plist', 'Wi-Fi peer-to-peer'),
    ('com.apple.wifivelocityd', 'com.apple.wifivelocityd.plist', 'Wi-Fi diagnostics'),
    ('com.apple.BluetoothUIService', 'com.apple.bluetoothuiservice.plist', 'Bluetooth UI helper'),
    ('com.apple.bluetoothuserd', 'com.apple.bluetoothuserd.plist', 'Bluetooth user helper'),
    ('com.apple.WirelessRadioManager', 'com.apple.WirelessRadioManager.plist', 'Radio coexistence'),
    ('com.apple.nfcd', 'com.apple.nfcd.plist', 'NFC hardware'),
    ('com.apple.applecamerad', 'com.apple.applecamerad.plist', 'Camera hardware'),
    ('com.apple.dietapplecamerad', 'com.apple.dietapplecamerad.plist', 'Camera hardware'),
    ('com.apple.dietappleh13camerad', 'com.apple.dietappleh13camerad.plist', 'Camera hardware'),
    ('com.apple.ptpcamerad', 'com.apple.ptpcamerad.plist', 'External PTP camera'),
    ('com.apple.gpsd', 'com.apple.gpsd.plist', 'GPS hardware'),
    ('com.apple.awdd', 'com.apple.awdd.plist', 'Wireless diagnostics'),
    ('com.apple.accessibility.motiontrackingd', 'com.apple.accessibility.motiontrackingd.plist', 'Motion tracking hardware'),
    ('com.apple.DumpBasebandCrash', 'com.apple.DumpBasebandCrash.plist', 'Apple baseband crash helper'),
)
DAEMONS = '/System/Library/LaunchDaemons/'


def merge(cache, native_jobs):
    """Validate both copies, return new cache + native files without mutating inputs."""
    jobs = cache.get('LaunchDaemons')
    if not isinstance(jobs, dict) or len(jobs) != 532:
        raise ValueError('Expected the complete532-job display cache')
    paths = {DAEMONS + filename for _, filename, _ in HARDWARE_JOBS}
    if set(native_jobs) != paths:
        raise ValueError('Missing/extra native hardware job')
    result, native = copy.deepcopy(cache), copy.deepcopy(native_jobs)
    for label, filename, _ in HARDWARE_JOBS:
        path = DAEMONS + filename
        original = native_jobs[path]
        cached = jobs.get(path)
        if not isinstance(original, dict) or not isinstance(cached, dict):
            raise ValueError('Invalid native/cache job: ' + label)
        if original.get('Label') != label or cached.get('Label') != label:
            raise ValueError('Native/cache label mismatch: ' + label)
        # Some cache entries have bootstrap-specific extra keys. Preserve each
        # copy independently; only executable identity must match.
        for key in ('Program', 'ProgramArguments'):
            if original.get(key) != cached.get(key):
                raise ValueError('Native/cache executable mismatch: ' + label)
        if original.get('Disabled', False) is not False or cached.get('Disabled', False) is not False:
            raise ValueError('Baseline hardware job already disabled: ' + label)
        native[path]['Disabled'] = True
        result['LaunchDaemons'][path]['Disabled'] = True
    # Deep conservation: every other job, cache key, endpoint and activation
    # condition must survive; the only allowed delta is these19 booleans.
    restored = copy.deepcopy(result)
    for _, filename, _ in HARDWARE_JOBS:
        path = DAEMONS + filename
        if 'Disabled' in jobs[path]:
            restored['LaunchDaemons'][path]['Disabled'] = jobs[path]['Disabled']
        else:
            del restored['LaunchDaemons'][path]['Disabled']
        check = copy.deepcopy(native[path])
        if 'Disabled' in native_jobs[path]:
            check['Disabled'] = native_jobs[path]['Disabled']
        else:
            del check['Disabled']
        if check != native_jobs[path]:
            raise ValueError('Native fields changed: ' + path)
    if restored != cache:
        raise ValueError('Unrelated cache changes')
    return result, native
