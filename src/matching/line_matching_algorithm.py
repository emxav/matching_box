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
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterFileDestination,
                       QgsVectorLayer,
                       QgsRectangle)
from .match_pair_manager import MatchPairManager


class LineMatchingAlgorithm(QgsProcessingAlgorithm):
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
                [QgsProcessing.TypeVectorLine]
            )
        )
        
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.TEST,
                self.tr('Test layer'),
                [QgsProcessing.TypeVectorLine]
            )
        )
            
        self.addParameter(
            QgsProcessingParameterEnum(
                self.METHOD,
                self.tr('Matching method (similarity measure + case of correspondence)'),
                options = ["TBD"],
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
                self.tr('Output file'),
                defaultValue = '/dados/temp/00_pairs.txt'
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
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
            pass
            #pairMgr = self.runEuclideanDistance( feedback, reference, test, method, threshold )
        elif method == 2 or method == 3:
            #pairMgr = self.runContextMeasure( feedback, reference, test, method, threshold )
            pass
        else:
            raise QgsProcessingException( self.tr( "Invalid match method." ), "INVALIDPARAMETERVALUE" );

       
        # 3) Salvar resposta
        outputFile = self.parameterAsFileOutput( parameters, self.OUTPUT, context )
        
        filetmp = open( outputFile, 'w' )
        filetmp.write( "# Pair manager\n" )
        filetmp.write( pairMgr.toString() )
        filetmp.close()
        
        return {self.OUTPUT: outputFile}

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Matching of line datasets'

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
        return LineMatchingAlgorithm()
