%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% This script applies the drifter from (Sarkka et. al., 2012) to clean the %
% nii signal from heart and respiration rates. It also cleans physiological%
% signals and downamples them to the number of TRs.                        % 
%                                                                          %
% Sarkka, S., Solin, A., Nummenmaa, A., Vehtari, A., Auranen, T.,          %  
% Vanni, S., and Lin, F.-H. (2012). Dynamical retrospective filtering of   %
% physiological noise in BOLD fMRI: DRIFTER. NeuroImage, 60:1517?1527.     %
%                                                                          %
%Author: ana.trianahoyos@aalto.fi                                          %
%created: 02.03.2021                                                       %
%modified 11.03.2021                                                       % 
%modified 07.09.2021 include more structured naming of files               %
%modified 31.01.2023 adapt to the PM experiment                            %
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


clear all
close all
clc

addpath(genpath('/m/cs/scratch/networks-pm/software/bramila'));
addpath('/m/cs/scratch/networks-pm/software/NIFTI');

path = '/m/cs/project/networks-pm/mri/fast_prepro_bids';
sub = 'sub-07';
tasks = {'pvt', 'resting', 'movie', 'nback'};
TR=0.594;

for idx=1:length(tasks)
    task = tasks{idx};
    disp(task)
    
    filepath = sprintf('%s/%s/func/%s_task-%s_device-biopac.mat',path,sub,sub,task);
    
    niifile = sprintf('%s/%s/func/%s_task-%s_bold.nii',path,sub,sub,task);
    savefile = sprintf('%s/%s/func/%s_task-%s_device-biopac_downsampled.mat',path,sub,sub,task);
    
    datafile = sprintf('%s/%s/func/%s_task-%s_device-biopac_data.mat',path,sub,sub,task);
    reffile = sprintf('%s/%s/func/%s_task-%s_device-biopac_refdata.mat',path,sub,sub,task);
        
    %Load BIOPAC data
    hr = load(filepath);
    b =hr.b;
    disp('BIOPAC file loaded')
    
    %Load NII data
    nii=load_untouch_nii(niifile);
    disp('NII data loaded')
    
    %construct the data structure
    data.data=double(nii.img);
    data.dt=TR;
    data.mode=0; % 0 = BOLD estimate only, 1 = BOLD+residual added back, -1 return all components
    disp('data structure done!')
    
    %Building the refdata structure
            
    % sampling interval of physiodata and fMRI (these were taken from Bramila).
    biopacfile.dt=0.0005;%0.001; % in seconds/sample (0.0005 taken from the original mat file, isi field).
    biopacfile.breath=0.01;%new sampling interval for breath it should not be higher than 2.4( for 25 inhales/min)
    biopacfile.HR=0.01; %new sampling interval for heart rate, should not be higher than 0.75(for 80 bpm)
    % set the range for frequencies in signals in bpm (try to keep those as narrow as posible)
    biopacfile.freqBreath=10:25; % in breaths per min
    biopacfile.freqHR=40:110; % in beats per minutes
    biopacfile.filter=1; % bandpass filter for reference data 1 - active, 0 - not active
        
    if biopacfile.filter == 1
            refdata{1}.filter = 1 ;
            refdata{2}.filter = 1 ;
    else
            refdata{1}.filter = 0 ;
            refdata{2}.filter = 0 ;
    end    
        
    refdata{1}.data = b(:,1);
    refdata{2}.data = b(:,4);
    refdata{1}.downdt=biopacfile.breath; 
    refdata{2}.downdt=biopacfile.HR;
    refdata{1}.freqlist=biopacfile.freqBreath;
    refdata{2}.freqlist=biopacfile.freqHR;	
    refdata{1}.name=sprintf('%s/BR_1',path);
    refdata{2}.name=sprintf('%s/HR_2',path);
    refdata{1}.outfolder=path;
    refdata{2}.outfolder=path;
    refdata{1}.dt=biopacfile.dt;
    refdata{2}.dt=biopacfile.dt;
    disp('refdata structure done!')
    
    [data,refdata]=drifter(data, refdata);
    disp('drifter completed! Saving files...')
    
    movefile(sprintf('%s/BR_1_filter.jpg', path), sprintf('%s/%s/func/%s_task-%s_BR_1_filter.jpg',path,sub,sub,task));
    movefile(sprintf('%s/HR_2_filter.jpg', path), sprintf('%s/%s/func/%s_task-%s_HR_2_filter.jpg',path,sub,sub,task));
    source = dir(sprintf('%s/*.jpg', path));
    movefile(sprintf('%s/%s', path, source.name), sprintf('%s/%s/func/%s_task-%s_%s.jpg',path,sub,sub,task,source.name));
    
    save(datafile, 'data','-v7.3');
    save(reffile, 'refdata');
    
    for j=1:length(refdata)
        downsampled_tr(j,:) = refdata{j}.FF;
    end
    
    save(savefile, 'downsampled_tr');
    
    disp('files saved')
    
    clear downsampled_tr
    clear data
    clear refdata
end
