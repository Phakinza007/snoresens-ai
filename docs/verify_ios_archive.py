"""Verify an unsigned device IPA, its app capabilities and the frozen v2 model assets."""
from pathlib import Path
import argparse
import hashlib
import json
import plistlib
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('ipa', type=Path)
parser.add_argument('--source-commit', required=True)
parser.add_argument('--expected-version')
parser.add_argument('--require-background-audio', action='store_true')
parser.add_argument('--output', type=Path, default=ROOT / 'results/native-ios/unsigned-build-checks.json')
args = parser.parse_args()
with zipfile.ZipFile(args.ipa) as archive:
    assert archive.testzip() is None, 'Archive CRC failed'
    infos = [name for name in archive.namelist() if name.startswith('Payload/')
             and name.count('/') == 2 and name.endswith('.app/Info.plist')]
    assert len(infos) == 1, 'Expected exactly one application'
    info = plistlib.loads(archive.read(infos[0]))
    bundle = infos[0].removesuffix('Info.plist')
    assert info.get('DTPlatformName') == 'iphoneos', 'Not an iPhone device build'
    assert info.get('NSMicrophoneUsageDescription'), 'Missing microphone usage description'
    if args.expected_version:
        assert info.get('CFBundleShortVersionString') == args.expected_version, 'Wrong app version'
    if args.require_background_audio:
        assert 'audio' in info.get('UIBackgroundModes', []), 'Missing background audio mode'
        assert info.get('UIFileSharingEnabled') is True, 'Missing document sharing'
        assert info.get('LSSupportsOpeningDocumentsInPlace') is True, 'Missing Files integration'
    executable = archive.read(bundle + info['CFBundleExecutable'])
    magic, cpu = struct.unpack('<II', executable[:8])
    assert magic == 0xfeedfacf and cpu == 0x100000c, 'Expected native arm64 Mach-O'
    assert not any(name.endswith('/embedded.mobileprovision') for name in archive.namelist()), 'Unexpected signing profile'
    models = {}
    for name, path in [('yamnet_base.tflite', ROOT / 'artifacts/yamnet_base.tflite'),
                       ('snore_score_head.tflite', ROOT / 'artifacts/snore_v2/snore_score_head.tflite')]:
        matches = [entry for entry in archive.namelist() if entry.endswith('/flutter_assets/assets/' + name)]
        assert len(matches) == 1, f'Missing asset {name}'
        digest = hashlib.sha256(archive.read(matches[0])).hexdigest()
        assert digest == hashlib.sha256(path.read_bytes()).hexdigest(), f'Wrong model {name}'
        models[name] = digest
    config_path = next(name for name in archive.namelist() if name.endswith('/flutter_assets/assets/mobile_metrics.json'))
    config = json.loads(archive.read(config_path))
    assert config['version'] == 'snore-v2-breathing-negatives', 'Wrong model configuration'
with args.ipa.open('rb') as stream:
    ipa_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
result = dict(
    source_commit=args.source_commit, ipa_sha256=ipa_hash,
    app_version=info.get('CFBundleShortVersionString'), build_number=info.get('CFBundleVersion'),
    bundle_identifier=info['CFBundleIdentifier'], display_name=info.get('CFBundleDisplayName'),
    minimum_ios=info.get('MinimumOSVersion'), platform=info['DTPlatformName'], architecture='arm64',
    microphone_description_present=True, background_modes=info.get('UIBackgroundModes', []),
    file_sharing=info.get('UIFileSharingEnabled', False),
    open_documents_in_place=info.get('LSSupportsOpeningDocumentsInPlace', False),
    model_version=config['version'], model_sha256=models,
    signing='unsigned; no embedded provisioning profile', physical_device_tested=False,
)
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False, indent=2))
