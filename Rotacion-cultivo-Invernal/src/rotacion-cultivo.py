################################################################
# Enero 2019
# rotacion-cultivo
# email: jorobledo@unc.edu.ar
# Codigo para Antonio Aoki
# Produce la rotacion de cultivo en la region de interes.
#################################################################
# Importa los modulos necesarios de python
import os, time, pdb, operator, csv, glob, logging, shutil, arcpy, datetime, numpy
from arcpy import env
from arcpy.sa import *

#Prueba la licencia de arcgis
arcpy.CheckOutExtension("spatial")
arcpy.env.overwriteOutput= True
arcpy.env.extent         = "MAXOF"

#Algunas definiciones necesarias para los archivos.
RAS                      = 'ras_'
OUT_RAS                  = 'OUT_RAS_'
COMB                     = 'comb_'
YRS                      = 'yrs'
FRST                     = 'frst_'
ROT_FRST_GRASS           = 'rfg_'
ROT_FRST_GRASS_URB       = 'all_'
CDL_ROT                  = 'cdl_rot_'
ROT                      = 'rot_'
HIGH                     = 'high_'
STATS                    = 'resultados_cba'
BASE_YR_WOUT_URBAN       = 'wout_urb_'
PRODUCT                  = 'product_'
EXPR_FILE                = 'EXPR_FILE'
CDL_VAL_NAME_MAP         = 'mapa_de_categorias.csv'
m2_to_ha                 = 0.0001
rasters_to_delete        = []
csv_files_to_delete      = []
#######################################################################

base_dir           = 'C:\\Users\\jo_ro\\Google Drive\\Maestria en Estadistica\\ArcGIS\\Antonio\\Rotacion-cultivo-Invernal'
inp_dir            = base_dir+os.sep+'entrada' # ubicacion de los archivos de entrada
analysis_dir       = base_dir+os.sep+'src' # ubicacion de los archivos iniciales
MIN_ID             = 300 # El numero minimo de identificador para las rotaciones.
USE_EXISTING_DATA  = False
EXISTING_ROTATIONS = 'rotaciones_existentes.csv' #Archivo con los identificadores de las secuencias generadas
list_states            = 'lista_de_regiones.txt' #Archivo con las regiones que se desean estudiar
delete_rasters         = False  # eliminar los archvos rasters auxiliares temporales
delete_csv_files       = False  # eliminar los archivos csv auxiliares
append_for_grs_urb     = False # que tenga en cuenta la parte de bosques y pastos
bool_merge_ras_files   = False # unir todos los rasters de una misma region
prev_first_yr          = 2011  # primer año
first_yr               = 2011  # primer año
last_yr                = 2017  #utimo año
base_yr                = 2017  #copiar ultimo año
list_min_area_rot      = [0.999] #entre 0 y 1. Puede tomar mas de un valor [0.4,0.1]
list_min_perc_of_rot   = [0] #entre 0 y 1. Tambien puede tomar mas de un valor
# 'E_' o 'I_'
ident = 'i_'


remove_urban_and_wtlnd = False #Cambiar a True si se quiere remover las categorias que estan en el archivo ciudades.txt

GRASSLANDS               = 'pastos.txt'
FORESTS                  = 'bosques.txt'
CROPS                    = 'cultivos.txt'
URBAN_WETLANDS           = 'ciudades.txt'

################################################################################
#ACA EN ADELANTE  NO ES NECESARIO TOCAR NADA!!!!
################################################################################

#Las funciones convert y sort_csv se sacaron de:
#http://stackoverflow.com/questions/2089036/sorting-csv-in-python
#sort_csv precisa de la funcion convert para funcionar.
def convert(types, values):
    return [t(v) for t, v in zip(types, values)]
def sort_csv(csv_filename, types, sort_key_columns):
    """sort (and rewrite) a csv file.
    types:  data types (conversion functions) for each column in the file
    sort_key_columns: column numbers of columns to sort by"""
    data = []
    f = open(csv_filename, 'r')
    for row in csv.reader(f):
        data.append(convert(types, row))
    data.sort(key=operator.itemgetter(sort_key_columns))
    f = open(csv_filename, 'w')
    csv.writer(f).writerow(['FROM', 'TO', 'VALUE'])
    csv.writer(f).writerows(data)

def is_nonag(a):
    gr_file = open(analysis_dir+os.sep+GRASSLANDS, 'r')
    lines = gr_file.readlines()

    for line in lines:
        if(line.split()[0] == a):
            return True

    fr_file = open(analysis_dir+os.sep+FORESTS, 'r')
    lines = fr_file.readlines()

    for line in lines:
        if(line.split()[0] == a):
            return True

    uw_file = open(analysis_dir+os.sep+URBAN_WETLANDS, 'r')
    lines = uw_file.readlines()

    for line in lines:
        if(line.split()[0] == a):
            return True

# Returns the number of string positions that are different in two crop rotations a and b
# E.g. a = [1, 2, 3, 5]; b = [2, 4, 3, 5] differ in 2 positions (1st and 2nd)
def lev(a, b):
        cnt = 0
        for i in range(len(a)):
                if(a[i] != b[i]):
                   cnt = cnt + 1
        return cnt

###############################################################################
# Reads a file containing list of pairs of CDL id's and their names. Returns list of CDL IDs
# @param file_name: name of file to read
# @return: a string containing a list of land uses in file_name
###############################################################################
def writeCDLData(cdl_comb, fileName):
        fileHandle = open(fileName, 'w')
        for i in range(len(cdl_comb)):
                for j in range(len(cdl_comb[i])):
                    fileHandle.write(str(cdl_comb[i][j]))
                    if (j < len(cdl_comb[i])-1):
                        fileHandle.write(', ')
                    else:
                        fileHandle.write('\n')
        fileHandle.close()

###############################################################################
# Reads a file containing list of pairs of CDL id's and their names. Returns list of CDL IDs
# @param file_name: name of file to read
# @return: a string containing a list of land uses in file_name
###############################################################################
def returnLandUses(file_name):
    cdl_file = open(file_name, 'r')
    lines = cdl_file.readlines()
    elem = []
    for line in lines:
        elem.append(line.split()[0])
    #print(file_name,elem)
    cdl_file_str = ""
    val = "\"Value\" = "

    # cdl_file_str is of the form "Value = 1 OR Value = 2 ... "
    for i in range(len(elem)):
        cdl_file_str+=(val)
        cdl_file_str+=elem[i]
        if i < len(elem)-1:
            cdl_file_str+=" OR "

    return cdl_file_str

###############################################################################
# Writes a reclassfication file that can be used in ArcGIS for 'ReclassByFile'
# @param file_hndl: name of reclass file to write
# @param from_str: 'from' parameter in reclass
# @param to_str: 'to' parameter in reclass
# @return: Nothing
###############################################################################
def writeReClassFile(file_hndl, from_str, value_str):
    # Assume that the to_str is the same as from_str
    file_hndl.write(str(from_str)+','+str(from_str)+','+str(value_str)+'\n')

###############################################################################
# Given a rotation spanning from 2008 to 2010, this function can create a
# rotation spanning from 2007 to 2010 by copying over 2010 year CDL info to 2007
# @param vec: crop rotation e.g. corn, soybean, corn, soybean
# @param yrs_in_rot: number of years in crop rotation e.g. it is 4 for 2008 to 2011
# @param first_yr: start of crop rotation year
# @param prev_first_yr: year from which we want crop rotation to start
# @return: the synchronized vector starting from prev_first_yr
###############################################################################
def synchronizeRotation(vec, yrs_in_rot, num_rot, first_yr, prev_first_yr):
    new_vec = []
    count = 0
    if(first_yr != prev_first_yr):
        for j in range(prev_first_yr, first_yr):
            new_vec.append(vec[yrs_in_rot-(first_yr-prev_first_yr)+count])
            count += 1

        for i in range(num_rot - (first_yr-prev_first_yr)):
                new_vec.append(vec[i])
        #new_vec.append(vec[:(yrs_in_rot - (first_yr-prev_first_yr))])
    else:
        new_vec = vec

    return new_vec

def delete_interim_files():
    print('Deleting...')
    # Delete the raster files
    if(delete_rasters):
        for i in range(len(rasters_to_delete)):
            logger.info('Deleting raster '+os.path.split(rasters_to_delete[i])[1])
            if delete_rasters:
                try:
                    arcpy.Delete_management(rasters_to_delete[i], "")
                except:
                    logger.info(arcpy.GetMessages())

    # Delete the csv files
    if(delete_csv_files):
        for k in range(len(csv_files_to_delete)):
            os.remove(csv_files_to_delete[k])

def combineCDLs(comb_rasters, yrs_in_rot, state):
    cdl_comb = []
    # For each line of the attribute table in the comb_rasters file, determine the appropriate crop rotation
    try:
        rows       = arcpy.SearchCursor(comb_rasters)
    except:
        logging.info(arcpy.GetMessages())
    row        = rows.next()
    while row != None:
        cdl_info_for_pixel = []
        for i in range(yrs_in_rot):
            #print('OUT_RAS+\'C\'+str(i+1) es:', OUT_RAS+'C'+str(i+1))
            cdl_info_for_pixel.append(row.getValue(OUT_RAS+'C'+str(i+1)))

        # Create a tuple containing cdlInfoForPixel and the number of pixels with that crop rotation type
        cdl_list = list(cdl_info_for_pixel)
        cdl_list.append(row.COUNT)
        # A '1' in the right most column(USED bit) indicates that the crop rotation will be used.In subsequent simplifications,
        # most of the 1's will be turned to 0's
        # E.g. cdlInfoForPixel can look like: 1, 5, 1, 5, 300, 1 (corn, soy, corn, soy, COUNT, 1)
        cdl_list.append(1)
        cdl_list.append(row.VALUE)
        cdl_comb.append(cdl_list)
        row = next(rows)

    return cdl_comb

###############################################################################
# Computes the crop rotations
# @param crp_rot_files: List of CDL files
# @return: crop rotations raster
###############################################################################
def computeCropRotations(state, out_dir, crp_rot_files, local_first_yr, local_last_yr, min_area_rot, min_perc_of_rot, first_loop):
    #yrs_in_rot es 3 en este caso.
    yrs_in_rot = len(crp_rot_files) # yrs_in_rot is the number of years for which we have crop rotation data
    print('yrs_in_rot = ', yrs_in_rot)
    #crp_rot_files es lo mismo que state_ras_files.
    # Extract the simplified raster data
    all_inp_rasters = '"'
    logger.info('Processing ' + str(yrs_in_rot) + ' rasters located in ' + inp_dir)

    prev_out_dir = out_dir
    if(USE_EXISTING_DATA):
        if(first_loop):
            global existing_inp_dir;
            existing_inp_dir  = output_dir
        else:
            if(local_first_yr > 2006):
                out_dir = existing_inp_dir+os.sep+str(state)
            else:
                out_dir = existing_inp_dir

    base_yr_data       = crp_rot_files[base_yr-local_first_yr]
    #print('base_yr_data = ',base_yr_data)
    comb_rasters       = out_dir+os.sep+COMB+str(state)+'_'+str(yrs_in_rot)+YRS
    cdl_comb           = []
    forest_data        = out_dir+os.sep+'forest'+str(base_yr)
    grasslands_data    = out_dir+os.sep+'grass'+str(base_yr)
    urban_data         = out_dir+os.sep+'urb'+str(base_yr)
    wout_urban         = out_dir+os.sep+BASE_YR_WOUT_URBAN+str(state)
    rot_and_frst       = out_dir+os.sep+FRST+str(state)+'_'+str(yrs_in_rot)+YRS
    rot_frst_grass     = out_dir+os.sep+ROT_FRST_GRASS+str(state)+'_'+str(yrs_in_rot)+YRS
    rot_frst_grass_urb = out_dir+os.sep+ROT_FRST_GRASS_URB+str(state)+'_'+str(yrs_in_rot)+YRS
    comb_final         = base_dir+os.sep+str(state)+'_'+str(yrs_in_rot)+YRS

    if(USE_EXISTING_DATA==False or first_loop==True):
        #For all years of CDL data, extract the pixels with crops
        for i in range(yrs_in_rot):
            if (i == 0):
                all_inp_rasters = '"'+out_dir+os.sep+OUT_RAS+str(state)+str(i)
            elif (i == yrs_in_rot -1):
                all_inp_rasters = all_inp_rasters+'; '+out_dir+os.sep+OUT_RAS+str(state)+str(i)+'"'
            else:
                all_inp_rasters = all_inp_rasters+'; '+out_dir+os.sep+OUT_RAS+str(state)+str(i)
        all_inp_rasters = []
        for i in range(yrs_in_rot):
            print(i)
            all_inp_rasters.append(out_dir+os.sep+OUT_RAS+str(state)+str(i))
            #print(all_inp_rasters)
            logger.info('\tExtracting attributes for raster ' + os.path.split(crp_rot_files[i])[1])
            # Simplify each of the rasters: i.e.extract the crop information
            #crop_cdl_2_str = returnLandUses(analysis_dir+os.sep+'cultivos_'+str(2012+i)+'.txt')
            crop_cdl_2_str = returnLandUses(analysis_dir+os.sep+str(CROPS))
            #print(crop_cdl_2_str)
            dir_path = os.path.dirname(crp_rot_files[i])
            file_name = os.path.basename(crp_rot_files[i])[:-11][-7:]
            #print(i, crp_rot_files[i])
            # Copy the TIF file to a GRID file to avoid a ArcGIS bug
            try:
                arcpy.CopyRaster_management(crp_rot_files[i], out_dir+os.sep+file_name,nodata_value=0)
                crp_rot_files[i] = out_dir+os.sep+file_name
                rasters_to_delete.append(out_dir+os.sep+file_name)
            except:
                logging.info('Copy raster '+crp_rot_files[i]+' failed')
                print('Copy raster '+crp_rot_files[i]+' failed')
            # Save output of extraction as ras_<state name>_<yr of rotation>
            att_extract = ExtractByAttributes(crp_rot_files[i], crop_cdl_2_str)
            att_extract.save(out_dir+os.sep+RAS+str(state)+str(i))
            rasters_to_delete.append(out_dir+os.sep+OUT_RAS+str(state)+str(i))
            rasters_to_delete.append(out_dir+os.sep+RAS+str(state)+str(i))

        # Remove the urban areas from raster for base_yr
        if remove_urban_and_wtlnd==True:
            logging.info('\tRemoving urban areas for '+os.path.split(base_yr_data)[1])
            urban_str = returnLandUses(analysis_dir+os.sep+URBAN_WETLANDS)
            out_set_null = SetNull(base_yr_data, base_yr_data, urban_str)
            out_set_null.save(wout_urban)
            rasters_to_delete.append(wout_urban)
        else:
            pass

    #For each raster replace the NoData values with cell values from raster for base_yr
        for i in range(yrs_in_rot):
            if i != ( (base_yr-local_first_yr) + ((yrs_in_rot-1)-(local_last_yr-local_first_yr)) ):
                logger.info('\tReplacing the NoData cells for ' + os.path.split(crp_rot_files[i])[1])
                try:
                    ###out_con = Con(IsNull(out_dir+os.sep+RAS+state+str(i)),base_yr_data,out_dir+os.sep+RAS+state+str(i))
                    out_con = Con(IsNull(out_dir+os.sep+RAS+str(state)+str(i)),299,out_dir+os.sep+RAS+str(state)+str(i))
                    out_con.save(out_dir+os.sep+OUT_RAS+str(state)+str(i))
                except:
                    logging.info(arcpy.GetMessages())
            else:
                try:
                    arcpy.CopyRaster_management(out_dir+os.sep+RAS+str(state)+str(i), out_dir+os.sep+OUT_RAS+str(state)+str(i),nodata_value=0)
                except:
                    logging.info(arcpy.GetMessages())

        # Combine the simplified rasters
        logger.info('Merging all CDLs')
#        out_combine = Combine([inRaster01,inRaster02,inRaster03])
#        out_combine.save(env.workspace+os.sep+'outcombine2')
        out_combine = Combine(all_inp_rasters)
        out_combine.save(comb_rasters)
        #('comb_rasters = ', comb_rasters)
        # Find the forested Land in sbase_yr
        if(append_for_grs_urb):
            logger.info('Extracting forest land in '+str(base_yr))
            cdl_f_str = returnLandUses(analysis_dir+os.sep+'forests_all.txt')
            att_extract = ExtractByAttributes(base_yr_data, cdl_f_str)
            att_extract.save(forest_data)
            # Find the grassland/pasture/herbaceus vegetation land in base_yr
            logger.info('Extracting grassland in '+str(base_yr))
            cdl_g_str = returnLandUses(analysis_dir+os.sep+GRASSLANDS)
            att_extract = ExtractByAttributes(base_yr_data, cdl_g_str)
            att_extract.save(grasslands_data)
            # Find the urban/wetland land in base_yr
            logger.info('Extracting urban and wetland in '+str(base_yr))
            cdl_u_str = returnLandUses(analysis_dir+os.sep+URBAN_WETLANDS)
            att_extract = ExtractByAttributes(base_yr_data, cdl_u_str)
            att_extract.save(urban_data)
    #################################################################################
    try:
        ras_cell_size_x = int(arcpy.GetRasterProperties_management(out_combine, 'CELLSIZEX').getOutput(0))
        ras_cell_size_y = int(arcpy.GetRasterProperties_management(out_combine, 'CELLSIZEY').getOutput(0))
        print('Tamanio de pixel (x,y) = (',ras_cell_size_x,',',ras_cell_size_y,')')
    except:
        logging.info(arcpy.GetMessages())
    area_raster = ras_cell_size_x*ras_cell_size_y*(m2_to_ha) # Area is computed in ha (convert cell_size_x*cell_size_y into ha)
    print('El area del pixel en hectareas es de:',area_raster)
    out_dir = prev_out_dir # Revert to the old out_dir
    cdl_comb = combineCDLs(comb_rasters, yrs_in_rot, state)

    # Sort the data based on the COUNT which is in column index yrs_in_rot (0 based counting)
    cdl_comb = sorted(cdl_comb, key=operator.itemgetter(yrs_in_rot), reverse = True)
    writeCDLData(cdl_comb, out_dir+os.sep+'cdl_comb_'+str(state)+'.csv')

    logger.info('Simplifying crop rotations')
    # Also create the reclassification table
    recl_1 = open(out_dir+os.sep+'recl_1.csv', 'w')
    state_stats = open(output_dir+os.sep+STATS+'.csv', 'a') # Contains information on how many pixels each rotation occupies

    total_pixels = 0
    for i in range(len(cdl_comb)):
        total_pixels += cdl_comb[i][yrs_in_rot]
    print('total_pixels', total_pixels)
    print('El area util es de:', total_pixels*area_raster)
    ###########################################################################
    # ALGORITHM!!!
    #
    #
    ###########################################################################
    # The first max_crop_rot rotations are selected by default
    cur_num_rot = 0
    cur_perc_land_in_rot = 0.0
    perc_simplified_land = 0.0
    perc_of_nxt_rot = 100.0
    cur_sum_land_in_rot = 0.0
    cur_index = 0
    cont_loop = False

    while((perc_of_nxt_rot>min_perc_of_rot and cur_perc_land_in_rot<min_area_rot)):
        cont_loop = False
        cur_num_rot += 1 # increase number of selected rotations by 1
        cur_sum_land_in_rot += float(cdl_comb[cur_index][yrs_in_rot])

        # find the % of pixels in all rotations till now
        #rate_of_increase = cur_perc_land_in_rot - prev_perc_land_in_rot # find how many pixels are in current rotation
        #prev_perc_land_in_rot = cur_perc_land_in_rot
        cur_index += 1
        try:
            perc_of_nxt_rot = float(cdl_comb[cur_index][yrs_in_rot])/float(cur_sum_land_in_rot)
            #print (cur_perc_land_in_rot, perc_of_nxt_rot,float(cdl_comb[cur_index][yrs_in_rot]),float(cur_sum_land_in_rot))
        except:
            perc_of_nxt_rot = 0.0 # If we end up here, we have probably run out of rotatiops
        cur_perc_land_in_rot = cur_sum_land_in_rot/float(total_pixels)
        if(perc_of_nxt_rot<min_perc_of_rot and cur_perc_land_in_rot<min_area_rot):
            cont_loop = True
        if(perc_of_nxt_rot>=min_perc_of_rot and cur_perc_land_in_rot>=min_area_rot):
            cont_loop = True
        if(perc_of_nxt_rot>=0.0 and cur_perc_land_in_rot>=1.0):
            cont_loop = False

    for i in range(cur_num_rot, len(cdl_comb)):
        cur_diff = 1.0
        rot_to_match_with =  0
        for j in range(cur_num_rot):
            # Compute the levenshtein distance between crop rotation types i and j
            # TODO!!! If we have 299 in crop rotation, then it does not compare well with the CDL because
            # that does not have 299
            diff_btwn_rot = float(lev(cdl_comb[i][:yrs_in_rot], cdl_comb[j][:yrs_in_rot]))/float(yrs_in_rot)

            # Check if the strings are permutations of each other
            if diff_btwn_rot < cur_diff:
                rot_to_match_with = j
                cur_diff = diff_btwn_rot

        cdl_comb[rot_to_match_with][yrs_in_rot] += cdl_comb[i][yrs_in_rot]
        # Set the USED bit of rotation 2 to 0
        cdl_comb[i][yrs_in_rot+1] = 0
        # In the reclassification file, set the reclassification bit to the rotation 1
        writeReClassFile(recl_1, cdl_comb[i][yrs_in_rot+2], cdl_comb[rot_to_match_with][yrs_in_rot+2])
        cdl_comb[i][yrs_in_rot+2] = cdl_comb[rot_to_match_with][yrs_in_rot+2]
        perc_simplified_land += (1.0-cur_diff)*cdl_comb[i][yrs_in_rot]/total_pixels

    float_str1 = "%.2f" % (cur_perc_land_in_rot*100)
    float_str2 = "%.2f" % (perc_simplified_land*100)
    float_str3 = "%.2f" % ((perc_simplified_land+cur_perc_land_in_rot)*100)
    logger.info('% of rotations which match CDL data exactly: '+str(float_str1)+'%')
    logger.info('% of rotations which have been simplified: '+str(float_str2)+'%')
    logger.info('% net accuracy: '+str(float_str3)+'%')
    stat_writer.write(str(state)+', '+str(cur_num_rot)+', '+str(local_first_yr)+', '+str(local_last_yr)+', '+str(float_str1)+', '+str(float_str3)+'\n')
    stat_writer.flush()

    cdl_comb = sorted(cdl_comb, key=operator.itemgetter(yrs_in_rot+1), reverse = True)
    writeCDLData(cdl_comb,out_dir+os.sep+CDL_ROT+str(state)+'.csv')
    recl_1.close()

    sort_csv(out_dir+os.sep+'recl_1.csv', (int, int, int), 0)

    # Reclassify
    rot_data = prev_out_dir+os.sep+ROT+str(state)+'_'+str(yrs_in_rot)+YRS
    num_lines = sum(1 for line in open(out_dir+os.sep+'recl_1.csv'))
    if(num_lines > 1):
       try:
          out_reclass = ReclassByTable(comb_rasters, out_dir+os.sep+'recl_1.csv', "FROM", "TO", "VALUE", "DATA")
          out_reclass.save(rot_data)
       except:
          logging.info(arcpy.GetMessages())
    else:
       rot_data = comb_rasters

    # read existing rotations
    prev_rot_file = csv.reader(open(base_dir+os.sep+'salida'+os.sep+tag+os.sep+EXISTING_ROTATIONS,'a+'))
    add_more_rot  = []
    max_rot_id    = MIN_ID
    prev_rot      = {}
    if(os.path.getsize(base_dir+os.sep+'salida'+os.sep+tag+os.sep+EXISTING_ROTATIONS) > 0):
        for str_row in prev_rot_file:
            row = [int(x) for x in str_row]
            #yrs_in_prev_rot = len(row)-1
            for i in range(1,len(row)-1):
                prev_rot[row[0]] = row[1:len(row)]
                if(row[0])>max_rot_id:
                    max_rot_id=row[0]

    # Reclassify the existing rotaations so that they do not overlap with the otehr CDL ID's.
    recl_cur_to_higher = open(out_dir+os.sep+'recl_cur_to_higher.csv', 'w')
    for i in range(len(cdl_comb)):
        if(cdl_comb[i][yrs_in_rot+1]>0):
            if(cdl_comb[i][yrs_in_rot+2]<max_rot_id):
                max_rot_id += 1
                recl_cur_to_higher.write(str(cdl_comb[i][yrs_in_rot+2])+', '+str(cdl_comb[i][yrs_in_rot+2])+', '+str(max_rot_id)+'\n')
                cdl_comb[i][yrs_in_rot+2] = max_rot_id

    recl_cur_to_higher.close()
    sort_csv(out_dir+os.sep+'recl_cur_to_higher.csv', (int, int, int), 0)

    higher_rot_data = out_dir+os.sep+HIGH+str(state)+'_'+str(yrs_in_rot)+YRS

    num_lines = sum(1 for line in open(out_dir+os.sep+'recl_cur_to_higher.csv'))
    if(num_lines > 1):
       try:
          out_reclass = ReclassByTable(rot_data, out_dir+os.sep+'recl_cur_to_higher.csv', "FROM"   , "TO", "VALUE", "DATA")
          out_reclass.save(higher_rot_data)
       except:
          logger.info(arcpy.GetMessages())
    else:
          higher_rot_data = rot_data
    # Extract the existing rotations
    cur_rot = {}
    for i in range(len(cdl_comb)):
        if(cdl_comb[i][yrs_in_rot+1]>0):
            #for j in range(yrs_in_rot):
            sync_vec = synchronizeRotation(cdl_comb[i][0:yrs_in_rot], yrs_in_rot, local_last_yr-local_first_yr+1, local_first_yr, prev_first_yr)
            cur_rot[cdl_comb[i][yrs_in_rot+2]] = sync_vec

    # Compare the newly created rotations with the existing rotations and reclassify
    # 1. Iterate through cur_rot and compare each cur_rot with the prev_rot
    # 2. If a cur_rot matches a prev_rot then put an entry in the reclass file
    # 3. If not, then add the cur_rot to the prev_rot file
    recl_cur_to_prev = open(out_dir+os.sep+'recl_cur_to_prev.csv', 'w')
    k1=k2=v1=v2=[]

    remove_cur_rot_items = []
    for k1,v1 in cur_rot.items():
        for k2,v2 in prev_rot.items():
            if(v1 == v2):
                # write in reclass file
                recl_cur_to_prev.write(str(k1)+', '+str(k1)+', '+str(k2)+'\n')
                remove_cur_rot_items.append(k1)
                # Iterate through cdl_comb and replace occurences of crop rotation type k1 with k2
                for i in range(len(cdl_comb)):
                    if(cdl_comb[i][yrs_in_rot+1]>0 and (cdl_comb[i][yrs_in_rot+2]==int(k1))):
                        cdl_comb[i][yrs_in_rot+2] = int(k2)

    for i in range(len(remove_cur_rot_items)):
        cur_rot.pop(remove_cur_rot_items[i])

    #global MIN_ID
    for k1,v1 in cur_rot.items():
        add_cur_rot = True
        for k2,v2 in prev_rot.items():
            if(k1==k2):
                tmp = max_rot_id+1
                max_rot_id += 1
                lis = tmp, v1
                recl_cur_to_prev.write(str(k1)+', '+str(k1)+', '+str(tmp)+'\n')

                add_more_rot.append(lis)
                add_cur_rot = False
                #MIN_ID += 300
        if add_cur_rot == True:
            lis = k1, v1
            recl_cur_to_prev.write(str(k1)+', '+str(k1)+', '+str(k1)+'\n')
            add_more_rot.append(lis)

    recl_cur_to_prev.close()
    sort_csv(out_dir+os.sep+'recl_cur_to_prev.csv', (int, int, int), 0)
    append_to_prev_rot_file = open(output_dir+os.sep+EXISTING_ROTATIONS,'a+')
    for j in range(len(add_more_rot)):
        # e.g. add_more_rot = (23, [24, 61, 61, 24])
        tmp = add_more_rot[j]
        append_to_prev_rot_file.write(str(tmp[0])+', ')
        for i in range(len(tmp[1])):
            append_to_prev_rot_file.write(str(tmp[1][i]))
            if i < (len(tmp[1])-1):
                append_to_prev_rot_file.write(', ')
            else:
                append_to_prev_rot_file.write('\n')
    append_to_prev_rot_file.close()
    shutil.copyfile(output_dir+os.sep+EXISTING_ROTATIONS,base_dir+os.sep+EXISTING_ROTATIONS)

    # Reclassify
    final_rot_data = out_dir+os.sep+PRODUCT+str(state)+'_'+str(yrs_in_rot)
    num_lines = sum(1 for line in open(out_dir+os.sep+'recl_cur_to_prev.csv'))
    if(num_lines > 1):
       try:
          out_reclass = ReclassByTable(higher_rot_data, out_dir+os.sep+'recl_cur_to_prev.csv', "FROM"   , "TO", "VALUE", "DATA")
          out_reclass.save(final_rot_data)
       except:
          logger.info(arcpy.GetMessages())
    else:
       final_rot_data = higher_rot_data

    # In the statename_stats.csv file print the crop rotation ID and the number of pixels it contains
    state_stats.write(str(state)+' , Rotation, Num_Pixels, Area_ha\n')
    for i in range(len(cdl_comb)):
        if(cdl_comb[i][yrs_in_rot+1]>0):
            sync_vec = synchronizeRotation(cdl_comb[i][:yrs_in_rot], yrs_in_rot, local_last_yr-local_first_yr+1, local_first_yr, prev_first_yr)
            state_stats.write(str(cdl_comb[i][yrs_in_rot+2])+', '+str(sync_vec).strip('[]')+', '+ str(cdl_comb[i][yrs_in_rot])+\
                              ', '+'\n')

    state_stats.close()

    # Append the forest data to the remaining set
    if(append_for_grs_urb and first_loop==True):
        logger.info('Appending forest,grassland and urban data')
        out_con = Con(IsNull(forest_data),final_rot_data,forest_data)
        out_con.save(rot_and_frst)
        # Append the grasslands data to the remaining set
        out_con = Con(IsNull(grasslands_data),rot_and_frst,grasslands_data)
        out_con.save(rot_frst_grass)
        # Append the urban data to the remaining set
        out_con = Con(IsNull(urban_data),rot_frst_grass,urban_data)
        out_con.save(rot_frst_grass_urb)
        out_con.save(comb_final)
        rasters_to_delete.append(forest_data)
        rasters_to_delete.append(grasslands_data)
        rasters_to_delete.append(urban_data)
        rasters_to_delete.append(rot_and_frst)
        rasters_to_delete.append(rot_frst_grass)
    else:
        try:
            arcpy.CopyRaster_management(final_rot_data, rot_frst_grass_urb,nodata_value=0)
            arcpy.CopyRaster_management(final_rot_data, comb_final,nodata_value=0)
        except:
            logging.info(arcpy.GetMessages())

    # Add temporary files to the delete files set
    rasters_to_delete.append(rot_data)
    rasters_to_delete.append(higher_rot_data)
    rasters_to_delete.append(comb_rasters)
    rasters_to_delete.append(final_rot_data)

    return rot_frst_grass_urb
############################# End of cropRotations#############################

###############################################################################
# Call the crop rotations code for each state for a given pair of parameters
# @param
# @return:
###############################################################################
def initiate(list_min_area_rot, list_min_rate_increase, local_first_yr, local_last_yr, first_loop,ident):
    #llamo los directorios y los guardo en listas.
    for subdir, dir_list, files in os.walk(inp_dir):
        break

    num_rot = local_last_yr-local_first_yr+1
    print('cantidad de elementos de una rotacion =', num_rot)
    # Read in the list of states to process
    #state_file = open(analysis_dir+os.sep+list_states, 'rb')
    #lines = state_file.readlines()
    lines = ['cba']


    # merged raster containing all states data
    to_merge_files = []
    merged_ras = 'merged'

    #loop para todos los estados.
    for line in lines:
        frst = False

        state = line.split()[0]
        # out_dir contains the output and intermediate analysis stuff
        if(local_first_yr>2006):
            out_dir  = str(output_dir)+os.sep+str(state)
        else:
            out_dir  = str(output_dir)
        if not os.path.exists (out_dir):
            os.makedirs(out_dir)

        state_ras_files = []
        range_of_yrs = []

        for i in range(num_rot):
            range_of_yrs.append(local_first_yr + i)

        logger.info('Evaluating '+state)
        logger.info('CROP ROTATIONS FOR '+state)
        #aca abrimos la carpeta correspondiente al anio en  el que estamos.
        for j in range(len(range_of_yrs)):
             for position, item in enumerate(dir_list):
                 #print (position, item)
                 if (str(range_of_yrs[j]) in item):
                     #buscamos el raster que corresponde al anio en el que estamos.
                     list_files = glob.glob(inp_dir+os.sep+str(range_of_yrs[j])+os.sep+str(range_of_yrs[j])+'_reclasificado.tif')
                     print(range_of_yrs[j],inp_dir+os.sep+str(range_of_yrs[j])+os.sep+str(range_of_yrs[j])+'_reclasificado.tif')
                     #print('aca si entra',list_files)
                     if list_files:
                         if frst == False:
                             local_first_yr = range_of_yrs[j]
                             frst = True
                         state_ras_files.append(''.join(list_files))
                     else:
                         print('No se leyeron bien los archivos TIF de entrada.')
        # env.workspace = "C:\\Users\\jo_ro\\Google Drive\\Maestria en Estadistica\\ArcGIS\\CropRotations-master\\entrada"
        # #set local variables
        # inRaster01 = "Est_12_13"
        # inRaster02 = "Est_13_14"
        # inRaster03 = "Est_14_15"
        # state_ras_files = [inRaster01,inRaster02,inRaster03]

        if len(state_ras_files) > num_rot:
            state_ras_files = state_ras_files[:num_rot]
            local_last_yr   = local_first_yr + num_rot - 1

        logger.info('List of raster files ')
        for k in range(len(state_ras_files)):
            logger.info(state_ras_files[k])
        logger.info('First Year '+str(local_first_yr))
        logger.info('Last Year '+str(local_last_yr))

        #hasta aca funcionaria bien.
        ras = computeCropRotations(state, out_dir, state_ras_files, local_first_yr, local_last_yr, list_min_area_rot, list_min_rate_increase, first_loop)
        to_merge_files.append(ras)

    # Delete all arcgis files except the merged raster
    for i in range(len(to_merge_files)):
        logger.info('Deleting raster '+os.path.split(to_merge_files[i])[1])
        rasters_to_delete.append(to_merge_files[i])

    if(bool_merge_ras_files and first_loop==True):
        logger.info('Merging all crop rotation rasters...')
        try:
            if(len(to_merge_files)>1):
                arcpy.MosaicToNewRaster_management(to_merge_files, output_dir, merged_ras, "", "8_BIT_UNSIGNED", "", "1", "LAST", "FIRST")
            else:
                arcpy.Rename_management(to_merge_files, merged_ras)
        except:
            logger.info(arcpy.GetMessages())
            #delete_interim_files()

    # cdl_map maps CDL IDs to crop names e.g. 1 is mapped to Corn
    cdl_map_file = csv.reader(open(analysis_dir+os.sep+CDL_VAL_NAME_MAP, 'r'))
    cdl_map = {}
    # cdl_map1 = {}
    # cdl_map2 = {}
    # cdl_map3 = {}

    #aca asigna el numero que le corresponde a cada anio correctamente.
    for row in cdl_map_file:
        cdl_map[int(row[0])] = row[1]
    # for row in cdl_map_file:
    #     cdl_map1[int(row[0])] = row[1]
    #     cdl_map2[int(row[0])] = row[2]
    #     cdl_map3[int(row[0])] = row[3]

    # Write a use friendly version of the EXISTING_ROTATIONS file
    prev_rot_file = csv.reader(open(output_dir+os.sep+EXISTING_ROTATIONS,'r'))
    human_readable_rot = open(output_dir+os.sep+READABLE_ROTS,'w')
    #human_readable_rot2 = open(base_dir+os.sep+READABLE_ROTS,'w')
    #numero de pixeles por combinacion
    para_has = csv.reader(open(output_dir+os.sep+STATS+'.csv', 'r'))
    i=0
    num_pix =[]
    for str_row in para_has:
        i+=1
        if i > 1:
            num_pix.append(str_row[num_rot+1])
    j=0
    for str_row in prev_rot_file:
        j+=1
        line = []
        #row contiene todas las combinaciones
        row = [int(float(x)) for x in str_row]
        line.append(row[0])

        for i in range(1,len(row)):
            try:
                line.append(cdl_map[row[i]])
            except:
                print(row[i])
        #print(str_row)
        line.append(num_pix[j-1])
        # for i in range(1,len(row)):
        #     if i==1:
        #         try:
        #             line.append(cdl_map1[row[i]])
        #         except:
        #             print(row[i])
        #     if i==2:
        #         try:
        #             line.append(cdl_map2[row[i]])
        #         except:
        #             print(row[i])
        #     if i==3:
        #         try:
        #             line.append(cdl_map3[row[i]])
        #         except:
        #             print(row[i])
        csv.writer(human_readable_rot).writerow(line)
        #csv.writer(human_readable_rot2).writerow(line)

    # Delete all intermediate excel files
    list_csv_files = glob.glob(out_dir+os.sep+'*.csv*')
    for k in range(len(list_csv_files)):
        csv_files_to_delete.append(list_csv_files[k])

###############################################################################
# Find the number of unique elements in a sequence. Does not exclude characters
# @param
# @return:
###############################################################################
def uniquify(seq):
    # order preserving
    checked = []
    for e in seq:
        if e not in checked:
            checked.append(e)
    return checked

exp_file  = open(base_dir+os.sep+'salida'+os.sep+EXPR_FILE+'.csv','a+')
exp_file.write('min_area_rot, min_rate_increase, num_uniq_rot, avg_accuracy, delta_accuracy\n')

first_loop = True # Are we running the first loop of params a and b? If so, store the results for each
                  # state so that we do not need to recompute them.
existing_inp_dir = ''
for a in list_min_area_rot:
    for b in list_min_perc_of_rot:
        date           = datetime.datetime.now().strftime("%H-%M")
        #tag            = 'LakeSt_07_09'+date+'_'+str(a)+'_'+str(b)
        tag            = 'cba'+date+'_'+str(a)+'_'+str(b)
        ROTATION_STATS = 'resultados_'+tag+'.csv'
        READABLE_ROTS  = 'rotaciones_legibles_'+date+'.csv'
        seq = []

        output_dir = base_dir+os.sep+'salida'+os.sep+tag # contains all the output files
        # Create the output directory using the current date and tag
        if not os.path.exists (output_dir):
            os.makedirs(output_dir)

        LOG_FILENAME   = output_dir+os.sep+'Log_'+date+'.txt'
        logging.basicConfig(filename = LOG_FILENAME, level=logging.DEBUG) # Logging levels are DEBUG, INFO, WARNING, ERROR, and CRITICAL
        logger = logging
        logging.info("Started processing at :"+ date)
        logging.info(str(a)+' '+str(b))
        # Copy the EXISTING_ROTATIONS file to the current output directory
        try:
            shutil.copyfile(analysis_dir+os.sep+EXISTING_ROTATIONS, output_dir+os.sep+EXISTING_ROTATIONS)
        except:
            print('File copy of existing rotations failed')

        # Output the stats
        stat_writer    = open(output_dir+os.sep+ROTATION_STATS,'w')
        stat_writer.write('State, # Rot, Start Yr, End Yr, % CDL Match, % Overall Match\n')
        initiate(a, b, first_yr, last_yr, first_loop,ident)
        stat_writer.close()
        # Find number of unique crop rotations (excludes, grasslands, crops, urban areas)
        state_stats = open(output_dir+os.sep+STATS+'.csv', 'r') # Read in state_stats
        for line in state_stats:
            num = line.strip().split(',')[0]
            if(num.isdigit()):
                seq.append(num)

        exp_file.write(str(a)+', '+str(b)+', '+str(len(uniquify(seq)))+', ')

        # Find avg, delta, min and max accuracy of the last 2 columns in the ROTATION_STATS file
        state_stat = open(output_dir+os.sep+ROTATION_STATS,'r')
        cdl_match = []
        ovr_match = []
        frst_line = True
        for line in state_stat:
            if(frst_line):
                frst_line = False
            else:
                cdl_match.append(float(line.strip().split(',')[4]))
                ovr_match.append(float(line.strip().split(',')[5]))

        sum_cdl_match = sum(cdl_match)
        sum_ovr_match = sum(ovr_match)
        len_cdl_ovr   = len(cdl_match)
        avg_ovr       = (sum_ovr_match - sum_cdl_match)/len_cdl_ovr

        exp_file.write(str(sum_cdl_match/len_cdl_ovr)+', '+str(avg_ovr)+'\n')
        exp_file.flush()
        first_loop = False
        logging.info("Finished processing at :"+ time.strftime("%H:%M:%S", time.localtime()))

# Delete interim rasters
#delete_interim_files()
print('Done!')
