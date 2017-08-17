"""
A collection of configuration properties.

Note: relative paths are resolved from the working directory of the process that executes the
      script, not necessarily the location of the script.  Full paths are recommended.
      Paths can use a unix style forward slash (/) as a directory separator otherwise it must
      be a raw string (r"c:\tmp") to avoid special meaning of back slash (\)
"""

"""
The root_directory to start at when looking for documents to publish.
root_directory must be a quoted path to a folder or None.
"""
root_directory = 'c:/tmp/pub'

"""
The history_file is a path to a csv file with records of the services published.
This will be used to record what has been published by this app, for the primary
purpose of identifying services that should be removed (no longer have a source
document in the root_directory (above). history_file must be a quoted file path or
None. If no history file is provided, the app will query the server to get a list
of current services to act as the history list.  Any services found on the server
that are not in the root_folder and/or service_list will be unpublished.
The file must have a header row and at least 3 columns the first of which must be
string values for: source_path, service_folder, service_name 
"""
history_file = 'c:/tmp/pub/history.csv'

"""
The service_list is a path to a csv file with records of the services to be published.
This will be considered along with the files found in the root_directory.
This file allows the user to publish source documents not in the root_folder, provide
additional or non-default publishing parameters, and to specify if the service should
be deleted or unconditionally re-published. service_list must be a quoted path or None.
The file must have a header row and at least XX columns the first of which must be
string values for: TODO: define the service_list file format 
"""
service_list = 'c:/tmp/pub/services.csv'

"""
The default server type/connection file.  Must be a quoted string or None
A quoted string should be either 'MY_HOSTED_SERVICES' or a valid file path.
if this setting is missing, None or any other non-valid value, it will default
to 'MY_HOSTED_SERVICES'
"""
server = 'c:/tmp/pub/server.ags'

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
