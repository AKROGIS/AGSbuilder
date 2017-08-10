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

"""
The default server type/connection file.  Must be a quoted string or None
A quoted string should be either 'MY_HOSTED_SERVICES' or a valid file path.
if this setting is missing, None or any other non-valid value, it will default
to 'MY_HOSTED_SERVICES'
"""
server = 'c:/tmp/pubtest/server.ags'

"""
The Server URL is used to check if a service exists before publishing,
And to connect to the server for unpublishing.  If the server URL is not
provided, it will be extracted from the AGS file provided in the service property
"""
server_url = None

"""
The Admin username and password are used to connect to the server_url with the
ArcGIS ReST API to Stop/Delete services.  Without these properties, the
unpublish feature will not be available.  If they are None or not provided,
they can be provided on the command line.
They must be None, or quoted text
"""
admin_username = 'bigwig'
admin_password = 'secret'
