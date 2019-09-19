import os, time, pdb, operator, csv, glob, logging, shutil, arcpy, datetime
import numpy as np
from arcpy import env
from arcpy.sa import *

SD = 299
RSV = 3
SJ = 1

#Prueba la licencia de arcgis
arcpy.CheckOutExtension("spatial")
arcpy.env.overwriteOutput= True
arcpy.env.extent         = "MAXOF"

ubicacion_archivo = 'C:\\Users\\jo_ro\\Google Drive\\Maestria en Estadistica\\ArcGIS\\Antonio\\Rotacion-cultivo-estival\\rotaciones_existentes.csv'
donde_guardar = 'C:\\Users\\jo_ro\\Google Drive\\Maestria en Estadistica\\ArcGIS\\Antonio\\Rotacion-cultivo-estival\\salida.csv'

ras_in = 'C:\\Users\\jo_ro\\Google Drive\\Maestria en Estadistica\\ArcGIS\\Antonio\\Rotacion-cultivo-estival\\salida\\cba14-16_0.999_0\\cba\\all_cba_8yrs'
ras_out = 'C:\\Users\\jo_ro\\Google Drive\\Maestria en Estadistica\\ArcGIS\\Antonio\\Rotacion-cultivo-estival\\salida\\cba14-16_0.999_0\\raster_reclasificado.tif'


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
    #arcpy.CalculateField_management(out_reclass,'Clase',str(etiqueta[1]))
    # cursor = arcpy.da.InsertCursor(out_reclass,'Clase')
    # for i in range(len(etiqueta)):
    #     cursor.insertRow('Clase',etiqueta[i])
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
        if a == [1]:
            clasificacion.append([1 for i in range(len_sec)])
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
categorias = [[1],[1,2],[1,1,2],[1,1,1,2],[1,1,1,1,2]]
# etiqueta = ['monocultivo','4 1','3 1','2 1','1 1','Otros','Sin Clasificar','sjrsv','rsv','MAIZ','MS','MSR','MS5','TODOS']
# numeracion = [500,504,503,502,501,600,700,550,551,510,520,521,522,530]
etiqueta = ['monocultivo','1 1','2 1','3 1','4 1','MAIZ','MS','MSR','MS5','TODOS','sjrsv','rsv','Otros','Sin Clasificar']
numeracion = [500,501,502,503,504,510,520,521,522,530,550,551,600,700]
len_sec = len(a_clasificar[0])
label = dict(zip(etiqueta,numeracion))
#############################################
#Generador de categorias
#final = ['Otros' for i in range(len(a_clasificar))]
final_num = [label['Otros'] for i in range(len(a_clasificar))]
clasificacion, rotacion = generador_categorias(categorias,len_sec,numeracion)
clasificacion2, rotacion2 = generador_categorias(categorias,len_sec-1,numeracion)
clasificacion3, rotacion3 = generador_categorias(categorias,len_sec-2,numeracion)

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
                for j in range(len(clasificacion3)):
                    if a_clasificar[m] == clasificacion3[j]:
                        final_num[m] == rotacion3[j]
        else:
            for j in range(len(clasificacion2)):
                if a_clasificar[m] == clasificacion2[j]:
                    final_num[m] = rotacion2[j]
    else:
        for j in range(len(clasificacion)):
            if a_clasificar[m] == clasificacion[j]:
                final_num[m] = rotacion[j]

#GUARDAMOS UBICACION
ident = [i for i in range(0,len(a_clasificar))]
resultado1 = list(zip(ident,final_num,a_clasificar))
###############################################################################
#Corroboracion de la cantidad de secuencias que entran en cada categoria:
print('Clasificacion Posterior 1:')
for j in numeracion:
    i=0
    for x in final_num:
        if x == j:
            i+=1
    print(j,i)
###############################################################################
#Ahora trabajamos unicamente con los identificados como OTROS
#IDENTIFICACION 1,1,2
j = 0
seq = [[1,1,2],[2,1,1]]
print('Secuencia 2 1')
for s in seq:
    x1 = []
    for l in range(len(resultado1)):
        if final_num[l] == label['Otros']:
            xx = []
            for i in range(len(resultado1[l][2])):
                if resultado1[l][2][i:i+len(s)] == s:
                    xx.append(True)
            if len(xx)>=2:
                # print(s,final_num[l],resultado1[l][2])
                x1.append(label['2 1'])
                j+=1
            else:
                x1.append(final_num[l])
        else:
            x1.append(final_num[l])
    print(len(final_num),len(x1),len(resultado1))
    for k in range(len(final_num)):
        final_num[k] = x1[k]
print('Despues del primer filtro')
print('a '+str(label['2 1'])+' se sumaron:', j)
###############################################################################
#Ahora trabajamos unicamente con los identificados como OTROS
#identificamos 1 1
j = 0
seq = [[1,2],[2,1]]
print('Secuencia 1 1')
for s in seq:
    x1 = []
    for l in range(len(resultado1)):
        if final_num[l] == label['Otros']:
            xx = []
            for i in range(len(resultado1[l][2])):
                if resultado1[l][2][i:i+len(s)] == s:
                    xx.append(True)
            if len(xx)>=3:
                #print(s,final_num[l],resultado1[l][2])
                x1.append(label['1 1'])
                j+=1
            else:
                x1.append(final_num[l])
        else:
            x1.append(final_num[l])
    #print(len(final_num),len(x1),len(resultado1))
    for k in range(len(final_num)):
        final_num[k] = x1[k]
print('Despues del segundo filtro')
print('a '+str(label['1 1'])+' se sumaron:', j)
###############################################################################
#Ahora trabajamos unicamente con los identificados como OTROS
#IDENTIFICACION Sj y RSV
j = 0
m=0
print('Secuencia SJ y RSV')
x1=[]
for l in range(len(resultado1)):
    if final_num[l] == label['Otros']:
        xx = []
        n_rsv = n_sj =0
        if RSV in resultado1[l][2]:
            for i in range(len(resultado1[l][2])):
                if resultado1[l][2][i] == RSV:
                    n_rsv+=1
                elif resultado1[l][2][i] == SJ:
                    n_sj+=1
        if n_sj >= 3 and n_rsv >= 2:
            x1.append(label['sjrsv'])
            j+=1
        elif n_rsv > len(resultado1[l][2])/2:
            x1.append(label['rsv'])
            m+=1
        else:
            x1.append(final_num[l])
    else:
        x1.append(final_num[l])
for k in range(len(final_num)):
    final_num[k] = x1[k]
print('Despues del tercer filtro')
print('a '+str(label['sjrsv'])+' se sumaron:', j)
print('a '+str(label['rsv'])+' se sumaron:', m)
for j in numeracion:
    i=0
    for x in final_num:
        if x == j:
            i+=1
    print(j,i)

###############################################################################
#este codigo elije los MONOCULTIVO con 6/8, 5/7 o 4/6. (de los restantes)
i = 0
x2 = []
print('monocultivo')
for l in range(len(resultado1)):
    if final_num[l] == label['Otros']:
        j = 0
        for k in range(len(resultado1[l][2])):   #resultado1[l][2] es el vector de secuencia
            if resultado1[l][2][k]==1:
                j+=1
        if (j>= len(resultado1[l][2])-2):
            i+=1
            x2.append(label['monocultivo'])
        else:
            x2.append(final_num[l])
    else:
        x2.append(final_num[l])
# print(x2)
for k in range(len(final_num)):
    final_num[k] = x2[k]

print("Despues del cuarto filtro:")
print('A 500 se le sumaron:',i)
resultado2 = [[resultado1[i][0],final_num[i],resultado1[i][2]] for i in range(len(resultado1))]
###############################################################################
#este codigo busca entre los sobrantes, aquellos que tengan mas de la mitad del largo del vector con maiz
#categoria MAIZ
i = 0
x3 = []
for l in range(len(resultado2)):
    if final_num[l] == label['Otros']:
        j=0
        for k in range(len(resultado2[l][2])):
            if resultado2[l][2][k] == 2:
                j+=1
        if j>len(resultado2[l][2])/2:
            i+=1
            x3.append(label['MAIZ'])
        else:
            x3.append(final_num[l])
    else:
        x3.append(final_num[l])
for k in range(len(final_num)):
    final_num[k] = x3[k]

print("Despues del quinto filtro:")
print('A '+str(label['MAIZ'])+' se le sumaron:',i)
###############################################################################
#este codigo busca entre los sobrantes, aquellos que aparezcan las secuencias 2,1,2,1,2 o 1,2,1,2,1
#categoria 1 1
j = 0
seq = [[1,2,1,2,1],[2,1,2,1,2]]
for s in seq:
    x4 = []
    for l in range(len(resultado1)):
        if final_num[l] == label['Otros']:
            xx = []
            for i in range(len(resultado1[l][2])):
                if resultado1[l][2][i:i+len(s)] == s:
                    xx.append(True)
            if len(xx)>=1:
                #print(s,final_num[l],resultado1[l][2])
                x4.append(label['1 1'])
                j+=1
            else:
                x4.append(final_num[l])
        else:
            x4.append(final_num[l])
    #print(len(final_num),len(x1),len(resultado1))
    for k in range(len(final_num)):
        final_num[k] = x4[k]
print('Despues del sexto filtro')
print('a '+str(label['1 1'])+' se sumaron:', j)
###############################################################################
#este codigo busca entre los sobrantes, aquellas secuencias donde aparecen solamente 1 y 2, pero sin rotacion definida.
#ademas se consideran que aparezcan 1 y 2 solamente con un 3 (MSR)
#ademas se consideran que aparezcan 1 y 2 solamente con un 5 (MS5)
#categoria MS, MS5 y MSR
i=n=s = 0
x5 = []
for l in range(len(resultado2)):
    if final_num[l] == label['Otros']:
        if (3 not in resultado2[l][2]) and (5 not in resultado2[l][2]):
            i+=1
            x5.append(label['MS'])
        elif 3 not in resultado2[l][2] and 5 in resultado2[l][2]:
            j = 0
            for k in range(len(resultado2[l][2])):
                if resultado2[l][2][k] == 5:
                    j+=1
            if j == 1:
                x5.append(label['MS5'])
                n+=1
            else:
                x5.append(final_num[l])
        elif 3 in resultado2[l][2] and 5 not in resultado2[l][2]:
            j = 0
            for k in range(len(resultado2[l][2])):
                if resultado2[l][2][k] == 3:
                    j+=1
            if j == 1:
                x5.append(label['MSR'])
                s+=1
            else:
                x5.append(final_num[l])
        else:
            x5.append(final_num[l])
    else:
        x5.append(final_num[l])
for k in range(len(final_num)):
    final_num[k] = x5[k]
print('Despues del sexto filtro')
print('a '+str(label['MS'])+' se sumaron:', i)
print('a '+str(label['MS5'])+' se sumaron:', n)
print('a '+str(label['MSR'])+' se sumaron:', s)
###############################################################################
#Categoria que aparezcan los 4
i = 0
x6 = []
for l in range(len(resultado2)):
    if final_num[l] == label['Otros']:
        if 1 in resultado2[l][2] and 2 in resultado2[l][2] and 3 in resultado2[l][2] and 5 in resultado2[l][2]:
            i+=1
            x6.append(label['TODOS'])
        else:
            x6.append(final_num[l])
    else:
        x6.append(final_num[l])
for k in range(len(final_num)):
    final_num[k] = x6[k]
print('a '+str(label['TODOS'])+' se sumaron:', i)
###############################################################################
#Corroboracion de la cantidad de secuencias que entran en cada categoria:
print('Las cantidades de cada categoria ahora son:')
for j in numeracion:
    i=0
    for x in final_num:
        if x == j:
            i+=1
    print(j,i)

print('Algunas de las que quedaron en OTRAS fueron:')
for i in range(len(resultado2)):
    if final_num[i] == label['Otros'] and i <= 200:
        print(resultado2[i][2])

print('Generacion exitosa!')
guardar_datos(donde_guardar,clases_viejas,final_num)
reclasificador(ras_in,ras_out,donde_guardar,etiqueta)
print('Archvio reclasificado ubicado en')
print(ras_out)
