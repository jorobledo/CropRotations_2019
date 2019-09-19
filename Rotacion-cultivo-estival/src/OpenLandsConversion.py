################################################################
# September 8, 2014
# OpenLandsConversion.py
# email: ritvik@umd.edu
#
#################################################################

# Google Python Style Guide
# function_name, local_var_name, ClassName, method_name, ExceptionName, 
# GLOBAL_CONSTANT_NAME, global_var_name, module_name, package_name,  
# instance_var_name, function_parameter_name

import os, time, pdb, operator, csv, glob, logging, shutil, arcpy, datetime, numpy, sys, pandas
from dbfpy import dbf
from arcpy.sa import *
from itertools import groupby

arcpy.CheckOutExtension("spatial")
arcpy.env.overwriteOutput= True
arcpy.env.extent         = "MAXOF"

# USER MODIFIED PARAMETERS #####################################################
START_YEAR  = 2008
END_YEAR    = 2012
METRIC      = 'LCC' # 'LCC','DI','PI'
TAG         = 'LakeStates_Snap_'+METRIC
################################################################################

date        = datetime.datetime.now().strftime("mon_%m_day_%d_%H_%M")#'mon_09_day_09_21_52'#
cdl_dir     = 'C:\\Users\\ritvik\\Documents\\PhD\\Projects\\CropIntensity\\input\\' # Contains input CDL files
base_dir    = 'C:\\Users\\ritvik\\Documents\\PhD\\Projects\\Lake_States\\'
inp_dir     = base_dir+'Code\\Python\\'
out_dir     = base_dir+'output'+os.sep+TAG+'_'+date+os.sep
lcc_dir     = base_dir+'Land_Capability_Classes\\GIS_Files\\'

# Directories of GIS input file 
pad_dir     = base_dir+'PAD_USA\\'
bound_dir   = base_dir+'State_Boundaries\\'
 
# CONSTANTS
CONVERSION  = 'conversion'
RECL        = 'recl'
BOUNDARIES  = bound_dir+'states.shp'
LCC_CSV     = lcc_dir+'48States.csv'
LCC_CR      = lcc_dir+'lcc_cr'
DI_PI_CSV   = lcc_dir+'US_Comp_20120429.csv'
DI_PI_CR    = lcc_dir+'di_pi_cr'

SSURGO_REMAP_FILE = lcc_dir+'recl.txt'
PI_REMAP_FILE = lcc_dir+'recl_PI.txt'
DI_REMAP_FILE = lcc_dir+'recl_DI.txt'  
CULTIVATED  = [499,501,502] # Corn: 499; Soybean: 501; Other crops: 502
CORN        = 499
SOY         = 501
OPEN        = 500
REGION      = ['LP','UP']
SET_SNAP    = True

# FILE NAMES
list_states = 'MI_MN_WI.txt'#'MI_MN_WI.txt'#'states_48.txt'
REMAP_FILE  = inp_dir+'recl.txt'

# First position: test.index(500)
# All positions: print [i for i, x in enumerate(test) if x == 500]
# number of occurences: [1, 2, 3, 4, 1, 4, 1].count(1)
###############################################################################
#
#
#
#
###############################################################################
def dbf_to_csv(file_name):
    if file_name.endswith('.dbf'):
        logger.info("Converting %s to csv" % file_name)
        
        csv_fn = file_name[:-4]+ ".csv"
        
        with open(csv_fn,'wb') as csvfile:
            in_db = dbf.Dbf(file_name)
            out_csv = csv.writer(csvfile)
            names = []
            for field in in_db.header.fields:
                names.append(field.name)
            out_csv.writerow(names)
            for rec in in_db:
                out_csv.writerow(rec.fieldData)
            in_db.close()
    else:
        logger.info("\tFilename does not end with .dbf")

    return csv_fn

###############################################################################
#
#
#
#
###############################################################################
def backup_source_code(out_dir):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    try:
        shutil.copy(os.path.realpath(__file__),out_dir)
    except:
        print "WARNING: could not save source code file"
        
###############################################################################
#
#
#
#
###############################################################################
def make_dir_if_missing(d):
    if not os.path.exists(d):
        os.makedirs(d)

###############################################################################
#
#
#
#
###############################################################################
def consecutive_cropping(row,crop_id):
    max_run = 0
    total_count = row.count(crop_id)
    
    if total_count:
        max_run = max(sum(1 for _ in g) for k, g in groupby(row) if k==crop_id)
    
    return max_run

###############################################################################
#
#
#
#
###############################################################################
def identify_monoculture(row):
    return len(set(row)) == 1

###############################################################################
#
#
#
#
###############################################################################
def number_yrs_after_open(row):    
    num_yrs = 0
    cult_yr = 0
    
    if(row.count(OPEN)):
        # Find the last year of open land
        last_yr = row[::-1].index(OPEN)
        
        # Determine the number of years of cultivation after that
        if(last_yr > 0):
            for j in CULTIVATED:
                cult_yr += row[-last_yr:].count(j)    
            
            if(cult_yr > 0):
                num_yrs  = last_yr
        
    return cult_yr, num_yrs

###############################################################################
#
#
#
#
###############################################################################
def any_cultivation(row):
    for j in CULTIVATED:
        if(j in row):
            return True
    
    return False

def output_raster_attribute_to_csv(reg,state,ras,replace):
    state_dir = out_dir+os.sep+state+os.sep
    out_csv   = state_dir+reg+'_'+state+'.csv'
    fields    = "*"
      
    if arcpy.Exists(out_csv) and not(replace):
        pass
    else:
        try:  
            lst_flds = arcpy.ListFields(ras)  
            header = ''  
            for fld in lst_flds:  
                header += "{0},".format(fld.name)  
            
            # Add region and state to header
            header +=  "{0},".format('REGION')
            header +=  "{0},".format('STATE')
            
            if len(lst_flds) != 0:    
                f = open(out_csv,'w')  
                  
                f.write(header+'\n')  
                with arcpy.da.SearchCursor(ras, fields) as cursor:  
                    for row in cursor:  
                        f.write(str(row).replace("(","").replace(")","")+','+reg+','+state+'\n')  
                f.close()
      
        except:  
            logger.info('\t '+ras+" - is not integer or has no attribute table")  

    return out_csv
    logger.info('\tOutputting csv for region '+reg+' in state '+state)
      
###############################################################################
#
#
#
#
###############################################################################
def join_csv(reg,state,ras,out_csv,replace):
    state_dir    = out_dir+os.sep+state+os.sep
    out_CR       = state_dir+state+'_cr'
    
    if not(replace):
        pass
    else:
        try:
            arcpy.CopyRows_management(out_csv,out_CR)        
            arcpy.BuildRasterAttributeTable_management(ras, "Overwrite")
            arcpy.JoinField_management(ras,"VALUE",out_CR,"VALUE","")
        except:
            logger.info(arcpy.GetMessages())
        
    logger.info('\tJoining region ' +reg+' for state '+state)
    return ras

###############################################################################
#
#
#
#
###############################################################################
def extract_by_mask(state,extract_comb,replace):
    state_dir = out_dir+os.sep+state+os.sep
    list_ras  = []
    for reg in REGION:
        ext_ras  = state_dir+reg+'_'+state+'_'+str(START_YEAR)[2:]+'_'+str(END_YEAR)[2:]
        vec_mask = base_dir+os.sep+'Lake States Outline'+os.sep+reg+'_'+'LakeStates.shp'
        list_ras.append(ext_ras)
        
        if arcpy.Exists(ext_ras) and not(replace):
            pass
        else:
            try:
                arcpy.gp.ExtractByMask_sa(extract_comb,vec_mask,ext_ras)                
            except:
                logger.info(arcpy.GetMessages())
        
        logger.info('\Extracting for '+reg+' in state '+state)
        
    return list_ras

###############################################################################
#
#
#
#
###############################################################################
def extract_LU_change(state,ras,replace):
    state_dir = out_dir+os.sep+state+os.sep
    ext_ras   = state_dir+'LU_'+state+'_'+str(START_YEAR)[2:]+'_'+str(END_YEAR)[2:]
    where     = CONVERSION+" > 0" 

    if arcpy.Exists(ext_ras) and not(replace):
        pass
    else:
        try:
            att_extract = ExtractByAttributes(ras,where) 
            att_extract.save(ext_ras)
        except:
            logger.info(arcpy.GetMessages())

    logger.info('\tRemove no LU pixels for state '+state)
    return ext_ras

###############################################################################
#
#
#
#
###############################################################################
def filter_and_project_raster(reg,state,ras,replace):    
    filtered_state =  out_dir+os.sep+state+os.sep+'f_'+reg+'_'+state+'_'+str(START_YEAR)[2:]+'_'+str(END_YEAR)[2:]

    if arcpy.Exists(filtered_state) and not(replace):
        pass
    else:
        try:
            out_set_null = SetNull(Lookup(RegionGroup(ras,"","","NO_LINK"),"count") == 1,extract_comb)
            out_set_null.save(filtered_state)
            
            # Reproject
            dsc = arcpy.Describe(ras)
            coord_sys = dsc.spatialReference
            arcpy.DefineProjection_management(filtered_state,coord_sys)
        except:
            logger.info(arcpy.GetMessages())
    
    logger.info('\t Filtering small pixels from state '+state)
    return filtered_state

###############################################################################
#
#
#
#
###############################################################################
def sieve(state,extract_comb):
    min_cells = 1
    filtered_state =  out_dir+os.sep+state+os.sep+'final_'+state
    
    tmp1 = RegionGroup(extract_comb, "FOUR", "WITHIN", "NO_LINK", "") 
    query = "VALUE > " + min_cells
    tmp2 = ExtractByAttributes(tmp1, query)
    
    out_raster = Nibble(extract_comb, tmp2)
    out_raster.save(filtered_state)

###############################################################################
#
#
#
#
###############################################################################
def filter_polygon(state,extract_comb):
    poly_1 = out_dir+os.sep+state+os.sep+'poly_1.shp'
    poly_2 = out_dir+os.sep+state+os.sep+'poly_2.shp'
    
    arcpy.RasterToPolygon_conversion(extract_comb, poly_1, "NO_SIMPLIFY", "VALUE")
    arcpy.CalculateAreas_stats(poly_1,poly_2)
 
###############################################################################
#
#
#
#
###############################################################################   
def identify_no_change_pixels(state,ras,replace):
    state_dir = out_dir+os.sep+state+os.sep
    out_csv   = state_dir+state+'_not_filtered.csv'
    
    if arcpy.Exists(out_csv) and not(replace):
        pass
    else:
        with open(out_csv,'wb') as f:
            w = csv.writer(f)

            try:
                arcpy.AddField_management(ras,CONVERSION,"LONG")
                arcpy.AddField_management(ras,'CULTIVATED',"LONG")
                arcpy.AddField_management(ras,'OPEN',"LONG")                
                arcpy.AddField_management(ras,'CORN',"LONG")
                arcpy.AddField_management(ras,'SOY',"LONG")
            except:
                logger.info(arcpy.GetMessages())                        
                            
            cursor = arcpy.UpdateCursor(ras)
            # Lets make a list of all of the fields in the table
            fields = arcpy.ListFields(ras)    
            field_names = [field.name for field in fields]
            # Write all field names to the output file
            w.writerow(field_names)
                        
            for row in cursor:
                land_use_trend = []
                for j in range(START_YEAR, END_YEAR+1):            
                    land_use_trend.append(row.getValue('RECL_'+state.upper()+'_'+str(j)))
                if(identify_monoculture(land_use_trend)):
                    pass
                elif(not(any_cultivation(land_use_trend))):
                    pass
                else:
                    row.setValue(CONVERSION,1)
                    cursor.updateRow(row)

                num_consecutive_corn = consecutive_cropping(land_use_trend,CORN)
                num_consecutive_soy  = consecutive_cropping(land_use_trend,SOY)
                cult_yr, num_yrs     = number_yrs_after_open(land_use_trend)
                
                row.setValue('CULTIVATED',cult_yr)
                cursor.updateRow(row)
                row.setValue('OPEN',num_yrs)
                cursor.updateRow(row)
                                
                if(num_consecutive_corn):
                    row.setValue('CORN',num_consecutive_corn)
                    cursor.updateRow(row)
                if(num_consecutive_soy):
                    row.setValue('SOY',num_consecutive_soy)
                    cursor.updateRow(row)
                
                field_vals = [row.getValue(field.name) for field in fields]
                w.writerow(field_vals)
                
                row = cursor.next()
    
    #arcpy.ExportXYv_stats(ras,names_att_table, "COMMAdir+state+'.csv',"ADD_FIELD_NAMES")

    logger.info('\tIdentifying monoculture and no cultivation pixels in state '+state)
    return out_csv

###############################################################################
#
#
#
#
###############################################################################
def erase_PAD(state,ras,replace):
    # Process: Erase
    
    pad_state     = pad_dir+'PAD-US_'+state+'\\PADUS1_3_'+state+'.gdb\\PADUS1_3'+state    
    pad_out_dir   = pad_dir+'output\\'+state+os.sep
    bound_out_dir = bound_dir+'output\\'+state+os.sep
    state_dir     = out_dir+os.sep+state+os.sep
    
    make_dir_if_missing(pad_out_dir)
    make_dir_if_missing(bound_out_dir)
    make_dir_if_missing(state_dir)

    select_state  = bound_out_dir+state+'.shp'
    erased_pad    = pad_out_dir+state+'.shp'
    extract_comb  = state_dir+'ext_'+state+'_'+str(START_YEAR)[2:]+'_'+str(END_YEAR)[2:]

    #
    if arcpy.Exists(select_state) and not(replace):
        pass
    else:
        where = '"STATE_ABBR" = ' + "'%s'" %state.upper()
        try:
            arcpy.Select_analysis(BOUNDARIES,select_state,where)
        except:
            logger.info(arcpy.GetMessages())

    #
    if arcpy.Exists(erased_pad) and not(replace):
        pass
    else:
        try:
            arcpy.Erase_analysis(select_state,pad_state,erased_pad, "")
        except:
            logger.info(arcpy.GetMessages())

    #
    if arcpy.Exists(extract_comb) and not(replace):
        pass
    else:
        try:
            # Create bounding box from polygon (xmin, ymin, xmax, ymax)
            #desc = arcpy.Describe(erased_pad)
            #rectangle = "%s %s %s %s" % (desc.extent.XMin, desc.extent.YMin, desc.extent.XMax,   desc.extent.YMax)
            
            #arcpy.Clip_management(ras,rectangle,extract_comb,erased_pad,"#","ClippingGeometry")
            arcpy.gp.ExtractByMask_sa(ras,erased_pad,extract_comb)
        except:
            logger.info(arcpy.GetMessages())

    logger.info('\t Erasing PAD from state '+state)
    return extract_comb

###############################################################################
# reclassify_and_combine
#
#
#
###############################################################################
def reclassify_and_combine(state,state_lcc,state_cdl_files,replace):
    to_comb_rasters = []
      
    # Create output directory for each state
    state_dir  = out_dir+os.sep+state+os.sep
    make_dir_if_missing(state_dir)

    # Reclass for each year
    for j in range(len(range_of_yrs)):
        recl_raster = state_dir+RECL+'_'+state+'_'+str(range_of_yrs[j])
        
        if arcpy.Exists(recl_raster) and not(replace):            
            pass
        else:
            try:
                out_reclass = ReclassByASCIIFile(state_cdl_files[j],REMAP_FILE,"NODATA")        
                out_reclass.save(recl_raster)
            except:
                logger.info(arcpy.GetMessages())
        
        logger.info('\tReclassified...'+recl_raster)
        to_comb_rasters.append(recl_raster)

    to_comb_rasters.append(state_lcc)
    
    # Combine all input rasters
    comb_raster = state_dir+os.sep+'comb_'+state+'_'+str(range_of_yrs[0])[2:]+'_'+str(range_of_yrs[len(range_of_yrs)-1])[2:]
      
    if arcpy.Exists(comb_raster) and not(replace):
        pass
    else:     
        try:   
            out_combine = Combine(to_comb_rasters)
            out_combine.save(comb_raster)
        except:
            logger.info(arcpy.GetMessages())
        
    logger.info('\tCombined...'+comb_raster)
    return comb_raster

###############################################################################
#
#
#
#
############################################################################### 
def create_state_ssurgo(state,replace):    
    state_lcc_dir  = lcc_dir+state+os.sep
    
    state_ssurgo = state_lcc_dir+state+'ssurgo'
    lu_ssurgo    = state_lcc_dir+state+'_lu_ssurgo'    
    out_state_sgo  = state_lcc_dir+state+'_sgo_'+METRIC.lower()
    
    # Join with LCC csv
    if arcpy.Exists(out_state_sgo) and not(replace):
        pass
    else:
        arcpy.BuildRasterAttributeTable_management(state_ssurgo, "Overwrite")

        try:
            if(METRIC=='LCC'):
                arcpy.JoinField_management (state_ssurgo,"VALUE",LCC_CR,"mukey","")
            else: # DI or PI            
                arcpy.JoinField_management (state_ssurgo,"VALUE",DI_PI_CR,"mukey","")                
        except:
            logger.info(arcpy.GetMessages())
            
        # Lookup to create new raster with new VALUE field
        # Execute Lookup
        lup_column = ''
        remap_file = ''
        
        if(METRIC=='LCC'):
            lup_column = 'NICCDCD'
            remap_file = SSURGO_REMAP_FILE
        elif(METRIC=='PI'):
            lup_column = 'PI'
            remap_file = PI_REMAP_FILE
        elif(METRIC=='DI'):
            lup_column = 'DI'
            remap_file = DI_REMAP_FILE
                        
        lu_tmp = Lookup(state_ssurgo,lup_column)        
        # Save the output 
        lu_tmp.save(lu_ssurgo)
        
        # Reclass raster to group LCC values into 3 classes: 
        # Productive, Moderate and Marginal
        out_reclass = ReclassByASCIIFile(lu_ssurgo,remap_file,"NODATA")        
        out_reclass.save(out_state_sgo)
    
    logger.info('\t SSURGO state '+state)
    return out_state_sgo

###############################################################################
#
#
#
#
###############################################################################    
def merge_csv_files(list_csv_files,fname):
    write_file = out_dir+fname+'.csv'
     
    with open(write_file,'w+b') as append_file:
        need_headers = True
        for input_file in list_csv_files:
            with open(input_file,'rU') as read_file:
                headers = read_file.readline()
                if need_headers:
                    # Write the headers only if we need them
                    append_file.write(headers)
                    need_headers = False
                # Now write the rest of the input file.
                for line in read_file:
                    append_file.write(line)
    logger.info('Appended CSV files')
    return write_file
    
###############################################################################
# main
#
#
#
###############################################################################   
if __name__ == "__main__":
    # make output dir
    make_dir_if_missing(out_dir)

    # Read in all state names
    lines = open(inp_dir+os.sep+list_states, 'rb').readlines()
    
    range_of_yrs = []
    for i in range(END_YEAR-START_YEAR+1):
        range_of_yrs.append(START_YEAR+i)
    
    for subdir, dir_list, files in os.walk(cdl_dir):
            break        
    
    # Logger
    LOG_FILENAME   = out_dir+os.sep+'Log_'+TAG+'_'+date+'.txt'
    logging.basicConfig(filename = LOG_FILENAME, level=logging.DEBUG,\
                        format='%(asctime)s    %(levelname)s %(module)s - %(funcName)s: %(message)s',\
                        datefmt="%Y-%m-%d %H:%M:%S") # Logging levels are DEBUG, IN    FO, WARNING, ERROR, and CRITICAL
    logger = logging

    # Backup source code
    backup_source_code(out_dir)
    
    # Convert LCC_CSV into copy rows file
    try:
        arcpy.CopyRows_management(LCC_CSV,LCC_CR,"")
        arcpy.CopyRows_management(DI_PI_CSV,DI_PI_CR,"")       
    except:
        logger.info(arcpy.GetMessages())
            
    # Loop across all states   
    list_csv_files = []
    list_filt_ras  = [] 
    list_dbf_csv   = []
    for line in lines:
        state_cdl_files = []
        # Find out state name    
        state = line.split()[0]
        logger.info(state)
        
        # Collect all CDL files for state within given year range     
        for j in range(len(range_of_yrs)):
            for position, item in enumerate(dir_list):
                if (str(range_of_yrs[j]) in item):
                    cdl_file = glob.glob(cdl_dir+os.sep+dir_list[position]+os.sep+state+os.sep+'*_'+state+'_*'+str(range_of_yrs[j])+'*.tif')
                    if cdl_file:                    
                        state_cdl_files.append(''.join(cdl_file))
                    else:
                        logger.info(cdl_file + 'not found!')
                        sys.exit(0)
        
        # Set snap extent
        if(SET_SNAP):
            arcpy.env.snapRaster     = state_cdl_files[0]
            SET_SNAP                 = False
            logger.info('\tSet snap extent')
        # 0. Create SSURGO file
        state_sgo     = create_state_ssurgo(state,True)

        # 1. Combine CDL (START_YEAR ... END_YEAR) + SSURGO    
        comb_raster   = reclassify_and_combine(state,state_sgo,state_cdl_files,True)

        # 2. Add field indicating land-use conversion and corn/soy cropping
        out_csv       = identify_no_change_pixels(state,comb_raster,True)
        
        # 3. Remove non LU change pixels from raster
        LU_change_ras = extract_LU_change(state,comb_raster,True)        

        # 4. Erase the PAD
        extract_comb  = erase_PAD(state,LU_change_ras,True)

        # 5. Extract by regional mask
        extract_mask  = extract_by_mask(state,extract_comb,True)
                        
        reg_indx = 0
        state_csv_files = []
        state_filt_ras  = [] 
        for ras in extract_mask:
            reg = REGION[reg_indx]
            
            # 6. Remove small pixels
            filtered_ras = filter_and_project_raster(reg,state,ras,True)
                
            # 7. Join back the csv
            join_csv(reg,state,filtered_ras,out_csv,True)
            list_filt_ras.append(filtered_ras)
            state_filt_ras.append(filtered_ras)
        
            # 8. Join back the csv
            out_csv_file = output_raster_attribute_to_csv(reg,state,filtered_ras,True)
            list_csv_files.append(out_csv_file)
            state_csv_files.append(out_csv_file)
            reg_indx += 1    
        
        # Merge state csv files
        state_csv = merge_csv_files(state_csv_files,'append_'+state+'_'+TAG+'_'+date)
        df   = pandas.DataFrame.from_csv(state_csv,index_col=False)
        cols = [col for col in df.columns if col not in ['REGION','COUNT','Rowid']]
        df2  = df[cols].drop_duplicates()
        gr = df.groupby('VALUE').aggregate({'COUNT':numpy.sum},as_index=False)#.to_csv(out_dir+'qzzz.csv')
        gr['VALUE'] = gr.index
        gr  = gr.merge(df2,how='right',on='VALUE')
        gr.to_csv(out_dir+state+'_'+TAG+'.csv')
        
        try:
            out_CR   = out_dir+os.sep+'out_cr'
            merg_ras = state+"_merge_"+METRIC
            
            # Combine all filtered rasters
            arcpy.MosaicToNewRaster_management(";".join(state_filt_ras),out_dir,merg_ras,"","32_BIT_SIGNED","","1","LAST","FIRST")
            arcpy.BuildRasterAttributeTable_management(out_dir+merg_ras, "Overwrite")
            logger.info('Mosaiced... '+out_dir+merg_ras)
            
            # Zonal stat
            in_zone_data = base_dir+'UScounties\\LakeStateCounty.shp'        
            out_zsat     = ZonalStatisticsAsTable(in_zone_data,'FIPS',out_dir+merg_ras,out_dir+state+'_zsat.dbf', "DATA", "SUM")
            logger.info('Zonal stat... '+out_dir+merg_ras)   
            
            out_zonal_statistics = ZonalStatistics(in_zone_data,'FIPS',out_dir+merg_ras,"SUM","DATA")
            # Save the output 
            out_zonal_statistics.save(out_dir+state+'_zsat')         
            fl = dbf_to_csv(out_dir+state+'_zsat.dbf')
            list_dbf_csv.append(fl)
        except:
            logger.info(arcpy.GetMessages())
    
    merge_csv_files(list_dbf_csv,'Zonal_'+TAG)    
    logger.info('Done!')
    
