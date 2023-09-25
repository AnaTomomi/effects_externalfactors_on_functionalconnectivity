clear all
close all
clc

path = '/m/cs/scratch/networks-pm/effects_externalfactors_on_functionalconnectivity/results/H3';
strategy = '24HMP-8Phys-Spike_HPF';
atlas_name = 'seitzman-set1';
to_correct = 'reg-links'; %'reg-links' or 'parti-coeff'

filepath = sprintf('%s/%s_%s_%s.csv', path, to_correct, strategy, atlas_name);
data = readtable(filepath);

data = data(~contains(data.Var1, 'Intercept'), :); % Filter out the intercept
data = data(:,[1,3,8]); %select only the needed columns
data.Var1 = regexprep(data.Var1, '\d+$', ''); %set the same variable names for all
totest = unstack(data, 'p_values','Var1'); % Pivot the table

%Start the multiple comparison correction
data_BH = totest;
data_fdr = totest;
colNamesToIterate = totest.Properties.VariableNames(2:end);
for colName = colNamesToIterate
    pvals = totest.(colName{1});
    if max(pvals)>1
        fprintf('%s pval over 1', colName{1})
    end
    qvals_bh =  mafdr(pvals, 'BHFDR', 'True');
    qvals = mafdr(pvals);

    if any(qvals_bh<0.05)
        fprintf('result for %s \n',colName{1})
    end

    qvals_bh(qvals_bh > 0.05) = 0;
    qvals(qvals > 0.05) = 0;
    data_BH.(colName{1}) = qvals_bh;
    data_fdr.(colName{1}) = qvals;
end

writetable(data_BH, sprintf('%s/%s_%s_%s_BHcorrected.xlsx', path, to_correct, strategy, atlas_name))
writetable(data_fdr, sprintf('%s/%s_%s_%s_FDRcorrected.xlsx', path, to_correct, strategy, atlas_name))