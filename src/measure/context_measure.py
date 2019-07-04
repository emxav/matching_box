# -*- coding: utf-8 -*-

"""
/***************************************************************************
 MatchingBox
                                 A QGIS plugin
 This plugins contains a set of algorithms for matching geospatial vector datasets.
                              -------------------
        begin                : 2019-05-31
        copyright            : (C) 2019 by Emerson Xavier
        email                : emerson.xavier@eb.mil.br
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = 'Emerson Xavier'
__date__ = '2019-05-31'
__copyright__ = '(C) 2019 by Emerson Xavier'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

# imports
from PyQt5.QtCore import QCoreApplication
from qgis.core import (QgsGeometry,
                       QgsRectangle,
                       QgsVectorLayer,
                       QgsWkbTypes)
import math 

class ContextMeasure( object ):
    """
    This class handles geographic context measures.
    
    For Samal et al. [2004], "geographic context refers to the spatial relationships between objects in an area",
    mainly the relationships between an object and a limited set of landmarks. For more information see:
    Samal, A., Seth, S., and Cueto, K., 2004. A feature-based approach to conflation of geospatial sources.
    International Journal of Geographical Information Science, 18 (5), 459–489.
    Available at: http://dx.doi.org/10.1080/13658810410001658076
    
    """
        
    def __init__( self ):
        """Constructor"""
            
    
    def calculateShapeContext( self,
                              pointLayer,
                              searchLength,
                              angleStep,
                              distanceStep,
                              normalize = True ):
        """
        Calculate the shape context for a set of points using the Shape Context method developed by Belongie et al.
        
        For details see: Belongie, S., Malik, J., and Puzicha, J., 2002. Shape Matching and Object Recognition Using
        Shape Contexts. IEEE Transactions on Pattern Analysis and Machine Intelligence, 24 (4), 509–522.
        Available at: http://ieeexplore.ieee.org/document/993558/?arnumber=993558
        
        @param pointLayer: Input point layer.
        @param searchLength: Maximum search lenght to consider as a neighbourhood. 4 cm at data scale is a good value.
        @param angleStep: The radial size of each bin. A value of pi/6 is a good choice. pi/6 is a good value.
        @param distanceStep: The initial distance step for the bins. It will grow by its value plus radial size. 1 mm at data scale is a good value.
        @param normalize: Normalizes the histogram count to [0, 1]. Defaults to yes.
        @returns Histogram (bin, count) for the point set.
        """
        
        # 1) initial vars - O contexto eh um histograma
        # 0
        isMulti = QgsWkbTypes.isMultiType( int(pointLayer.wkbType()) )
        
        # 1.1) Le o layer para pontos
        points = dict()
        
        for feat in pointLayer.getFeatures():
            # Processe a geom se valida
            geom = feat.geometry()

            # Chks habituais
            if geom.isEmpty():
                continue
            
            # obtem a geometria
            point = geom.asPoint() if not isMulti else geom.asMultiPoint()[0].asPoint()
            
            #points.append( point )
            points[ feat.id() ] = point
        
        # 1.2) Abordagem radial
        angleSlices = int( round( 2.*math.pi / angleStep ) )
        
        # fill distance distance map
        distStepMap = []
        currDist = distanceStep
            
        while currDist < searchLength:
            distStepMap.append( currDist )
            
            # atlz valores
            currDist += currDist * angleStep
            
        distanceSlices = len( distStepMap )+1
        slices = angleSlices * distanceSlices;
        
        # ultimo slice - para todos
        distStepMap.append( searchLength )
        
        # 2) Varre todos os pontos - jah tenho os limites, preciso acertar qm faz o q
        # saida eh um dict de histogramas
        retval = dict()
        
        for idA, ptA in points.items():
            # monta o Box
            searchBox = QgsRectangle( ptA.x()-searchLength, ptA.y()-searchLength,
                                      ptA.x()+searchLength, ptA.y()+searchLength )
            neighCount = 0            
            histog = dict() # resultado para esse ponto
            
            # checa sua relacao com os demais
            #for j, ptB in enumerate( points ):
            for idB, ptB in points.items():
                # ignora o mesmo
                #if i == j:
                if idA == idB:
                    continue

                # ignore o disjoint
                if not searchBox.contains( ptB ):
                    continue
                
                # Ok, estah na area de busca, qual o valor do ang e distancia?
                distance = ptA.distance( ptB )
                
                # distance aqui eh radial - mudanca em relacao aos demais
                if distance > searchLength:
                    continue
                
                angle = math.atan2( ptB.y() - ptA.y(), ptB.x() - ptA.x() )
                
                # angulo negativo, corrija
                if angle < 0. :
                    angle += 2.*math.pi
                    
                # 3) agora coloca no histograma
                # 3.1) angulo
                angQuad = 1. + math.floor( angle / angleStep );

                # 3.2) distancia - usando o map - um lower_bound resolveria...
                distQuad = 0
                
                for k, dist in enumerate( distStepMap ):
                    if distance < dist:
                        distQuad = k
                        break
                
                # 3.3) colocando no histograma
                idx = int( angleSlices * distQuad + angQuad )
                if histog.get(idx) == None:
                    histog[ idx ] = 1
                else:
                    histog[ idx ] += 1
                
                neighCount += 1
            
                # fim for points(search)
                
            # seguindo o padrao anterior, soh considero os 3 vizinhos
            if neighCount >= 3:
                retval[ idA ] = histog
            
            #i += 1
            # fim for points(search)
            
            # 4) zera todos que nao existem - para iterar
            """ temp comment ---- gasta muito tempo!
            for histog in retval:
                if len( histog ) == 0:
                    retval.remove( histog )
                    
                # preenche, se vazio
                for k in range (1, slices+1 ):
                    if histog.get(k) is None:
                        histog[k] = 0
            """
                    
            # 5) normalizar
            if normalize:
                for histog in retval.values():
                    sum = 0
                    
                    for val in histog.values():
                        sum += val
                        
                    # OK, agora divida - garantindo div0
                    if sum > 0:
                        for key, val in histog.items():
                            histog[key] = val/sum
                        
        
        return retval
        
        
    def distanceContext( self, histogramA, histogramB ) -> float:
        """
        Calculates the normalized distance between histograms. Result in [0,1]
        """
        
        # o retorno eh o custo
        cost = 0.
        
        # 1) Varre A e incrementa
        for key, countA in histogramA.items():
            # current/compare = countA/countB
            countB = histogramB.get( key, 0 )
            
            denominator = countA + countB
            
            # agora calcula se > 0
            if denominator > 0:
                cost += ( countA - countB )**2 / denominator
        
        # 2) Varre B, nos que nao existem em A
        for key, countB in histogramB.items():
            # compare eh o A, mas soh levo adiante se for 0
            countA = histogramA.get( key, 0 )
            
            if countA == 0:
                cost += countB
        
        # a resposta eh a metade
        return cost/2.
        
