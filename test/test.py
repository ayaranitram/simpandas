
# import log2frame  # unused in tests
import pandas as pd
import simpandas as spd
import seaborn as sns
import matplotlib.pyplot as plt

sample_prod = spd.read_excel('../test/_testing_data/sample_prod.xlsx')
sample_prod[['WOPR:P1']]
sample_prod['2100-02-26', 'WBHP:P1']


# pressure_folder = r'\\nas.home\documentos\_DocumentosTecnicos\datasets\volve\Well_logs\03.PRESSURE'
# volve_rft = log2frame.rft_summaries_from_folders(pressure_folder)
# volve_rft = volve_rft.loc[~volve_rft.SUCCESS.isna()]
# volve_rft.index = pd.MultiIndex.from_tuples([(w.replace('_', '/'), i) for w, i in volve_rft.index])
# 
# manual = pd.read_excel('//nas.home/documentos/_DocumentosTecnicos/datasets/manual_labels.xlsx')
# manual.rename(columns={'Unnamed: 1': 'FILE'}, inplace=True)
# manual['WELL'] = manual['WELL_NAME']
# manual.drop(columns='Unnamed: 0', inplace=True)
# manual.set_index(['WELL_NAME', 'FILE'], inplace=True)
# manual['SUCCESS'] = manual['SUCCESS'].astype(bool)
# 
# volve_rft = pd.concat([volve_rft, manual])
# volve_rft = volve_rft.loc[~volve_rft.SUCCESS.isna()]
# volve_rft = volve_rft.drop_duplicates(subset=['WELL', 'DEPTH', 'SUCCESS'])
# 
# pressure_folder = '//nas.home/documentos/_DocumentosTecnicos/datasets/northernlights/08.Formation_Pressure_Data'
# northernlights_rft = log2frame.rft_summary(pressure_folder)
# northernlights_rft = northernlights_rft.loc[~northernlights_rft['DEPTH'].isna()]
# northernlights_xpt_mdt = pd.read_excel('//nas.home/documentos/_DocumentosTecnicos/datasets/northernlights_xpt_mdt_summary_table.xlsx')
# northernlights_rft = northernlights_rft.drop(columns=['SUCCESS', 'PRESSURE RAW DATA', 'data', 'WELL']).merge(
#     northernlights_xpt_mdt[['DEPTH', 'WELL', 'SUCCESS']], on='DEPTH', how='outer')
# northernlights_rft.index = pd.MultiIndex.from_tuples([(northernlights_rft['WELLBORE'].iloc[i], i) for i in northernlights_rft.index])
# northernlights_rft = northernlights_rft.loc[~northernlights_rft['SUCCESS'].isna()]
# 
# 
# rft_labels = pd.concat([volve_rft, northernlights_rft])
# rft_labels2 = spd.SimDataFrame(rft_labels, units={'DEPTH': 'm'})

