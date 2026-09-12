# Training

The implemented engine uses CPU-only PyTorch. Every batch executes `zero_grad`, forward, loss, `backward`, and `optimizer.step`.

Reproducibility records seed, split ratios, architecture, optimizer, learning rate, batch size, CPU worker/thread settings, feature columns, and scaler parameters in the final checkpoint.

Each epoch persists train/validation loss and a task metric. A checkpoint is written after every epoch. Test evaluation happens only after training and uses the isolated test split.

Pause is cooperative between epochs/batches, resume removes the pause control file, and cancel is cooperative. A crash leaves the latest valid checkpoint on disk.
