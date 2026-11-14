"""Check a generated unsigned IPA's platform, microphone description and model assets."""
from pathlib import Path
import argparse,hashlib,json,plistlib,struct,zipfile
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('ipa',type=Path);parser.add_argument('--source-commit',required=True);args=parser.parse_args()
with zipfile.ZipFile(args.ipa) as archive:
    assert archive.testzip() is None,'Archive CRC failed'
    infos=[name for name in archive.namelist() if name.startswith('Payload/') and name.count('/')==2 and name.endswith('.app/Info.plist')]
    assert len(infos)==1,'Expected exactly one application'
    info=plistlib.loads(archive.read(infos[0]));bundle=infos[0].removesuffix('Info.plist')
    assert info.get('DTPlatformName')=='iphoneos','Not an iPhone device build'
    assert info.get('NSMicrophoneUsageDescription'),'Missing microphone usage description'
    executable=archive.read(bundle+info['CFBundleExecutable'])
    magic,cpu=struct.unpack('<II',executable[:8]);assert magic==0xfeedfacf and cpu==0x100000c,'Expected native arm64 Mach-O'
    assert not any(name.endswith('/embedded.mobileprovision') for name in archive.namelist()),'Unexpected signing profile'
    models={}
    for name,path in [('yamnet_base.tflite',ROOT/'artifacts/yamnet_base.tflite'),('snore_score_head.tflite',ROOT/'artifacts/snore_v2/snore_score_head.tflite')]:
        matches=[entry for entry in archive.namelist() if entry.endswith('/flutter_assets/assets/'+name)]
        assert len(matches)==1,f'Missing asset {name}'
        digest=hashlib.sha256(archive.read(matches[0])).hexdigest();assert digest==hashlib.sha256(path.read_bytes()).hexdigest(),f'Wrong model {name}'
        models[name]=digest
    config_path=next(name for name in archive.namelist() if name.endswith('/flutter_assets/assets/mobile_metrics.json'))
    config=json.loads(archive.read(config_path));assert config['version']=='snore-v2-breathing-negatives'
result=dict(source_commit=args.source_commit,ipa_sha256=hashlib.file_digest(args.ipa.open('rb'),'sha256').hexdigest(),bundle_identifier=info['CFBundleIdentifier'],display_name=info.get('CFBundleDisplayName'),minimum_ios=info.get('MinimumOSVersion'),platform=info['DTPlatformName'],architecture='arm64',microphone_description_present=True,model_version=config['version'],model_sha256=models,signing='unsigned; no embedded provisioning profile',physical_device_tested=False)
out=ROOT/'results/native-ios';out.mkdir(parents=True,exist_ok=True);(out/'unsigned-build-checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
