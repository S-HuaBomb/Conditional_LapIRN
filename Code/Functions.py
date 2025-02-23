import SimpleITK as sitk
import numpy as np
import torch.utils.data as Data
import nibabel as nib
import torch
import glob
import itertools


def generate_grid(imgshape):
    x = np.arange(imgshape[0])
    y = np.arange(imgshape[1])
    z = np.arange(imgshape[2])
    grid = np.rollaxis(np.array(np.meshgrid(z, y, x)), 0, 4)
    grid = np.swapaxes(grid, 0, 2)
    grid = np.swapaxes(grid, 1, 2)
    return grid


# (grid[0, :, :, :, 0] - (size_tensor[3] / 2)) / size_tensor[3] * 2
def generate_grid_unit(imgshape):
    x = (np.arange(imgshape[0]) - ((imgshape[0] - 1) / 2)) / (imgshape[0] - 1) * 2
    y = (np.arange(imgshape[1]) - ((imgshape[1] - 1) / 2)) / (imgshape[1] - 1) * 2
    z = (np.arange(imgshape[2]) - ((imgshape[2] - 1) / 2)) / (imgshape[2] - 1) * 2
    grid = np.rollaxis(np.array(np.meshgrid(z, y, x)), 0, 4)
    grid = np.swapaxes(grid, 0, 2)
    grid = np.swapaxes(grid, 1, 2)
    return grid


def transform_unit_flow_to_flow(flow):
    x, y, z, _ = flow.shape
    flow[:, :, :, 0] = flow[:, :, :, 0] * (z - 1)
    flow[:, :, :, 1] = flow[:, :, :, 1] * (y - 1)
    flow[:, :, :, 2] = flow[:, :, :, 2] * (x - 1)

    return flow


def transform_unit_flow_to_flow_cuda(flow):
    b, x, y, z, c = flow.shape
    flow[:, :, :, :, 0] = flow[:, :, :, :, 0] * (z - 1)
    flow[:, :, :, :, 1] = flow[:, :, :, :, 1] * (y - 1)
    flow[:, :, :, :, 2] = flow[:, :, :, :, 2] * (x - 1)

    return flow


def load_4D(name):
    # X = sitk.GetArrayFromImage(sitk.ReadImage(name, sitk.sitkFloat32 ))
    # X = np.reshape(X, (1,)+ X.shape)
    X = nib.load(name)
    X = X.get_fdata()
    X = np.reshape(X, (1,) + X.shape)
    return X


def load_5D(name):
    # X = sitk.GetArrayFromImage(sitk.ReadImage(name, sitk.sitkFloat32 ))
    X = fixed_nii = nib.load(name)
    X = X.get_fdata()
    X = np.reshape(X, (1,) + (1,) + X.shape)
    return X


def imgnorm(img):
    max_v = np.max(img)
    min_v = np.min(img)
    norm_img = (img - min_v) / (max_v - min_v)
    return norm_img


def save_img(I_img, savename):
    # I2 = sitk.GetImageFromArray(I_img,isVector=False)
    # sitk.WriteImage(I2,savename)
    affine = np.diag([1, 1, 1, 1])
    new_img = nib.nifti1.Nifti1Image(I_img, affine, header=None)
    # save_path = os.path.join(output_path, file_index + "_wrapped_norm.nii")
    nib.save(new_img, savename)


def save_img_nii(I_img, savename):
    # I2 = sitk.GetImageFromArray(I_img,isVector=False)
    # sitk.WriteImage(I2,savename)
    affine = np.diag([1, 1, 1, 1])
    new_img = nib.nifti1.Nifti1Image(I_img, affine, header=None)
    # save_path = os.path.join(output_path, savename)
    nib.save(new_img, savename)


def save_flow(I_img, savename):
    # I2 = sitk.GetImageFromArray(I_img,isVector=True)
    # sitk.WriteImage(I2,savename)
    affine = np.diag([1, 1, 1, 1])
    new_img = nib.nifti1.Nifti1Image(I_img, affine, header=None)
    nib.save(new_img, savename)


class Dataset(Data.Dataset):
    """Characterizes a dataset for PyTorch"""

    def __init__(self, names, iterations, norm=False):
        """Initialization"""
        self.names = names
        self.norm = norm
        self.iterations = iterations

    def __len__(self):
        """Denotes the total number of samples"""
        return self.iterations

    def __getitem__(self, step):
        """Generates one sample of data"""
        # Select sample
        index_pair = np.random.permutation(len(self.names))[0:2]
        img_A = load_4D(self.names[index_pair[0]])
        img_B = load_4D(self.names[index_pair[1]])
        if self.norm:
            return torch.from_numpy(imgnorm(img_A)).float(), torch.from_numpy(imgnorm(img_B)).float()
        else:
            return torch.from_numpy(img_A).float(), torch.from_numpy(img_B).float()


class Dataset_epoch(Data.Dataset):
    """Characterizes a dataset for PyTorch"""

    def __init__(self, names, norm=False):
        """Initialization"""
        self.names = names
        self.norm = norm
        self.index_pair = list(itertools.permutations(names, 2))

    def __len__(self):
        """Denotes the total number of samples"""
        return len(self.index_pair)

    def __getitem__(self, step):
        """Generates one sample of data"""
        # Select sample
        img_A = load_4D(self.index_pair[step][0])
        img_B = load_4D(self.index_pair[step][1])

        # print(self.index_pair[step][0])
        # print(self.index_pair[step][1])

        if self.norm:
            return torch.from_numpy(imgnorm(img_A)).float(), torch.from_numpy(imgnorm(img_B)).float()
        else:
            return torch.from_numpy(img_A).float(), torch.from_numpy(img_B).float()


class Predict_dataset(Data.Dataset):
    def __init__(self, fixed_list, move_list, fixed_label_list, move_label_list, norm=False):
        super(Predict_dataset, self).__init__()
        self.fixed_list = fixed_list
        self.move_list = move_list
        self.fixed_label_list = fixed_label_list
        self.move_label_list = move_label_list
        self.norm = norm

    def __len__(self):
        """Denotes the total number of samples"""
        return len(self.move_list)

    def __getitem__(self, index):
        fixed_img = load_4D(self.fixed_list)
        moved_img = load_4D(self.move_list[index])
        fixed_label = load_4D(self.fixed_label_list)
        moved_label = load_4D(self.move_label_list[index])

        if self.norm:
            fixed_img = imgnorm(fixed_img)
            moved_img = imgnorm(moved_img)

        fixed_img = torch.from_numpy(fixed_img)
        moved_img = torch.from_numpy(moved_img)
        fixed_label = torch.from_numpy(fixed_label)
        moved_label = torch.from_numpy(moved_label)

        if self.norm:
            output = {'fixed': fixed_img.float(), 'move': moved_img.float(),
                      'fixed_label': fixed_label.float(), 'move_label': moved_label.float(), 'index': index}
            return output
        else:
            output = {'fixed': fixed_img.float(), 'move': moved_img.float(),
                      'fixed_label': fixed_label.float(), 'move_label': moved_label.float(), 'index': index}
            return output


if __name__ == '__main__':
    # datapath = '/home/wing/Desktop/registration/miccai2019/data_and_aseg/crop_min_max/norm'
    # names = sorted(glob.glob(datapath + '/*.nii'))[0:255]
    # dataset = Dataset_epoch(names, False)
    # training_generator = Data.DataLoader(Dataset_epoch(names, norm=False), batch_size=1,
    #                                      shuffle=False, num_workers=2)
    # for X, Y in training_generator:
    #     print("---")
    # # 64770 pairs
    # for i in range(0, dataset.__len__()):
    #     print(i, dataset.__len__())
    #     dataset.__getitem__(i)
    #     print("---")

    # imgshape = (5, 6, 7)
    # x = np.arange(imgshape[0])
    # y = np.arange(imgshape[1])
    # z = np.arange(imgshape[2])
    # grid = np.array(np.meshgrid(z, y, x)) #(3, 6, 7, 5)
    # grid = np.rollaxis(grid, 0, 4)# (6, 7, 5, 3)
    # grid = np.swapaxes(grid, 0, 2)# (5, 7, 6, 3)
    # grid = np.swapaxes(grid, 1, 2)# (5, 6, 7, 3)

    grid = generate_grid_unit((5, 6, 7))

    print(grid[:, :, :, 0].min(), grid[:, :, :, 0].max())  # -1, 1
    print(grid[:, :, :, 1].min(), grid[:, :, :, 1].max())  # -1, 1
    print(grid[:, :, :, 2].min(), grid[:, :, :, 2].max())  # -1, 1

    grid = generate_grid((5, 6, 7))
    # print(grid[:, :, :, 0]) # 0-6
    # print(grid[:, :, :, 1]) # 0-5
    # print(grid[:, :, :, 2]) # 0-4
    print("done")
