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
from enum import Enum

class MatchPairManager( object ):
    """
    This class handles with matching pairs.
    
    """
    
    class CriteriaType( Enum ):
        ISMAXIMUM = 0 # Only the maximum value in a column/row will be used (if > threshold).
        ISMINIMUM = 1 # Only the minimum value in a column/row will be used (if < threshold).
        ISABOVE   = 2 # Any value above the threshold will be used.
        ISUNDER   = 3 # Any value under the threshold will be used.
        BOTHMAX   = 4 # If maximum value is the same: A->B and B->A. Only 1:1 matches.
        BOTHMIN   = 5 # If minimum value is the same: A->B and B->A. Only 1:1 matches.        
    
    def __init__( self ):
        """Constructor"""
        self.aPairs = list()
        self.bPairs = list()
        self.aPosition = dict()
        self.bPosition = dict()
    
    
    def hasMatchesOfA( self, alfaId ):
        """Checks whether the A object exists in the manager """
        it = self.aPosition.get( alfaId )
        return it != None
    
    def hasMatchesOfB( self, betaId ):
        """Checks whether the A object exists in the manager """
        it = self.bPosition.get( betaId )
        return it != None
    
    def getMatchesOfA( self, alfaId ):
        """Returns a list of B ids which match with the alfaId """
        
        retval = []
        it = self.aPosition.get( alfaId )
        
        if it != None :
            retval = list( self.bPairs[ it ] )
                
        return retval
    
    def getMatchesOfB( self, betaId ):
        """Returns a list of A ids which match with the betaId """
        
        retval = []
        it = self.bPosition.get( betaId )
        
        if it != None :
            retval = list( self.aPairs[ it ] )
                
        return retval
        
    def toString( self, asOneToOne = False ):
        """Serializes the pairs to string using ':' as separator. """
        
        # 1) Checks
        if len( self.aPairs ) != len( self.bPairs ) or len( self.aPairs ) == 0:
            return "" #throw
        
        retval = ""
        
        # 2) Se 1:1 eh linha a linha
        if( asOneToOne ):
            # para cada alfa
            for alfaId, alfaIndex in self.aPosition.items():
                # pegue os betas
                beta = self.bPairs[ alfaIndex ]
                
                # para cada B que corresponde ao A
                for betaId in beta:
                    retval += alfaId + ':' + betaId + '\n';
            
        # 2) Nao eh 1:1, mantem o padrao "a1,a2:b1,b2"    
        else:
            for i in range( len( self.aPairs ) ):
                alfa = self.aPairs[i]
                beta = self.bPairs[i]
                
                if len( alfa ) < 1: # chk seguranca
                    continue
                
                # imprime As, depois Bs
                rowA = str()
                rowB = str()
                
                for a in alfa:
                    rowA += str(a) + ','
                for b in beta:
                    rowB += str(b) + ','
                    
                retval += rowA[0: len(rowA)-1] + ':' + rowB[0: len(rowB)-1] + '\n'
              
        
        return retval
    # end_toString

    def insertPair( self, alfaId, betaId ):
        """Insert a pair: a, b"""
        # First, checks for a and b
        ita = self.aPosition.get( alfaId )
        itb = self.bPosition.get( betaId )
    
        # if alfa exists
        if ita != None :
            # if beta exists
            if itb != None :
                # ok, both exists. So merge them, if unmerged
                if ita != itb :
                    self.merge( ita, itb )
            # Ok, no beta
            else :
                self.bPairs[ ita ].add( betaId )
                self.bPosition[ betaId ] = ita
        # Ok, no alfa
        else :
            # se b exists, invert
            if itb != None :
                self.aPairs[ itb ].add( alfaId )
                self.aPosition[ alfaId ] = itb
            # ok, no beta no alfa
            else :
                # Insere os ids, depois os indices
                self.aPairs.append( set( { alfaId } ) )
                self.bPairs.append( set( { betaId } ) )
                                   
                # indices
                self.aPosition[ alfaId ] = len( self.aPairs ) - 1
                self.bPosition[ betaId ] = len( self.aPairs ) - 1
    
    # end_insertPair
    
    def merge( self, index1, index2 ):
        """Merges two groups of pairs"""

        # 1) Initial chk
        if index1 == index2:
            return
        
        # 2) Merge lines
        self.aPairs[ index1 ].union( self.aPairs[ index2 ] )
        self.bPairs[ index1 ].union( self.bPairs[ index2 ] )
        
        # 3) O novo indice eh o index1 para todos
        for i in self.aPairs[ index2 ]:
            self.aPosition[ i ] = index1
            
        for j in self.bPairs[ index2 ]:
            self.bPosition[ j ] = index1
    
    # end_merge
    
    def buildFromMatrix( self, matrix, criteriaType, threshold ):
        """
        A complete method to build match pairs from a matrix of distances between objects.
        
        matrix : two-dimensional list which contains the distances and object IDs (first column, firstrow).
        criteriaType : which criteria should used to establishes the matching. See CriteriaType for detais.
        threshold : minimum or maximum value, depending on the criteria, to establishes a similarity.
        """
        
        # 1) Check parameters
        # at least 2 rows x 2 cols
        if len( matrix ) < 2 :
            return # throw
        if len( matrix[0] ) < 2:
            return # throw
        
        nrows, ncols = len( matrix ), len( matrix[0] )
        
        # 2) Criteria ISMAXIMUM
        if criteriaType == self.CriteriaType.ISMAXIMUM:
            # 2.1) ismax - cols
            for j in range( 1, ncols ):
                imax = 0
                maxValue = float('-inf')
                
                for i in range( 1, nrows ):
                    if matrix[i][j] > maxValue:
                        imax = i
                        maxValue = matrix[i][j]
                        
                # por fim, insere o par ref/test, se dist < threshold
                if maxValue > threshold:
                    self.insertPair( matrix[0][j], matrix[imax][0] )
                    
            # 2.2) ismax - rows
            for i in range( 1, nrows ):
                jmax = 0
                maxValue = float('-inf')
                
                for j in range( 1, ncols ):
                    if matrix[i][j] > maxValue:
                        jmax = j
                        maxValue = matrix[i][j]
                        
                # por fim, insere o par ref/test, se dist > threshold
                if maxValue > threshold:
                    self.insertPair( matrix[0][jmax], matrix[i][0] )
                    
        # 3) ISMINIMUM
        elif criteriaType == self.CriteriaType.ISMINIMUM:
            # 3.1) ismin - cols
            for j in range( 1, ncols ):
                imin = 0
                minValue = float('inf')
                
                for i in range( 1, nrows ):
                    if matrix[i][j] < minValue:
                        imin = i
                        minValue = matrix[i][j]
                        
                # por fim, insere o par ref/test, se dist < threshold
                if minValue < threshold:
                    self.insertPair( matrix[0][j], matrix[imin][0] )
                    
            # 3.2) ismin - rows
            for i in range( 1, nrows ):
                jmin = 0
                minValue = float('inf')
                
                for j in range( 1, ncols ):
                    if matrix[i][j] < minValue:
                        jmin = j
                        minValue = matrix[i][j]
                        
                # por fim, insere o par ref/test, se dist < threshold
                if minValue < threshold:
                    self.insertPair( matrix[0][jmin], matrix[i][0] )
                    
        # 4) ISABOVE
        elif criteriaType == self.CriteriaType.ISABOVE:
            # 4.1) Isabove = cols + rows
            for j in range( 1, ncols ):
                for i in range( 1, nrows ):
                    # qq coisa maior que o threshold eh par 
                    if matrix[i][j] > threshold:
                        self.insertPair( matrix[0][j], matrix[i][0] )
                    
        # 5) ISUNDER
        elif criteriaType == self.CriteriaType.ISUNDER:
            # 5.1) Isunder = cols + rows
            for j in range( 1, ncols ):
                for i in range( 1, nrows ):
                    # qq coisa menor que o threshold eh par 
                    if matrix[i][j] < threshold:
                        self.insertPair( matrix[0][j], matrix[i][0] )
        
        # 6) BOTHMAX
        elif criteriaType == self.CriteriaType.BOTHMAX:
            maxCol_Lin = dict()
            
            # 6.1) ismax - cols
            for j in range( 1, ncols ):
                imax = 0
                maxValue = float('-inf')
                
                for i in range( 1, nrows ):
                    if matrix[i][j] > maxValue:
                        imax = i
                        maxValue = matrix[i][j]
                        
                # por fim, insere o par ref/test, se dist < threshold, no temp
                if maxValue > threshold:
                    maxCol_Lin[ matrix[0][j] ] = matrix[imax][0]
                    
            # 6.2) ismax - rows
            for i in range( 1, nrows ):
                jmax = 0
                maxValue = float('-inf')
                
                for j in range( 1, ncols ):
                    if matrix[i][j] > maxValue:
                        jmax = j
                        maxValue = matrix[i][j]
                        
                # por fim, insere o par ref/test, se dist > threshold e na lista temp
                if maxValue > threshold:
                    it = maxCol_Lin.get( matrix[0][jmax] )
                    
                    if it == matrix[i][0]:
                        self.insertPair( matrix[0][jmax], matrix[i][0] )
                    
        # 7) BOTHMIN
        elif criteriaType == self.CriteriaType.BOTHMIN:
            minCol_Lin = dict()
            
            # 7.1) ismin - cols
            for j in range( 1, ncols ):
                imin = 0
                minValue = float('inf')
                
                for i in range( 1, nrows ):
                    if matrix[i][j] < minValue:
                        imin = i
                        minValue = matrix[i][j]
                        
                # por fim, insere o par ref/test, se dist < threshold, numa lista temp
                if minValue < threshold:
                    minCol_Lin[ matrix[0][j] ] = matrix[imin][0]
                    
            # 7.2) ismin - rows
            for i in range( 1, nrows ):
                jmin = 0
                minValue = float('inf')
                
                for j in range( 1, ncols ):
                    if matrix[i][j] < minValue:
                        jmin = j
                        minValue = matrix[i][j]
                        
                # por fim, insere o par ref/test, se dist < threshold e na lista_temp
                if minValue < threshold:
                    it = minCol_Lin.get( matrix[0][jmin] ) 
                    
                    if it == matrix[i][0]:
                        self.insertPair( matrix[0][jmin], matrix[i][0] )
        else:
            raise Exception("Invalid criteria.", "InvalidParameterValue")
        
        # end_buildFromMatrix
        
    
    
