import os, time, pdb, operator, csv, glob, logging, shutil, arcpy, datetime
import numpy as np
from arcpy import env
from arcpy.sa import *

SD = 299
RSV = 3
SJ = 1
RSI = 8
TRI = 9
OTI = 10
mono = RSI
#Prueba la licencia de arcgis
arcpy.CheckOutExtension("spatial")
arcpy.env.overwriteOutput= True
arcpy.env.extent         = "MAXOF"

ubicacion_archivo = 'C:\\Users\\jo_ro\\Google Drive\\Maestria en Estadistica\\ArcGIS\\Antonio\\Rotacion-cultivo-Invernal\\rotaciones_existentes.csv'
donde_guardar = 'C:\\Users\\jo_ro\\Google Drive\\Maestria en Estadistica\\ArcGIS\\Antonio\\Rotacion-cultivo-Invernal\\salida.csv'

ras_in = 'C:\\Users\\jo_ro\\Google Drive\\Maestria en Estadistica\\ArcGIS\\Antonio\\Rotacion-cultivo-Invernal\\salida\\cba14-32_0.999_0\\cba\\all_cba_7yrs'
ras_out = 'C:\\Users\\jo_ro\\Google Drive\\Maestria en Estadistica\\ArcGIS\\Antonio\\Rotacion-cultivo-Invernal\\salida\\cba14-32_0.999_0\\raster_reclasificado.tif'


def reclasificador(entrada,salida,clasificador,etiqueta):
    out_reclass = ReclassByTable(entrada, clasificador, "FROM", "TO", "VALUE", "DATA")
    arcpy.AddField_management(out_reclass,'Clase','TEXT')
    cursor = arcpy.UpdateCursor(out_reclass)
    row = cursor.next()
    i = 0
    while row:
        row.setValue('Clase',str(etiqueta[i]))
        i+=1
        cursor.updateRow(row)
        row = cursor.next()
    out_reclass.save(salida)

def lector_datos(file_name):
    g = open(file_name,'r')
    y = []
    z = []
    for row in csv.reader(g,int):
        x=[]
#        for i in range(1,len(row)):
        for i in range(1,len(row)):
            #print(row[i])
            #x.append(int(float(row[i])))
            x.append(int(float(row[i])))
        y.append(x)
        z.append(int(float(row[:1][0])))
    return y,z

def guardar_datos(file_name,viejos,nuevos):
    f = open(file_name,'w')
    csv.writer(f).writerow(['FROM', 'TO', 'VALUE'])
    for i in range(len(viejos)):
        csv.writer(f).writerow([viejos[i],viejos[i],nuevos[i]])

def generador_categorias(categorias,len_sec,numeracion):
    clasificacion = []
    rotacion = []
    for k in range(len(categorias)):
        a = categorias[k]
        if len(a) == 1:
            clasificacion.append([a[0] for i in range(len_sec)])
            rotacion.append(numeracion[k])
        elif len(a) <= len_sec: #sercioro que la categoria tenga sentido...
            for i in range(len(a)):
                rotacion.append(numeracion[k])
                a = a[1:]+a[:1]
                largo_a = len(a)
                categoria = []
                rep = int(len_sec/largo_a)
                if np.remainder(len_sec,largo_a) == 0:
                    for i in range(rep):
                        categoria += a
                else:
                    resto = np.remainder(len_sec,largo_a)
                    for i in range(rep):
                        categoria += a
                    for i in range(resto):
                        categoria.append(a[i])
                clasificacion.append(categoria)
        #clasificacion tiene todas las categorias posibles de la categoria correspondiente
    #clasificador
    return clasificacion, rotacion

####################################################################################################################3
a_clasificar,clases_viejas = lector_datos(ubicacion_archivo)
# categorias = [[mono],[RSI,RSI,RSI,RSI,RSI,RSI,TRIGO],[RSI,RSI,RSI,RSI,RSI,TRIGO,TRIGO],[RSI,RSI,RSI,RSI,TRIGO,TRIGO,TRIGO],[RSI,RSI,RSI,TRIGO,TRIGO,TRIGO,TRIGO],[RSI,RSI,TRIGO,TRIGO,TRIGO,TRIGO,TRIGO],[RSI,TRIGO,TRIGO,TRIGO,TRIGO,TRIGO,TRIGO],[TRIGO]]
etiqueta = ['RSI','>RSI','>TRI','>OTI','TODOS','Sin Clasificar','Otros']
numeracion = [800,801,802,803,804,2000,1000]
len_sec = len(a_clasificar[0])
label = dict(zip(etiqueta,numeracion))
#############################################
#Generador de categorias
final_num = [label['Otros'] for i in range(len(a_clasificar))]
#clasificacion, rotacion = generador_categorias(categorias,len_sec,numeracion)

for j in numeracion:
    i=0
    for x in final_num:
        if x == j:
            i+=1
    print(j,i)
###########################################################################################
#PRIMER CATEGORIZACION
#asignamos UNA categoria a cada una de las secuencias en cada . k corre en numero de pixel.
#a_clasificar tiene todas  las secuencias de cada uno de los pixeles.
for m in range(len(a_clasificar)):
     #buscamos si corresponde a alguna de todas las clasificaciones posibles.
    if SD in a_clasificar[m]:
        a_clasificar[m].remove(SD)
        if SD in a_clasificar[m]:
            a_clasificar[m].remove(SD)
            if SD in a_clasificar[m]:
                final_num[m] = label['Sin Clasificar']
            else:
                final_num[m] == label['Otros']
        else:
            final_num[m] = label['Otros']
    else:
        final_num[m] = label['Otros']
#GUARDAMOS UBICACION
ident = [i for i in range(0,len(a_clasificar))]
resultado1 = list(zip(ident,final_num,a_clasificar))
###############################################################################
#Corroboracion de la cantidad de secuencias que entran en cada categoria:
# print('Clasificacion Posterior 1:')
for j in numeracion:
    i=0
    for x in final_num:
        if x == j:
            i+=1
    print(j,i)
###############################################################################
#IDENTIFICACION RSI y TRIGO
j = 0
m1=0; m2=0; m3=0; m4=0; m5=0; m6=0
x1=[]
for l in range(len(resultado1)):
    if final_num[l] == label['Otros'] and len(resultado1[l][2]) == 7:
        n_rsi = 0
        n_tri = 0
        n_oti = 0
        for i in range(len(resultado1[l][2])):
            if resultado1[l][2][i] == RSI:
                n_rsi += 1
            elif resultado1[l][2][i] == TRI:
                n_tri += 1
            elif resultado1[l][2][i] == OTI:
                n_oti += 1
            else:
                print('Error! La secuencia:')
                print(resultado[l][2])
                print('tiene otro valor.')
        if RSI in resultado1[l][2] and OTI in resultado1[l][2] and TRI in resultado1[l][2]:
            x1.append(label['TODOS'])
            m5 += 1
        elif n_rsi == len(resultado1[l][2]):
            x1.append(label['RSI'])
            m6 += 1
        elif n_rsi >= len(resultado1[l][2])/2:
            x1.append(label['>RSI'])
            m1 += 1
        elif n_tri >= len(resultado1[l][2])/2 and (OTI in resultado1[l][2]):
            x1.append(label['>TRI'])
            m2 += 1
        elif n_tri >= len(resultado1[l][2])/2 and (RSI in resultado1[l][2]):
            x1.append(label['>TRI'])
            m3 += 1
        elif n_oti >= len(resultado1[l][2])/2:
            x1.append(label['>OTI'])
            m4 += 1
        else:
            x1.append(final_num[l])
    elif final_num[l] == label['Otros'] and len(resultado1[l][2]) == 6:
        n_rsi = 0
        n_tri = 0
        n_oti = 0
        for i in range(len(resultado1[l][2])):
            if resultado1[l][2][i] == RSI:
                n_rsi += 1
            elif resultado1[l][2][i] == TRI:
                n_tri += 1
            elif resultado1[l][2][i] == OTI:
                n_oti += 1
            else:
                print('Error! La secuencia:')
                print(resultado[l][2])
                print('tiene otro valor.')
        if RSI in resultado1[l][2] and OTI in resultado1[l][2] and TRI in resultado1[l][2]:
            x1.append(label['TODOS'])
            m5 += 1
        elif n_rsi == len(resultado1[l][2]):
            x1.append(label['RSI'])
            m6 += 1
        elif n_rsi >= len(resultado1[l][2])/2:
            x1.append(label['>RSI'])
            m1 += 1
        elif n_tri >= len(resultado1[l][2])/2 and (OTI in resultado1[l][2]) and (RSI not in resultado1[l][2]):
            x1.append(label['>TRI'])
            m2 += 1
        elif n_tri >= len(resultado1[l][2])/2 and (RSI in resultado1[l][2]) and (OTI not in resultado1[l][2]):
            x1.append(label['>TRI'])
            m3 += 1
        elif n_oti >= len(resultado1[l][2])/2:
            x1.append(label['>OTI'])
            m4 += 1
        else:
            x1.append(final_num[l])
    elif final_num[l] == label['Otros'] and len(resultado1[l][2]) == 5:
        n_rsi = 0
        n_tri = 0
        n_oti = 0
        for i in range(len(resultado1[l][2])):
            if resultado1[l][2][i] == RSI:
                n_rsi += 1
            elif resultado1[l][2][i] == TRI:
                n_tri += 1
            elif resultado1[l][2][i] == OTI:
                n_oti += 1
            else:
                print('Error! La secuencia:')
                print(resultado[l][2])
                print('tiene otro valor.')
        if RSI in resultado1[l][2] and OTI in resultado1[l][2] and TRI in resultado1[l][2]:
            x1.append(label['TODOS'])
            m5 += 1
        elif n_rsi == len(resultado1[l][2]):
            x1.append(label['RSI'])
            m6 += 1
        elif n_rsi >= len(resultado1[l][2])/2:
            x1.append(label['>RSI'])
            m1 += 1
        elif n_tri >= len(resultado1[l][2])/2 and (OTI in resultado1[l][2]) and (RSI not in resultado1[l][2]):
            x1.append(label['>TRI'])
            m2 += 1
        elif n_tri >= len(resultado1[l][2])/2 and (RSI in resultado1[l][2]) and (OTI not in resultado1[l][2]):
            x1.append(label['>TRI'])
            m3 += 1
        elif n_oti >= len(resultado1[l][2])/2:
            x1.append(label['>OTI'])
            m4 += 1
        else:
            x1.append(final_num[l])
    else:
        x1.append(final_num[l])
print(len(final_num),len(x1))
for k in range(len(final_num)):
    final_num[k] = x1[k]

print('Despues de clasificar')
print('a TODOS:'+str(label['TODOS'])+' se sumaron:', m5)
print('a MONO:'+str(label['RSI'])+' se sumaron:',m6)
print('a RSI:'+str(label['>RSI'])+' se sumaron:', m1)
print('a TRI-OTI:'+str(label['>TRI'])+' se sumaron:', m2)
print('a TRI-RSI:'+str(label['>TRI'])+' se sumaron:', m3)
print('a OTI:'+str(label['>OTI'])+' se sumaron:', m4)
###############################################################################
print('Las cantidades de cada categoria ahora son:')
for j in numeracion:
    i=0
    for x in final_num:
        if x == j:
            i+=1
    print(j,i)

print('codificacion:')
print('RSI=',RSI,' ; ','OTI=',OTI,' ; ','TRI=',TRI,' ; ')
print('Algunas de las que quedaron en OTRAS fueron:')
for i in range(len(resultado1)):
    if final_num[i] == label['Otros'] and i <= 200:
        print(i, final_num[i], resultado1[i][2])

print('Generacion exitosa!')
guardar_datos(donde_guardar,clases_viejas,final_num)
reclasificador(ras_in,ras_out,donde_guardar,etiqueta)
print('Archvio reclasificado ubicado en')
print(ras_out)
