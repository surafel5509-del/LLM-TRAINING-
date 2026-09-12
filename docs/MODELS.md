# Models

MLP classification and regression are implemented as actual PyTorch modules. Model versions are created only when a run reaches `COMPLETED` and a final checkpoint exists.

A version records its originating run, checkpoint path, version number, and real test metrics. Previous versions are never overwritten.

CNN, sequence models, ONNX export and TorchScript export are intentionally not implemented in this release.
