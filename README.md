# CropRotations_2019

Contains the winter and summer crop rotation aglorithms.

This repository contains the algorithm used to create and classify crop rotations in our published paper *"Temporal integration of remote-sensing land cover maps to identify crop rotation patterns in a semiarid region of Argentina"* [[1]](https://doi.org/10.1002/agj2.20758).

The algorithm is based on the Dr. Ritvik Sahajpal's algorithm, which can be found on [here](https://github.com/ritviksahajpal/CropRotations),
and is adapted for Argentinean crops. It also performs the reclassification of the crop sequences into new groups.

In the corresponding folder(winter or summer):
1.) Run the program rotacion-cultivo.py to build the file "rotaciones_existentes.xls", which generates all the existing rotations.
2.) Run the program clasificador.py as to reclassify the existing rotations in the different categories selected. 

[1] *"Temporal integration of remote-sensing land cover maps to identify crop rotation patterns in a semiarid region of Argentina"* A.M. Aoki, J.I. Robledo, R.C. Izaurralde, M.G. Balzarini, Agronomy Journal 113(4), pp. 3232-3243. [https://doi.org/10.1002/agj2.20758](https://doi.org/10.1002/agj2.20758)


### Español

Contiene las rotaciones estivales e invernales

En la respectiva carpeta src (en estival o invernal):
1.) Correr el programa rotacion-cultivo.py para armar el archivo "rotaiones_existentes.xls"
2.) Correr el programa clasificador.py para para reclasificar las rotaciones existentes en las distintas categorias ensambladas.
