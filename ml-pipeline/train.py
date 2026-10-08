#!/usr/bin/env python3
"""
Train a behavior-cloning driving policy from one or more recorded AV Sim sessions.

This is the main student-tunable surface: --lr, --epochs, --batch-size, --width (model
capacity), and --max-samples (dataset size) are all exposed deliberately, so changing them and
re-running against the AV Sim (see bridge/run_trained_policy.py) produces an observably different
driving behavior.
"""
import argparse
import sys
from pathlib import Path

import torch
from torch.utils.data import DataLoader, ConcatDataset, random_split

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dataset import DrivingFrameDataset
from model import DrivingPolicyNet


def parse_args():
  p = argparse.ArgumentParser(description="Train a behavior-cloning driving policy.")
  p.add_argument("dataset_dirs", nargs="+", help="one or more directories produced by bridge/run_record_session.py")
  p.add_argument("--epochs", type=int, default=10)
  p.add_argument("--batch-size", type=int, default=32)
  p.add_argument("--lr", type=float, default=1e-3)
  p.add_argument("--val-split", type=float, default=0.1)
  p.add_argument("--width", type=float, default=1.0, help="model capacity multiplier")
  p.add_argument("--max-samples", type=int, default=None, help="cap total dataset size, to compare data-quantity effects")
  p.add_argument("--seed", type=int, default=0)
  p.add_argument("--out", default="checkpoint.pt")
  return p.parse_args()


def build_dataset(dataset_dirs, max_samples, seed):
  datasets = [DrivingFrameDataset(d) for d in dataset_dirs]
  dataset = ConcatDataset(datasets)
  if max_samples is not None and max_samples < len(dataset):
    generator = torch.Generator().manual_seed(seed)
    indices = torch.randperm(len(dataset), generator=generator)[:max_samples].tolist()
    dataset = torch.utils.data.Subset(dataset, indices)
  return dataset


def main():
  args = parse_args()
  torch.manual_seed(args.seed)

  dataset = build_dataset(args.dataset_dirs, args.max_samples, args.seed)
  if len(dataset) == 0:
    raise SystemExit("no samples found -- check dataset_dirs point at recorded sessions with a non-empty labels.csv")

  val_size = int(len(dataset) * args.val_split)
  train_size = len(dataset) - val_size
  generator = torch.Generator().manual_seed(args.seed)
  train_set, val_set = random_split(dataset, [train_size, val_size], generator=generator)

  train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True)
  val_loader = DataLoader(val_set, batch_size=args.batch_size) if val_size > 0 else None

  model = DrivingPolicyNet(width=args.width)
  optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
  loss_fn = torch.nn.MSELoss()

  for epoch in range(args.epochs):
    model.train()
    train_loss = 0.0
    for images, labels in train_loader:
      optimizer.zero_grad()
      preds = model(images)
      loss = loss_fn(preds, labels)
      loss.backward()
      optimizer.step()
      train_loss += loss.item() * images.size(0)
    train_loss /= len(train_set)

    msg = f"epoch {epoch + 1}/{args.epochs}  train_loss={train_loss:.4f}"
    if val_loader is not None:
      model.eval()
      val_loss = 0.0
      with torch.no_grad():
        for images, labels in val_loader:
          val_loss += loss_fn(model(images), labels).item() * images.size(0)
      val_loss /= len(val_set)
      msg += f"  val_loss={val_loss:.4f}"
    print(msg)

  torch.save({"state_dict": model.state_dict(), "width": args.width}, args.out)
  print(f"saved checkpoint to {args.out}")


if __name__ == "__main__":
  main()
