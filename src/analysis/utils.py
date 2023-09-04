''' Helper functions to compute connectivity matrices 

author: trianaa1
'''

import glob, os
import pandas as pd
import numpy as np
from scipy.io import savemat, loadmat
from scipy.spatial.distance import euclidean

import nibabel as nib
from nilearn.maskers import NiftiLabelsMasker

from sklearn.linear_model import LinearRegression


def list2mat(a):
    ''' converts lists of numpy arrays to formats that can be saved in 
    .mat files
    
    Parameters
    ----------
    a: list
    
    Returns
    -------
    b: numpy array
    '''
    
    b = np.empty((len(a),), dtype=object)
    for i in range(len(a)):
        b[i] = a[i]  
    return b


def compute_groupmasks(conn_path, fmriprep_path, task, vol_size, atlas_name):
    files = sorted(glob.glob(fmriprep_path + f'/**/func/*{task}_*mask.nii', recursive=True))
    
    group_mask_mult_name = f'{conn_path}/group_mask_mult.nii'
    group_mask_sum_name = f'{conn_path}/group_mask_sum95.nii'
    if not os.path.exists(group_mask_mult_name) or not os.path.exists(group_mask_sum_name):
        group_mask_mult = np.ones(vol_size)
        group_mask_sum = np.zeros(vol_size)
        for file in files:
            head, tail = os.path.split(file)
            subject = tail[0:6]
            if subject=='sub-09' and task =='resting':
                # sub-09 mask had a big cut in the frontal, superior part. Thus, the sub-09 was denoised with the PVT brain mask
                mask = nib.load(f'{fmriprep_path}/{subject}/func/{subject}_task-pvt_space-MNI152NLin6Asym_res-2_desc-brain_mask.nii')
            elif subject=='sub-25' and task =='nback':
                # sub-25 mask had a big cut in the superior part. Thus, the sub-25 was denoised with the resting brain mask
                mask = nib.load(f'{fmriprep_path}/{subject}/func/{subject}_task-resting_space-MNI152NLin6Asym_res-2_desc-brain_mask.nii')
            else:
                mask = nib.load(f'{fmriprep_path}/{subject}/func/{subject}_task-{task}_space-MNI152NLin6Asym_res-2_desc-brain_mask.nii')                
            
            data = mask.get_fdata()
            group_mask_mult = group_mask_mult*data
            group_mask_sum = group_mask_sum+data
        thr = np.amax(group_mask_sum)*0.95
        group_mask_sum[group_mask_sum<thr] = 0 #set values that are not in the 95% percentile of the mask to zero
        # i.e. if a voxel is in 95% of the cases, it stays
        group_mask_sum[group_mask_sum>0] = 1

        group_mask_nii = nib.Nifti1Image(group_mask_mult, mask.affine, mask.header)
        nib.save(group_mask_nii,group_mask_mult_name)
        group_mask_nii = nib.Nifti1Image(group_mask_sum, mask.affine, mask.header)
        nib.save(group_mask_nii,group_mask_sum_name)
        print(f'Group mask computed for {len(files)} files')
    
    #Multiply the group mask by the atlas
    if atlas_name=='seitzman-set1':
        atlas = '/m/cs/scratch/networks-pm/atlas/300_ROI_Set/seitzman_set1.nii'
    elif atlas_name=='seitzman-set2':
        atlas = '/m/cs/scratch/networks-pm/atlas/300_ROI_Set/seitzman_set2.nii'

    masked_atlas = f'{conn_path}/group_mask_{atlas_name}.nii'

    if not os.path.exists(masked_atlas):
        gmask = nib.load(group_mask_mult_name)
        gmask_data = gmask.get_fdata()
        atlas_nii = nib.load(atlas)
        atlas_data = atlas_nii.get_fdata()
        atlas_data = np.reshape(atlas_data, vol_size)

        atlas_mask = gmask_data*atlas_data
        atlas_mask_nii = nib.Nifti1Image(atlas_mask, atlas_nii.affine, atlas_nii.header)
        
        nib.save(atlas_mask_nii,masked_atlas)
        print(f'Masked {atlas_name} atlas with group mask')
    return masked_atlas

def compute_averagedROIts(nii_path, conn_path, task, strategy, group_atlas):
    ''' computes the averaged-ROI timeseries based on a selected atlas. The 
    computations are done for all subjects in a folder.
    
    Parameters
    ----------
    nii_path: folder path to where the denoised files are
    conn_path: folder path to where the computations will be stored
    strategy: denoised strategy
    group_atlas: file path to the group mask multiplied by the selected atlas.
                 It should be a nii file
    
    Returns
    -------
    roi_ts_file: string with the path to the file containing the averaged-ROI 
                 time series for all subjects
    '''
    
    files = sorted(glob.glob(nii_path + f'/**/*{task}_*{strategy}.nii', recursive=True))
    atlas_name = os.path.basename(group_atlas).split('_')[-1].split('.nii')[0]
    roi_ts_file = f'{conn_path}/{strategy}/averaged_roits_{strategy}_{atlas_name}.mat'
    
    masker = NiftiLabelsMasker(labels_img=group_atlas, standardize=True)
    
    if not os.path.exists(roi_ts_file):
        all_ts = []
        if not os.path.exists(roi_ts_file):
            for file in files:
                head, tail = os.path.split(file)
                print(f'Creating node time series for {file}')
                time_series = masker.fit_transform(file)
                all_ts.append(time_series)
            rs_ts = list2mat(all_ts)
            savemat(roi_ts_file, {'rs_ts':rs_ts})
    return roi_ts_file
    
def get_behav_data_movie(behav_path, lag):
    ''' selects the behavioral data for specific days before the scanner (lag). 
    In this case, only behavioral scores that are relaated to H4 in the 
    paper are selected. 
    
    Parameters
    ----------
    behav_path: folder path to where the behavioral data files are
    lag: number of days before the scanner to select
    
    Returns
    -------
    filtered_behav: DataFrame with the selected information
    '''
    sleep = pd.read_csv(os.path.join(behav_path, 'sub-01_day-all_device-oura.csv'))
    sleep = sleep[['date','Total Sleep Duration', 'Awake Time','Restless Sleep',
                  'Sleep Efficiency','Sleep Latency']] #as defined in the paper

    phys = pd.read_csv(os.path.join(behav_path, 'sub-01_day-all_device-embraceplus.csv'))
    phys = phys[['date','mean_respiratory_rate_brpm', 'min_respiratory_rate_brpm',
                     'max_respiratory_rate_brpm','median_respiratory_rate_brpm',
                     'std_respiratory_rate_brpm','mean_prv_rmssd_ms', 'min_prv_rmssd_ms', 
                     'max_prv_rmssd_ms','median_prv_rmssd_ms','std_prv_rmssd_ms']]

    mood = pd.read_csv(os.path.join(behav_path, 'sub-01_day-all_device-smartphone_sensor-ema.csv'))
    mood = mood[['date','pa_mean', 'pa_median', 'pa_min', 'pa_max', 'pa_std', 'na_mean',
               'na_median', 'na_min', 'na_max', 'na_std', 'stress_mean',
               'stress_median', 'stress_min', 'stress_max', 'stress_std', 'pain_mean',
               'pain_median', 'pain_min', 'pain_max', 'pain_std']]

    # unify the date format
    sleep['date'] = pd.to_datetime(sleep['date'], format='%d-%m-%Y')
    mood['date'] = pd.to_datetime(mood['date'], format='%Y-%m-%d')
    phys['date'] = pd.to_datetime(phys['date']).dt.tz_convert(None)  # Remove timezone information
    phys['date'] = phys['date'].dt.date  # Keep only the date part
    phys['date'] = pd.to_datetime(phys['date'], format='%Y-%m-%d')

    # merge dataframe
    behav = pd.merge(sleep, mood, on='date', how='outer')
    behav = pd.merge(behav, phys, on='date', how='outer')
        
    #fill in the nans with the mean 
    behav.fillna(round(behav.mean(numeric_only=True)), inplace=True)

    #select the days
    scan_days = pd.read_csv(os.path.join(f'{behav_path.rsplit("/", 2)[0]}/mri','sub-01_day-all_device-mri.csv'), header=0)
    scan_days = scan_days[['date']]
    scan_days['date'] = pd.to_datetime(scan_days['date'], format='%d/%m/%y')
    scan_days['date'] = scan_days['date'] - pd.Timedelta(days=lag)

    #select the days
    filtered_behav = behav[behav['date'].isin(scan_days['date'])]
    filtered_behav.drop(columns=['date'], inplace=True)
        
    return filtered_behav

def nearest_neighbors(data):
    ''' computes the simmilarity matrix in a matrix between pairs of observations
    based on the nearest neighbors model (Euclidean distance).
    
    Parameters
    ----------
    data: DataFrame (N_subjects x N_variables)
    lag: number of days before the scanner to select
    
    Returns
    -------
    nn_scaled: simmilarity matrix (n_sub x n_sub)
    '''
    n_sub = len(data)
    nn = np.zeros((n_sub, n_sub))
    for i in range(n_sub):
        for j in range(n_sub):
            if i < j:
                dist_ij = 1-(abs(euclidean(data.iloc[i,:].values, data.iloc[j,:].values))/n_sub)
                nn[i,j] = dist_ij
                nn[j,i] = dist_ij
    nn_scaled = (nn-np.min(nn))/(np.max(nn)-np.min(nn))
    return nn_scaled

def anna_karenina(data):
    ''' computes the simmilarity matrix in a matrix between pairs of observations
    based on the anna karenina model.
    
    Parameters
    ----------
    data: DataFrame (N_subjects x N_variables)
    lag: number of days before the scanner to select
    
    Returns
    -------
    ak_scaled: simmilarity matrix (n_sub x n_sub)
    '''
    n_sub = len(data)
    ak = np.zeros((n_sub, n_sub))
    for i in range(n_sub):
        for j in range(n_sub):
            if i < j:
                dist_ij = 1 - (abs(np.linalg.norm((data.iloc[i,:].values + data.iloc[j,:].values)/2))/n_sub) #calculate distance between i and j
                ak[i,j] = dist_ij
                ak[j,i] = dist_ij

    ak_scaled = (ak-np.min(ak))/(np.max(ak)-np.min(ak))
    np.fill_diagonal(ak_scaled, 1)
    return ak_scaled