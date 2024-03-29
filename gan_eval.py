import os
import torch
from torch.utils.data import Dataset, DataLoader
from torch import nn
import argparse
from typing import Union

from punches_lib.gan import models, models_experimental as me, features,  testing, utils
from punches_lib import datasets



def load_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--discriminator_path", type=str, required=True, help="Path where the params for the discriminator are stored.")
    parser.add_argument("--discriminator_type", type=str, default="classic", choices=["classic", "experimental"], help="Type of discriminator to use. Options: funnel, conv, dense.")
    parser.add_argument("--input_channel_dim", type=int, default=512, help="Number of channels of the input data (the features representation of the images --- default: 512).")
    parser.add_argument("--base_width", type=int, default=64, help="Base width (i.e., minimum number of output channels) per hidden conv layer in discriminator and generator (default: 64).")
    parser.add_argument("--batch_size", type=int, default=128, help="Batch size for evaluating the features (default: 128).")
    parser.add_argument("--validset_root", type=str, default=None, help="Root where the validation data are stored (default: None).")
    parser.add_argument("--openset_root", type=str, default=None, help="Root where the open data are stored (default: None).")
    parser.add_argument("--path_features_train", type=str, default=None, help="Path from where the features for training the GAN will be loaded from. If None, features will be calculated at runtime but not saved. Features must be loaded and cannot be recalculated.")
    parser.add_argument("--path_features_valid", type=str, default=None, help="Path from where the features for the validation dataset will be loaded from. If None, features will be calculated at runtime but not saved. For recalculating the features and saving them in this path, toggle the switch --force_feats_recalculation (default: None).")
    parser.add_argument("--path_features_open", type=str, default=None, help="Path from where the features for the open data dataset will be loaded from. If None, features will be calculated at runtime but not saved. For recalculating the features and saving them in this path, toggle the switch --force_feats_recalculation (default: None).")
    parser.add_argument("--path_features_crops", type=str, default=None, help="")
    parser.add_argument("--force_feats_recalculation", action="store_true", default=False, help="Force recalculation of the features even if --backbone_network_feats is passed")
    parser.add_argument("--backbone_network_feats", type=str, choices=["resnet18", "resnet34", "resnet50", None], default=None, help="Backbone network for obtaining the features (default: None).")
    parser.add_argument("--backbone_network_params", type=str, default=None, help="Path to the state_dict containing the parameters for the pretrained backbone (default: None)")
    parser.add_argument("--folder_save_outputs", type=str, default=None, help="Folder where to save the outputs after discriminator evaluation (default: None).")
    parser.add_argument("--save_hist_path", type=str, default="hist.png", help="Path where to save the histogram (default: hist.png).")
    parser.add_argument("--by", type=float, default=0.05, help="Calculation of performance: increment used for swiping the axis 0-1 in search of a threshold (default: 0.05).")
    parser.add_argument("--save_performance_path", type=str, default="performance.csv", help="Path where to save the performance as a CSV file (default: performance.csv).")
    parser.add_argument("--rescale_factor", type=float, default=1.0, help="Rescale factor for the embeddings (default: 1.0).")
    parser.add_argument("--device", type=str, default=None, help="Device to use for the computations (default: None -> use CUDA if available).")
    parser.add_argument("--verbose", action="store_true", default=False, help="Verbose mode (default: False).")
    parser.add_argument("--do_random", action="store_true", default=False, help="Do eval with random sample (default: False).")
    args = parser.parse_args()
    return args

def main():
    args = load_args()
    
    # INSTANTIATE DISCRIMINATOR AND LOAD WEIGHTS
    if args.discriminator_type == "classic":
        netD = models.DiscriminatorFunnel(num_channels=args.input_channel_dim, base_width=args.base_width)
    elif args.discriminator_type == "experimental":
        netD = me.Discriminator(num_channels=args.input_channel_dim, base_width=args.base_width)
    else:
        raise ValueError("Invalid discriminator type: {}".format(args.discriminator_type))
    netD.load_state_dict(torch.load(args.discriminator_path))

    if args.verbose:
        print("...Discriminator loaded.")

        print("...Getting datasets:", end=" ")
    # OBTAIN THE FEATURES AND DATALOADERS
    dataset_valid = datasets.get_dataset(args.validset_root, transforms=datasets.get_bare_transforms()) if args.validset_root is not None else None
    dataset_open = datasets.get_dataset(args.openset_root, transforms=datasets.get_bare_transforms()) if args.openset_root is not None else None
    if args.do_random:
        dataset_random = datasets.BasicDataset(torch.randn((500, 3, 256, 256)))
    
    if args.verbose:
        print("\u2713")    

        print("...Computing features")
        print("\t\t Validation:", end=" ")
    valid_features = features.get_features(args.path_features_valid, args.force_feats_recalculation, dataset_valid, args.backbone_network_feats, args.backbone_network_params, args.batch_size, num_classes=19, device=args.device) if dataset_valid is not None else None
    if args.rescale_factor != 1.0:
        valid_features = torch.nn.functional.interpolate(valid_features, scale_factor=args.rescale_factor, mode='bilinear')
    if args.verbose:
        print("\u2713")
        print("\t\t Open:", end=" ")
    open_features = features.get_features(args.path_features_open, args.force_feats_recalculation, dataset_open, args.backbone_network_feats, args.backbone_network_params, args.batch_size, num_classes=19, device=args.device) if dataset_open is not None else None
    if args.rescale_factor != 1.0:
        open_features = torch.nn.functional.interpolate(open_features, scale_factor=args.rescale_factor, mode='bilinear')
    if args.verbose:
        print("\u2713")

    crops_features = features.get_features(args.path_features_crops, args.force_feats_recalculation, None, args.backbone_network_feats, args.backbone_network_params, args.batch_size, num_classes=19, device=args.device) if args.path_features_crops is not None else None
    rand_features = None
    if args.do_random:
        rand_features = features.get_features(None, True, dataset_random, args.backbone_network_feats, args.backbone_network_params, args.batch_size, num_classes=19, device=args.device)

    
    # train_features = features.get_features(args.path_features_train, False, None, args.backbone_network_feats, args.backbone_network_params, args.batch_size, num_classes=19) if args.path_features_train is not None else None

    # trainloader = DataLoader(datasets.BasicDataset(train_features), batch_size=args.batch_size, shuffle=False, num_workers=4) if train_features is not None else None
    validloader = DataLoader(datasets.BasicDataset(valid_features), batch_size=args.batch_size, shuffle=False, num_workers=4) if valid_features is not None else None
    openloader = DataLoader(datasets.BasicDataset(open_features), batch_size=args.batch_size, shuffle=False, num_workers=4) if open_features is not None else None
    cropsloader = DataLoader(datasets.BasicDataset(crops_features), batch_size=args.batch_size, shuffle=False, num_workers=4) if crops_features is not None else None
    if args.do_random:
        randloader = DataLoader(datasets.BasicDataset(rand_features), batch_size=args.batch_size, shuffle=False, num_workers=4) if rand_features is not None else None
    
    # outs_train = testing.get_outputs(netD, trainloader).squeeze() if trainloader is not None else None
    if args.verbose:
        print("...Evaluating discriminator")
        print("\t\t Validation:", end=" ")
    outs_valid = testing.get_outputs(netD, validloader, device=args.device).squeeze() if validloader is not None else None
    if args.verbose:
        print("\u2713")
        print("\t\t Open:", end=" ")
    outs_open = testing.get_outputs(netD, openloader, device=args.device).squeeze() if openloader is not None else None
    if args.verbose:
        print("\u2713")
    outs_crops = testing.get_outputs(netD, cropsloader, device=args.device).squeeze() if cropsloader is not None else None
    outs_rand = None
    if args.do_random:
        outs_rand = testing.get_outputs(netD, randloader, device=args.device).squeeze() if randloader is not None else None

    

    if (fold:=args.folder_save_outputs) is not None:
        os.makedirs(fold, exist_ok=True)
        # torch.save(outs_train, os.path.join(fold, "train.pt"))
        torch.save(outs_valid, os.path.join(fold, "validouts_valid.pt"))
        torch.save(outs_open, os.path.join(fold, "open.pt"))
        print(f"Outputs saved in {args.folder_save_outputs}")

    if (fold:=os.path.dirname(args.save_hist_path)) != "":
        os.makedirs(fold, exist_ok=True)
    testing.plot_hist(outputs_ood=outs_open, outputs_test=outs_valid, outputs_random=outs_rand, outputs_crops=outs_crops, save_path=args.save_hist_path, title="Discriminator validation")

    additional_outputs = None
    if outs_rand is not None and outs_crops is not None:
        additional_outputs = torch.cat((outs_rand, outs_crops), dim=0)
    elif outs_rand is not None:
        additional_outputs = outs_rand
    elif outs_crops is not None:
        additional_outputs = outs_crops

    perf = testing.get_performance(outs_valid, outs_open, increment=args.by, additional_outputs=additional_outputs) if outs_valid is not None else None
    if (fold:=os.path.dirname(args.save_performance_path)) != "":
        os.makedirs(fold, exist_ok=True)
    perf.to_csv(args.save_performance_path)

    print("Best\n", perf.nlargest(1, "W"))

    if additional_outputs is not None:
        print("Best (additional)\n", perf.nlargest(1, "AW"))

    
if __name__ == "__main__":
    main()
