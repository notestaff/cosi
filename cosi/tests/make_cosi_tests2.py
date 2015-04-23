#!/usr/bin/env python

#
# Script: make_cosi_tests.py
#
# Generate the scripts to call cosi test cases. 
#

import sys, os, stat, logging, argparse, collections, types, re
import __main__ as main


def makeCosiTests():

    parser = argparse.ArgumentParser( description = 'Create top-level scripts to run cosi test cases',
                                      formatter_class = argparse.ArgumentDefaultsHelpFormatter )

    parser.add_argument( '--min-model-num', type = int, help = 'minimum model id to check', required = True )
    parser.add_argument( '--max-model-num', type = int, help = 'maximum model id to check', required = True )
    parser.add_argument( '--cosi-sim-param-variants', action = DefaultAppend,
                         default = [ '', '-u .001', '-u .0001' ],
                         help = 'cosi simulation param variants' )
    parser.add_argument( '--skip', action = DefaultAppend,
                         default = 'tests/model003/t_u_0001 tests/model004/t_u_001 tests/'
                         'model004/t_u_0001 tests/model005/t_u_001 tests/model005/t_u_0001 '
                         'tests/model006/t_u_001 tests/model006/t_u_0001 tests/model014/t_u_001 '
                         'tests/model014/t_u_0001 tests/model015/t_u_0001 tests/model015/t_u_001 '
                         'tests/model013/t_u_001 tests/model013/t_u_0001 '
                         'tests/model016/t_u_0001 tests/model003/t_u_001'.split(),
                         help = 'skip these tests' )
    parser.add_argument( '--xfail', action = DefaultAppend, help = 'tests expected to fail',
                         default = () )

    logging.basicConfig( level = logging.DEBUG,
                         format='%(process)d %(asctime)s %(levelname)-8s %(filename)s:%(lineno)s %(message)s' )

    args = parser.parse_args()

    testScripts = []
    testData = []

    testNum = 1
    for modelNum in range( args.min_model_num, args.max_model_num+1 ):
        modelDir = os.path.join( 'tests', 'model%03d' % modelNum )
        testData.append( modelDir )
        for simParamVariant in args.cosi_sim_param_variants:
            testDir = os.path.join( modelDir, AddFileSfx( 't', simParamVariant ) )
            if testDir in args.skip:
                logging.info( 'skipping test: ' + testDir ) 
                continue
            if not os.path.isdir( testDir ): os.makedirs( testDir )
            runFN = os.path.join( testDir, 'run.sh' )
            with open( runFN, 'w' ) as out:
                out.write( '#!/usr/bin/env bash\n' )
                out.write( '# Run one test case.  This script is generated by $srcdir/%s.\n' %
                           ( os.path.basename( main.__file__ ) ) )
                out.write( 'set -e -o pipefail -o nounset\n' )
                out.write( '$srcdir/tests/runtest.py --test-num %d --test-dir $srcdir/%s%s %s $@\n'
                             % ( testNum, testDir,
                                 ' --use-orig-seed' if testDir in args.xfail else '',
                                 ( "--cosi-sim-params '%s'" % simParamVariant ) if simParamVariant else '' ) )
                os.fchmod( out.fileno(), stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO )

            testScripts.append( runFN )

            logging.info( 'wrote test ' + testDir )

            testNum += 1

    with open( 'tests/cositests.am', 'w' ) as out:
        out.write( 'TESTS = ' + ' '.join( testScripts ) + '\n' )
        out.write( 'XFAIL_TESTS = %s\n' % ' '.join( [ os.path.join( f, 'run.sh' ) for f in ( args.xfail or () ) ] ) )
        out.write( 'COSI_TESTDATA = ' + ' '.join( testData ) + '\n' )
    
def MakeAlphaNum( str ):
    """Return a version of the argument string, in which all non-alphanumeric chars have been replaced
    by underscores.
    """
    return re.sub( '\W+', '_', str )

def AddFileSfx( fullFileName, *sfx ):
    """Add the specified suffix to a filename, inserting it before the file extension.
    So, if the file was named ../Data/myfile.tsv and the suffix is 'verA',
    this returns '../Data/myfile_verA.tsv' .
    """

    fileName, fileExt = os.path.splitext( fullFileName if not fullFileName.endswith( '/' ) else fullFileName[:-1] )
    return ( ( fileName + Sfx( sfx ) ) if fileExt not in ( '.gz', 'bz2' ) else \
               AddFileSfx( fileName, *sfx ) ) + fileExt + ( '' if not fullFileName.endswith( '/' ) else '/' )

def Sfx( *vals ):
    """Return a suffix string based on the value: if the value is non-empty, return '_' + val; but if it is
    already empty, then just return the empty string.
    """

    def underscorify( val ):
        """prepend undescrore if needed"""
        if not val and val != 0: return ''
        noPrefix = isinstance( val, str) and val.startswith('#')
        alphaVal = MakeAlphaNum( str( val ) )
        return alphaVal[1:] if noPrefix else ( alphaVal if alphaVal.startswith( '_' ) else '_' + alphaVal )
    
    return ''.join( map( underscorify, flatten( vals ) ) )

def flatten(*args):
    """flatten(sequence) -> tuple

    Returns a single, flat tuple which contains all elements retrieved
    from the sequence and all recursively contained sub-sequences
    (iterables).

    Examples:
    >>> [1, 2, [3,4], (5,6)]
    [1, 2, [3, 4], (5, 6)]
    >>> flatten([[[1,2,3], (42,None)], [4,5], [6], 7, tuple((8,9,10))])
    (1, 2, 3, 42, None, 4, 5, 6, 7, 8, 9, 10)

    Taken from http://kogs-www.informatik.uni-hamburg.de/~meine/python_tricks

    """

    x = args[0] if len( args ) == 1 else args

    result = []
    for el in x:
        #if isinstance(el, (list, tuple)):
        if IsSeq( el ): result.extend(flatten(el))
        else: result.append(el)
    return tuple( result )

class AtomicForIsSeq(object):
    """Instances of classes derived from this class will be called _not_ sequences
    by IsSeq(), even if they otherwise look like a sequence."""
    pass

def IsSeq( val ):
    """Test if the value is a sequence but not a string or a dict.
    Derive your class from AtomicForIsSeq to force its instances to be called
    _not_ sequences by this function, regardless of anything else.
    """
    return ( isinstance( val, ( collections.Sequence, types.GeneratorType ) ) or
             ( hasattr( val, '__getitem__' ) and hasattr( val, '__len__' ) ) )  \
             and not isinstance( val, ( str, collections.Mapping, AtomicForIsSeq ) )

class DefaultAppend(argparse._AppendAction):
    def __call__(self, parser, namespace, values, option_string=None):
        items = argparse._copy.copy(argparse._ensure_value(namespace, 
                                                           self.dest, []))
        try:
            self._not_first
        except AttributeError:
            self._not_first = True
            del items[:]
        items.append(values)
        setattr(namespace, self.dest, items)

    
if __name__ == '__main__': makeCosiTests()