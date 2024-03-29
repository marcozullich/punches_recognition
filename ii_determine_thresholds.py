import argparse
from sqlite3 import paramstyle

import os

import torch
from matplotlib import pyplot as plt, font_manager as fm, rcParams

from punches_lib import datasets
from punches_lib.ii_loss import eval as eval_ii
from punches_lib.ii_loss import models
from punches_lib.radam import RAdam

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path_outlier_scores_valid", type=str, default="model/model_ii.pth_valid.pth", help="path to the outlier scores of the validation set (default: model/model_ii.pth_valid.pth).")
    # parser.add_argument("--path_outlier_scores_crops", type=str, default="model/model_ii.pth_crops.pth", help="path to the outlier scores of the ood set (default: model/model_ii.pth_crops.pth).")
    parser.add_argument("--path_outlier_scores_ood", type=str, default="model/model_ii.pth_ood.pth", help="path to the outlier scores of the ood set (default: model/model_ii.pth_ood.pth).")
    parser.add_argument("--save_path", type=str, default="model/model_ii_hist.png", help="path where the hist will be saved (default: model/model_ii_hist.png).")
    # parser.add_argument("--use_MDPI_font", action="store_true", default=False, help="use the MDPI font.")
    parser.add_argument("--font", type=str, default=None, help="font to use.")
    parser.add_argument("--threshold", type=float, default=None, help="threshold to draw on the histogram (default: None).")
    parser.add_argument("--y_scale_log", action="store_true", default=False, help="use a log scale for the y axis.")
    return parser.parse_args()

def main():
    args = get_args()

    if args.font is not None:
        if not any(args.font in str(font_entry) for font_entry in fm.fontManager.ttflist):
            try:
                # check user dir for existence of font
                font_path = os.path.expanduser(f"~/.fonts/{args.font}.ttf")
                fm.fontManager.addfont(font_path)
            except FileNotFoundError:
                print(f"Could not find the desired font '{args.font}'. Using the default font.")
                args.font = None
        rcParams["font.family"] = args.font

    scores_valid = torch.load(args.path_outlier_scores_valid, map_location="cpu")
    #scores_crops = torch.load(args.path_outlier_scores_crops, map_location="cpu")
    scores_ood = torch.load(args.path_outlier_scores_ood, map_location="cpu")

    fig = plt.figure(figsize=(8,2.5))
    plt.hist(scores_valid.numpy(), bins=75, label="Validation dataset", alpha=0.5, density=True)
    #plt.hist(scores_crops.numpy(), bins=100, label="crops", alpha=0.5, density=True)
    plt.hist(scores_ood.numpy(), bins=30, label="OOD training set", alpha=0.5, density=True)
    if args.threshold is not None:
        plt.axvline(args.threshold, color="r", linestyle="--", label=f"threshold ({args.threshold:.4f})")
    if args.y_scale_log:
        plt.yscale("log")
        plt.ylabel("Density (log scale)")
    else:
        plt.ylabel("Density")
    plt.xlabel("OS")
    
    plt.tight_layout()
    
    plt.legend(loc="upper right")
    plt.savefig(args.save_path)

if __name__ == "__main__":
    main()

