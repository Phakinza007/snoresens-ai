# Third-party assets and data

This repository contains the INT182 Snoresens AI project source, trained heads, model artifacts and documentation. Public visibility does not change third-party license terms.

- YAMNet pretrained model: Google / TensorFlow, Apache License 2.0. Source and documentation: https://github.com/tensorflow/models/tree/master/research/audioset/yamnet
- TensorFlow.js / TensorFlow Lite WASM runtime: Apache License 2.0. Bundled license: `deployments/snoresens-vercel/dist/vendor/LICENSE-TENSORFLOW.txt`.
- Lucide icons: Lucide Static 0.468.0. License: `web/snoresens/LUCIDE-LICENSE.txt`.
- Noto Sans Thai: SIL Open Font License, `web/snoresens/FONT-LICENSE.txt`.
- `test_snore.wav`, `test_snore_16k.wav`, and the cropped/edited demo WAV in the static deployment derive from **Tongue base snoring**, by **Langenbergstefan**, Wikimedia Commons: https://commons.wikimedia.org/wiki/File:Tongue_base_snoring.ogg . Audio is CC BY-SA 3.0: https://creativecommons.org/licenses/by-sa/3.0/ . Changes include conversion to mono 16 kHz PCM WAV, cropping, and insertion of silence in the 45-second demo. Derived audio remains under CC BY-SA 3.0.
- Training data references (raw datasets are not committed): [Kaggle Snoring Dataset](https://www.kaggle.com/datasets/tareqkhanemu/snoring) and [IISc Coswara](https://github.com/iiscleap/Coswara-Data). Follow each source's data terms when obtaining it.
- Design reference supplied for the project: https://www.figma.com/design/CyO0k9yBp1nxGHMsvJhHuk?node-id=3-130 . See `web/snoresens/CREDITS.md` for implementation/asset details.

No `.env`, deployment credentials, browser authentication tokens, local virtual environments, personal recordings, or raw training recordings are intended for this repository. The included audio is the specifically attributed public demonstration sample, not user-uploaded recordings.
