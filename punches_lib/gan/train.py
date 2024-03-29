import torch
import torchvision.utils as vutils
import os
import copy

# Training Loop
def train_model(num_epochs, dataloader, netG, netD, real_label, fake_label, optimizerG, optimizerD, nz, fixed_noise, criterion, device, save_dir):
    # Lists to keep track of progress
    img_list = []
    G_losses = []
    D_losses = []
    iters = 0
    netG.to(device)
    netD.to(device)
    fixed_noise.to(device)
    label_smoothing_factor = 0.15

    print("Starting Training Loop...")
    # For each epoch
    for epoch in range(num_epochs):
        # For each batch in the dataloader
        #for i, data in enumerate(dataloader, 0):
        for i, data in enumerate(dataloader, 0):
            ############################
            # (1) Update D network: maximize log(D(x)) + log(1 - D(G(z)))
            ###########################
            ## Train with all-real batch
            netD.zero_grad()
            # Format batch
            real_cpu = data.to(device)
            b_size = real_cpu.size(0)
            label = torch.full((b_size,), real_label, dtype=torch.float, device=device)
            # labels smoothing
            label -= (torch.rand(b_size, device=device) * label_smoothing_factor * (1 if real_label == 1 else -1))
            # Forward pass real batch through D
            output = netD(real_cpu).view(-1)
            # Calculate loss on all-real batch
            errD_real = criterion(output, label)
            # Calculate gradients for D in backward pass
            errD_real.backward()
            D_x = output.mean().item()

            ## Train with all-fake batch
            # Generate batch of latent vectors
            noise = torch.randn(b_size, nz, 8, 8, device=device)
            # Generate fake image batch with G
            fake = netG(noise)
            label.fill_(fake_label)
            # labels smoothing
            label += (torch.rand(b_size, device=device) * label_smoothing_factor * (1 if fake_label == 0 else -1))
            # Classify all fake batch with D
            output = netD(fake.detach()).view(-1)
            # Calculate D's loss on the all-fake batch
            errD_fake = criterion(output, label)
            # Calculate the gradients for this batch
            errD_fake.backward()
            D_G_z1 = output.mean().item()
            # Add the gradients from the all-real and all-fake batches
            errD = errD_real + errD_fake
            # Update D
            optimizerD.step()

            ############################
            # (2) Update G network: maximize log(D(G(z)))
            ###########################
            netG.zero_grad()
            label.fill_(real_label)  # fake labels are real for generator cost
            # Since we just updated D, perform another forward pass of all-fake batch through D
            output = netD(fake).view(-1)
            # Calculate G's loss based on this output
            errG = criterion(output, label)
            # Calculate gradients for G
            errG.backward()
            D_G_z2 = output.mean().item()
            # Update G
            optimizerG.step()

            # Output training stats
            if i % 200 == 0:
                print('[%d/%d][%d/%d]\tLoss_D: %.4f\tLoss_G: %.4f\tD(x): %.4f\tD(G(z)): %.4f / %.4f'
                      % (epoch, num_epochs, i, len(dataloader),
                         errD.item(), errG.item(), D_x, D_G_z1, D_G_z2))

            # Save Losses for plotting later
            G_losses.append(errG.item())
            D_losses.append(errD.item())

            # Check how the generator is doing by saving G's output on fixed_noise
            if (iters % 500 == 0) or ((epoch == num_epochs - 1) and (i == len(dataloader) - 1)):
                with torch.no_grad():
                  fake = netG(fixed_noise.to(device)).detach().cpu()
                  #fake.detach().cpu()
                img_list.append(vutils.make_grid(fake, padding=2, normalize=True))

            iters += 1
        if epoch > 850:
          cur_model_wts = copy.deepcopy(netG.state_dict())
          path_to_save_paramOnly = os.path.join(save_dir, 'epoch-{}.GNet'.format(epoch + 1))
          torch.save(cur_model_wts, path_to_save_paramOnly)

          cur_model_wts = copy.deepcopy(netD.state_dict())
          path_to_save_paramOnly = os.path.join(save_dir, 'epoch-{}.DNet'.format(epoch + 1))
          torch.save(cur_model_wts, path_to_save_paramOnly)

    return G_losses, D_losses
