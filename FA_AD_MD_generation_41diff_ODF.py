interactive = False

from dipy.core.gradients import gradient_table
from dipy.io.image import load_nifti
from dipy.io.gradients import read_bvals_bvecs
from dipy.reconst.csdeconv import auto_response_ssst
from dipy.reconst.dti import TensorModel, fractional_anisotropy, mean_diffusivity, axial_diffusivity
from dipy.data import default_sphere
from dipy.reconst.dti import color_fa
from dipy.direction import peaks_from_model
from dipy.viz import window, actor, has_fury
from dipy.segment.mask import median_otsu
from dipy.tracking.local_tracking import LocalTracking, pft_tracker
from dipy.tracking.streamline import Streamlines
from dipy.tracking import utils
from dipy.tracking.stopping_criterion import (AnatomicalStoppingCriterion,
                                              StreamlineStatus)
from dipy.io.stateful_tractogram import Space, StatefulTractogram
from dipy.io.streamline import save_tck
from dipy.viz import colormap
import os
from sklearn.neighbors import KDTree
import numpy as np
import nibabel as nib
from dipy.io import read_bvals_bvecs
from dipy.core.gradients import gradient_table
from dipy.segment.mask import median_otsu
from dipy.reconst.dti import TensorModel, fractional_anisotropy, mean_diffusivity, axial_diffusivity
from scipy.spatial import KDTree
from sklearn.neighbors import KDTree


# Function to load NIFTI file
def load_nifti(file_path, return_img=False):
    nifti_img = nib.load(file_path)
    data = nifti_img.get_fdata()
    affine = nifti_img.affine
    if return_img:
        return data, affine, nifti_img
    return data, affine


# Load JHU template
jhu_template_path = 'JHU-ICBM-labels-1mm.nii.gz'
jhu_template_img = nib.load(jhu_template_path)
jhu_template_data = jhu_template_img.get_fdata()

# 5 - body of corpus callosum
# 7 - fornix
# 8 - corticospinal tract r
# 16 - cerebral peduncle r
# 18 - anterior limb of internal capsule r
# 36, 37, 38, 39 - cingulum

roi_labels = [5, 7, 8, 16, 18, 36, 37, 38, 39]


subject_folder = ["003_S_4441_CN_F_69","003_S_4350_CN_M_73","109_S_4499_CN_M_84",
                  "003_S_4288_CN_F_73","003_S_4644_CN_F_68","007_S_4620_CN_M_77",
                  "098_S_4018_CN_M_76","098_S_4003_CN_F_78","094_S_4234_CN_M_70",
                  "021_S_4335_CN_F_73","021_S_4276_CN_F_75","016_S_2284_EMCI_M_73",
                  "016_S_4575_EMCI_F_62","016_S_2007_EMCI_F_84","005_S_4185_EMCI_M_81",
                  "007_S_2106_EMCI_M_81","005_S_2390_EMCI_F_89","016_S_4902_LMCI_F_77",
                  "016_S_4646_LMCI_F_62","016_S_4584_LMCI_F_78","007_S_4611_LMCI_M_68",
                  "003_S_4524_LMCI_M_72","003_S_4354_LMCI_M_76","021_S_4857_LMCI_M_68",
                  "003_S_2374_F_82_EMCI","057_S_4909_F_78_LMCI","003_S_4119_M_79_CN",
                  "057_S_4897_F_76_EMCI","094_S_2367_M_75_EMCI","003_S_4081_F_73_CN",
                  "094_S_2216_M_69_EMCI","094_S_4162_F_72_LMCI","094_S_4503_F_72_CN",
                  "094_S_4630_F_66_LMCI","098_S_0896_M_86_CN","098_S_2047_M_78_EMCI",
                  "094_S_4858_M_57_EMCI","098_S_2052_M_74_EMCI","094_S_4295_F_70_LMCI",
                  "094_S_4486_F_69_EMCI","094_S_4560_F_70_CN","098_S_2071_M_85_EMCI",
                  "098_S_2079_M_66_EMCI","098_S_4002_F_74_CN","098_S_4059_M_72_EMCI",
                  "027_S_4729_LMCI_F_78","021_S_4633_LMCI_F_73","021_S_4402_LMCI_F_73",
                  "005_S_4168_EMCI_M_82","007_S_4272_EMCI_M_72","016_S_2031_EMCI_M_73",
                  "016_S_4097_CN_F_71","007_S_4516_CN_M_72","007_S_4488_CN_M_73",
                  "005_S_0610_CN_M_89","003_S_4872_CN_F_69","003_S_4840_CN_M_62",
                  "003_S_4839_CN_M_66","003_S_4555_CN_F_66","005_S_4707_M_68_AD",
                  "005_S_5119_F_77_AD","003_S_4142_F_90_AD","003_S_5165_M_79_AD",
                  "003_S_4152_M_61_AD","005_S_5038_M_82_AD","005_S_4910_F_82_AD",
                  "003_S_4136_M_67_AD","003_S_4892_F_75_AD"]

for subject_name in subject_folder:
    subject_folder_path = "registered_data"

    # Load registered labels
    registered_label_file_path = os.path.join(subject_folder_path, f'registered_label_image_{subject_name}.nii.gz')
    registered_label_img = nib.load(registered_label_file_path)
    registered_labels = registered_label_img.get_fdata()

    # Find coordinates corresponding to the registered labels
    label_coordinates = []
    roi_coordinates = []

    for label in roi_labels:
        label_coordinates_label = np.array(np.where(registered_labels == label)).T
        label_coordinates.append(label_coordinates_label)


    selected_coordinates = []
    valid_folder_path = "/content/drive/MyDrive/Ananya_Singhal_2010110087/ICIP - classification/41diff_coordinates"
    valid_coordinates_file_path = os.path.join(valid_folder_path, f'coordinates_{subject_name}.txt')
    valid_coordinates = np.loadtxt(valid_coordinates_file_path, delimiter=',')

    # KDTree for quick spatial lookup
    tree = KDTree(np.round(valid_coordinates), leaf_size = 2, metric = 'l2')

    # Select only those coordinates from the concatenated streams
    for label_coord in label_coordinates:
        if label_coord.shape[0] != 0:
            dist, indices = tree.query(label_coord, k=1)
            indices = indices[dist <= 4]
            valid = valid_coordinates[indices]
            selected_coordinates.append(valid)
            print(len(selected_coordinates))

    # Load diffusion tensor data
    ordered_folder_path = "ordered_DTI_4D_img_41diff_new21_subs"
    nii_gz_file = os.path.join(ordered_folder_path, f'ordered_4d_image_{subject_name}.nii.gz')
    data, affine, hardi_img = load_nifti(nii_gz_file, return_img=True)

    # Load common b-values and b-vectors
    common_bval_file = np.load('common_bval_file.npy')
    common_bvec_file = np.load('common_bvec_file.npy')

    gtab = gradient_table(common_bval_file, common_bvec_file)

    # Masking
    maskdata, mask = median_otsu(data, vol_idx=range(10, 46), median_radius=3, numpass=1, autocrop=False, dilate=2)

    # Tensor model fitting
    tenmodel = TensorModel(gtab)
    tenfit = tenmodel.fit(maskdata)

    # Calculate FA, MD, and AD scores for selected coordinates
    FA = []
    MD = []
    AD = []
    for s in selected_coordinates:
      selected_coordinates_indices = s.astype(float)
      selected_coordinates_indices = tuple(selected_coordinates_indices.T.astype(int).tolist())
      print(selected_coordinates_indices)
      selected_evals = tenfit.evals[selected_coordinates_indices]
      print(selected_coordinates_indices)
      FA.append(fractional_anisotropy(selected_evals))
      MD.append(mean_diffusivity(selected_evals))
      AD.append(axial_diffusivity(selected_evals))

    print(f'Processing and saving for {subject_name} complete.')


    folder1 = "FA_AD_MD"
    # Saving the FA in .npy file
    if not os.path.exists(folder1):
      os.makedirs(folder1)
    np.save(os.path.join(folder1, f'FA_{subject_name}.npy'), FA, allow_pickle = True)
    np.save(os.path.join(folder1, f'MD_{subject_name}.npy'), MD)
    np.save(os.path.join(folder1, f'AD_{subject_name}.npy'), AD)
