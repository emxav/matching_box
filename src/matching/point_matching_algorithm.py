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

from PyQt5.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingException,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterFileDestination,
                       QgsVectorLayer,
                       QgsRectangle,
                       QgsWkbTypes)
from .match_pair_manager import MatchPairManager
from ..measure.context_measure import ContextMeasure
import math


class PointMatchingAlgorithm(QgsProcessingAlgorithm):
    """
    This algorithm performs the matching between two point datasets using
    some methods implemented.

    Similarity distances:
    - Euclidean distance
    - Context measure (see class ContextMeasure)
    
    Criteria:
    - Closer criteria: m:n matching case
    - Both nearest: 1:1 matching case 
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    REFERENCE = 'REFERENCE'
    TEST = 'TEST'
    METHOD = 'METHOD'
    THRESHOLD = 'THRESHOLD'
    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source. It can have any kind of
        # geometry.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.REFERENCE,
                self.tr('Reference layer'),
                [QgsProcessing.TypeVectorPoint]
            )
        )
        
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.TEST,
                self.tr('Test layer'),
                [QgsProcessing.TypeVectorPoint]
            )
        )
            
        self.addParameter(
            QgsProcessingParameterEnum(
                self.METHOD,
                self.tr('Matching method (similarity measure + case of correspondence)'),
                options = ["Euclidean - closer", "Euclidean - both nearest", "Context - closer", "Context - both nearest"],
                defaultValue = 0
            )
        )
            
        self.addParameter(
            QgsProcessingParameterNumber(
                self.THRESHOLD,
                self.tr('Distance threshold (depends on the method)'),
                minValue=0,
                type=QgsProcessingParameterNumber.Double,
                defaultValue=1.
            )
        )

        # Return
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT,
                self.tr('Output file')
                #,defaultValue = '/dados/temp/00_pairs.txt'
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        
        NOTE: MultiPoints will be treated as a single point (the first).
        """
    
        # 1) get input parameters
        reference = self.parameterAsVectorLayer( parameters, self.REFERENCE, context )
        test      = self.parameterAsVectorLayer( parameters, self.TEST,      context )
        method    = self.parameterAsEnum(        parameters, self.METHOD,    context )
        threshold = self.parameterAsDouble(      parameters, self.THRESHOLD, context )
        
        # 2) Common tests
        if reference.featureCount() < 1 or test.featureCount() < 1:
            raise QgsProcessingException( self.tr( "Empty vector layer." ), "INVALIDPARAMETERVALUE" );
        
        # 3) Run 
        if method == 0 or method == 1:
            pairMgr = self.runEuclideanDistance( feedback, reference, test, method, threshold )
        elif method == 2 or method == 3:
            pairMgr = self.runContextMeasure( feedback, reference, test, method, threshold )
        else:
            raise QgsProcessingException( self.tr( "Invalid match method." ), "INVALIDPARAMETERVALUE" );

       
        # 3) Salvar resposta
        outputFile = self.parameterAsFileOutput( parameters, self.OUTPUT, context )
        
        filetmp = open( outputFile, 'w' )
        filetmp.write( "# Pair manager\n" )
        filetmp.write( pairMgr.toString() )
        filetmp.close()
        
        return {self.OUTPUT: outputFile}
        
        #print( pairMgr.toString() )
        #return {}

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Matching of point datasets'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self.name())

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(self.groupId())

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Algorithms for feature matching'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return PointMatchingAlgorithm()
    
    def shortHelpString( self ):
        """Returns a localised short helper string for the algorithm, that appears at right."""
        
        return """The <b>threshold</b> parameter depends most of the matching method.<br/>
For an <i>Euclidean</i> method, it should be a distance in the SRS' units.<br/>
For a <i>Context</i> method, it should be between [0, 1] interval, in which 0 means high similarity.<br/>
"""
    
        """Internals"""
    
    def runEuclideanDistance( self, feedback, reference, test, method, threshold ) -> MatchPairManager:
        """
        Processing the matching using Euclidean distance.
        
        Return: the MatchPairManager
        """
      
        # 2) test parameters
        testExtent = test.extent()
        maxDistance = testExtent.width() if testExtent.width() > testExtent.height() else testExtent.height()
        
        if maxDistance < 2. * threshold:
            raise Exception( self.tr( "Test data with a small bounding box. It should be at least twice the threshold." ), "INVALIDPARAMETERVALUE" );
        
        refIsMulti  = QgsWkbTypes.isMultiType( int(reference.wkbType()) )
        testIsMulti = QgsWkbTypes.isMultiType( int(test.wkbType()) )
        
        # 3) Run the processing
        ncols = reference.featureCount()
        nrows = test.featureCount()
        
        distMatrix = [[ int(maxDistance) for x in range(ncols+1) ] for y in range(nrows+1) ] 

        # 3.1) Compute the number of steps to display within the progress bar and
        # get features from source
        total = 100.0 / ncols
        
        # 3.2) Itera sobre os ref e procura o equivalente em test
        for j, refFeat in enumerate( reference.getFeatures() ):
            # running chks
            if feedback.isCanceled():
                break
            
            # Coloque o ID no lugar
            distMatrix[0][j+1] = refFeat.id() #refFeat.id()
            
            refGeom = refFeat.geometry()
            
            # Chks habituais
            if refGeom.isEmpty():
                continue
            
            # obtem a geometria e monta o box de busca
            refPoint = refGeom.asPoint() if not refIsMulti else refGeom.asMultiPoint()[0].asPoint()
                       
            refBox = QgsRectangle( refPoint.x()-threshold, refPoint.y()-threshold,
                                   refPoint.x()+threshold, refPoint.y()+threshold )
            
            for i, testFeat in enumerate( test.getFeatures() ):
                
                # Coloque o ID no lugar - repetindo
                distMatrix[i+1][0] = testFeat.id()  #testFeat.id()
                
                testGeom = testFeat.geometry()
            
                # Chks habituais
                if testGeom.isEmpty():
                    continue
                
                # obtem a geometria
                testPoint = testGeom.asPoint() if not testIsMulti else testGeom.asMultiPoint()[0].asPoint()
                            
                # ignore o disjoint
                if not refBox.contains( testPoint ):
                    continue
                
                # agora sim, o que a gente veio fazer aqui: distance
                distMatrix[i+1][j+1] = refPoint.distance( testPoint )            
        
            feedback.setProgress( int(j * total) )
    
        # debug
        
        # 4) OK, tenho tudo, faltam os pares
        pairMgr = MatchPairManager()
        
        # check o criteria 
        criteria = pairMgr.CriteriaType.ISMINIMUM if method % 2 == 0 else pairMgr.CriteriaType.BOTHMIN
        
        pairMgr.buildFromMatrix( distMatrix, criteria, threshold )
        
        return pairMgr
        
    
    
    def runContextMeasure( self, feedback, reference, test, method, threshold ) -> MatchPairManager:
        """
        Processing the matching using Context measure.
        
        Return: the MatchPairManager
        """
        
        # 1) Initial calculus
        # 1.1) Descobrir quem eh menor, que serve de param 
        # SearchLength = Diagonal / PointCount * 20  -> distance for 20 points in Diagonal
        boxA = reference.extent()
        boxB = test.extent()
        
        searchLengthA = math.sqrt( boxA.width()**2 + boxA.height()**2 ) / reference.featureCount() * 20.
        searchLengthB = math.sqrt( boxB.width()**2 + boxB.height()**2 ) / test.featureCount() * 20.
        
        # parameters for context
        cttSearchLength = searchLengthA if searchLengthA > searchLengthB else searchLengthB
        cttDistanceStep = cttSearchLength / 20.
        cttAngleStep = math.pi/6.
        
        # outros
        refIsMulti  = QgsWkbTypes.isMultiType( int(reference.wkbType()) )
        testIsMulti = QgsWkbTypes.isMultiType( int(test.wkbType()) )
        
        # 2) Calculate the context
        context = ContextMeasure()
        
        shapeContextA = context.calculateShapeContext( reference, cttSearchLength, cttAngleStep, cttDistanceStep )
        feedback.setProgress( 10 )
        
        shapeContextB = context.calculateShapeContext( test,      cttSearchLength, cttAngleStep, cttDistanceStep )
        feedback.setProgress( 20 )

        # 3) Run the processing
        ncols = reference.featureCount()
        nrows = test.featureCount()
        
        distMatrix = [[ 1. for x in range(ncols+1) ] for y in range(nrows+1) ] 

        # 3.1) Compute the number of steps to display within the progress bar and
        # get features from source
        total = 80.0 / ncols
        
        # 3.2) Itera sobre os ref e procura o equivalente em test
        for j, refFeat in enumerate( reference.getFeatures() ):
            # running chks
            if feedback.isCanceled():
                break
            
            # Coloque o ID no lugar
            distMatrix[0][j+1] = refFeat.id()
            
            refGeom = refFeat.geometry()
            refHist = shapeContextA.get( refFeat.id() )
            
            # Chks habituais
            if refGeom.isEmpty() or refHist is None:
                continue
            
            # obtem a geometria e monta o box de busca - baseado no cttSearchLength
            refPoint = refGeom.asPoint() if not refIsMulti else refGeom.asMultiPoint()[0].asPoint()
                       
            refBox = QgsRectangle( refPoint.x()-cttSearchLength, refPoint.y()-cttSearchLength,
                                   refPoint.x()+cttSearchLength, refPoint.y()+cttSearchLength )
            
            for i, testFeat in enumerate( test.getFeatures() ):
                
                # Coloque o ID no lugar - repetindo
                distMatrix[i+1][0] = testFeat.id()
                
                testGeom = testFeat.geometry()
                testHist = shapeContextB.get( testFeat.id() )
            
                # Chks habituais
                if testGeom.isEmpty() or testHist is None:
                    continue
                
                # obtem a geometria
                testPoint = testGeom.asPoint() if not testIsMulti else testGeom.asMultiPoint()[0].asPoint()
                            
                # ignore o disjoint
                if not refBox.contains( testPoint ):
                    continue
                
                # agora sim, o que a gente veio fazer aqui: distance
                distMatrix[i+1][j+1] = context.distanceContext( refHist, testHist )        
        
            feedback.setProgress( 20 + int(j * total) )
        # fim for_feat
        
        # debug

        
        # 4) OK, tenho tudo, faltam os pares
        pairMgr = MatchPairManager()
        
        # check o criteria 
        criteria = pairMgr.CriteriaType.ISMINIMUM if method % 2 == 0 else pairMgr.CriteriaType.BOTHMIN
        
        pairMgr.buildFromMatrix( distMatrix, criteria, threshold )
        
        return pairMgr;
        
        
        
    
    
