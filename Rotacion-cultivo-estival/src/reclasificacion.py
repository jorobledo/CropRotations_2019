import os, time, pdb, operator, csv, glob, logging, shutil, arcpy, datetime, numpy
from arcpy import env
from arcpy.sa import *

#Prueba la licencia de arcgis
arcpy.CheckOutExtension("spatial")
arcpy.env.overwriteOutput= True
arcpy.env.extent         = "MAXOF"

base_dir           = 'C:\\Users\\jo_ro\\Google Drive\\Maestria en Estadistica\\ArcGIS\\Antonio\\Rotacion-cultivo-estival'
inp_dir            = base_dir+os.sep+'entrada' # ubicacion de los archivos de entrada
analysis_dir       = base_dir+os.sep+'src' # ubicacion de los archivos iniciales

yrs_in_rot = 8
curr_yr = 2010


for i in range(yrs_in_rot):
    if i>0 :
        curr_yr += 1
    comb_rasters = inp_dir+os.sep+str(curr_yr)+os.sep+'e_'+str(curr_yr-2000)
    print(curr_yr, comb_rasters)
    rot_data = inp_dir+os.sep+str(curr_yr)+os.sep+str(curr_yr)+'_reclasificado.tif'
    out_reclass = ReclassByTable(comb_rasters, analysis_dir+os.sep+'reclass_'+str(curr_yr)+'.csv', "FROM", "TO", "VALUE", "DATA")
    out_reclass.save(rot_data)
