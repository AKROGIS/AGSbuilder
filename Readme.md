# ArcGIS Service Builder

This is a python task that will sync a local folder structure of web mapping
service definitions (typically as maps, and layers) with an instance of ArcGIS
Server or Portal/AGOL.  It will create, update, and delete services as needed
to match the contents of the filesystem.  It can be run as needed (when ever
the file system changes), or as a regularly scheduled task.  It does not
check for updates to data sources, so those updates will need to be triggered
separately. Whenever possible, services published to a local server should not
copy the data to the server, but rather use a network link to get live data.

It is still under development and is not yet functional.  
It is currently written for ArcGis 10.x and python 2.7.  But Pro and python3
is being considered.
