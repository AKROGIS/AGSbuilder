"""
A collection of configuration properties.

Note: relative paths are resolved from the working directory of the process that executes the
      script, not necessarily the location of the script.
"""

"""
The root directory to start at when looking for documents to publish
Path can use a unix style forward slash (/) as a directory separator 
otherwise it must be a raw string (r"c:\tmp") to avoid special meaning of back slash (\)
"""
root_directory = 'c:/tmp/pubtest'
