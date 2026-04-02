# © 2017 Quest Inc.
# ALL RIGHTS RESERVED.

#
# Command line utilities
#

import subprocess, os, shlex, json
from .http_calls import RestTools, BodyFromTable, HttpResultAsTable
from datetime import datetime


class EnvironmentVariablesValues:

  def table(self, rows):

    header = rows[0]

    for h in header:

      if h.rfind("?") + 1 == len(h):

        env = h.rstrip("?")
        if (os.environ.has_key(env)):
          setattr(self, env, lambda: os.environ[env])
      else:
        setattr(self, "set%s" % h,  lambda x, h=h: os.environ.update({h:x}))


class ProcessUtils:

  def nowUtcDate(self):

    return datetime.utcnow().date()

  def runCommand( self, cmd ):

    subprocess.call( [ cmd ] )

  def runCommandWithArgs( self, cmd, args ):

    command = [ cmd ] + shlex.split( args )
    return self.runCommandEx( command )

  def runCommandEx( self, command ):

    if isinstance( command, str ):
      command = shlex.split( command )

    print( "------------------------------------------------" )
    print( "runCommandEx:", command )

    out = subprocess.check_output( command ).decode( "utf-8" )

    print( "output:", out )
    return out

  def getAttrFromCmdOut( self, attr, cmd ):

    out = self.runCommandEx( cmd )
    return RestTools().get_attr_by_type( json.loads( out ), attr )

  def compareValues( self, v1, v2 ):

    if ( v1 is None ):
      return False

    vType = type( v1 )

    try:
      return v1 == vType( v2 )
    except ValueError:
      return False

  def waitSecondTimesCmdResponseHasValue( self, timeout, retries, cmd, value ):

    def func( args ):

      out = self.runCommandEx( args[ "cmd" ] )
      return self.compareValues( out, value )

    return RestTools().wait( timeout, retries, func, cmd = cmd )

  def waitSecondTimesCmdResponseAttributeHasValue( self, timeout, retries, cmd, attr, value ):

    def func( args ):

      out = self.getAttrFromCmdOut( args[ "attr" ], args[ "cmd" ] )
      return self.compareValues( out, value )

    return RestTools().wait( timeout, retries, func, attr = attr, cmd = cmd )


class RunCommandWithBody( BodyFromTable ):

  def __init__( self, cmd ):

    self.cmd = cmd
    BodyFromTable.__init__( self, "", "" )

  def processRow( self, data, id ):

    command = shlex.split( self.cmd )
    command += [ json.dumps( data ) ]

    ProcessUtils().runCommandEx( command )


class CommandResultAsTable( HttpResultAsTable ):

  def __init__( self, cmd ):

    out = json.loads( ProcessUtils().runCommandEx( cmd ) )

    if ( isinstance( out, dict ) and "hits" in out ):

      self.result = out[ "hits" ][ "hits" ]

    elif ( isinstance( out, dict ) and "docs" in out ):

      self.result = out[ "docs" ]

    else:

      self.result = out

    print( "------------------------------------------------" )
    print( "CommandResultAsTable output: ", self.result )
