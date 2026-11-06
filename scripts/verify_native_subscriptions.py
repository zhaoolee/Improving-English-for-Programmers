#!/usr/bin/env python3
from pathlib import Path
import subprocess,zipfile,tempfile,argparse
parser=argparse.ArgumentParser(description="Validate generated packages with PicLex native models and decode README QR images; no simulator.")
parser.add_argument("--piclex-root",required=True,type=Path)
args=parser.parse_args()
repo=Path(__file__).resolve().parents[1]

def block(source,marker):
 start=source.index(marker);end=source.index('{',start)+1;depth=1
 while depth:
  depth+=(source[end]=='{')-(source[end]=='}');end+=1
 return source[start:end]
models=args.piclex_root/'PicLex'
card=(models/'Models/PhotoCard.swift').read_text();context=(models/'Models/ContextVocabulary.swift').read_text();archive=(models/'Services/PhotoArchive.swift').read_text()
source='import Foundation\nimport CoreGraphics\nimport CryptoKit\nimport ImageIO\nimport UniformTypeIdentifiers\nimport Vision\n'
source+=card[card.index('struct SceneBoundingBox:'):card.index('enum PhotoRecognitionStatus:')]
source+=context[context.index('struct VocabularyLearning:'):context.index('enum VocabularyStudyGoal:')]
source+='\n'+block(context,'struct VocabularyAudio:')+'\n'
for marker in ['enum PhotoArchiveFormat','struct PhotoArchiveManifest:','struct PhotoArchiveMetadata:','enum PhotoArchiveError:']:
 source+='\n'+block(archive,marker)+'\n'
# New optional cover metadata uses these native value types.
for marker in ['enum PhotoDeckCoverRole:', 'struct PhotoDeckCover:', 'struct PhotoDeckCovers:']:
 if marker in archive: source+='\n'+block(archive,marker)+'\n'
source+='''
let root = URL(fileURLWithPath: CommandLine.arguments[1])
let decoder = PhotoArchiveFormat.decoder()
let dirs = try FileManager.default.contentsOfDirectory(at: root, includingPropertiesForKeys: nil)
var count = 0
for dir in dirs where dir.hasDirectoryPath {
 let manifest = try decoder.decode(PhotoArchiveManifest.self, from: Data(contentsOf: dir.appendingPathComponent("manifest.json")))
 for item in manifest.photos {
  let raw = try Data(contentsOf: dir.appendingPathComponent(item.jsonPath))
  let meta = try decoder.decode(PhotoArchiveMetadata.self, from: raw)
  try meta.validate()
  precondition(PhotoArchiveFormat.digest(raw) == item.jsonSHA256)
  let image = try Data(contentsOf: dir.appendingPathComponent(meta.imagePath))
  precondition(PhotoArchiveFormat.digest(image) == meta.imageSHA256)
  _ = try PhotoArchiveFormat.imageExtension(image)
  count += 1
 }
}
print("Native metadata + image validation passed: \\(count) cards")
let assets = URL(fileURLWithPath: CommandLine.arguments[2])
for qr in try FileManager.default.contentsOfDirectory(at: assets, includingPropertiesForKeys: nil) where qr.lastPathComponent.hasSuffix("-qr.png") {
 let request = VNDetectBarcodesRequest(); request.symbologies = [.qr]; request.usesCPUOnly = true
 try VNImageRequestHandler(url: qr).perform([request])
 let slug = qr.lastPathComponent.replacingOccurrences(of: "-qr.png", with: "")
 let expected = slug.hasPrefix("classic-") ? "https://piclex.v2fy.com/public/subscriptions/" + slug + "/feed.json" : "https://zhaoolee.com/Improving-English-for-Programmers/subscriptions/" + slug + "/feed.json"
 precondition(request.results?.first?.payloadStringValue == expected)
 print("QR decoded: " + slug)
}
'''
with tempfile.TemporaryDirectory(prefix='readme-native-') as tmp:
 dest=Path(tmp); data=dest/'data';data.mkdir()
 for pack in (repo/'public-hugo/subscriptions').glob('*/*.piclexdeck'):
  with zipfile.ZipFile(pack) as z:z.extractall(data/pack.parent.name)
 (dest/'main.swift').write_text(source)
 subprocess.run(['xcrun','swiftc','-module-cache-path',str(dest/'cache'),str(dest/'main.swift'),'-o',str(dest/'check')],check=True)
 subprocess.run([str(dest/'check'),str(data),str(repo/'site/static/series')],check=True)
