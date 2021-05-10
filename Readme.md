# ArcGIS Service Builder

**NOTE**
This project was abandoned and archived 5/2021 Due to challanges with the 
differences between Pro and ArcMap, and unecessary complexity. The recommended
solution is a collection of Pro projects with publishable maps organized in
a well known folder with a readme file to describe any special instructions.
These maps can be updated and republished as often as necessary to keep the
services current. For the AKRO GIS team, there are Pro projects organized in
a services folder under each server running ArcGIS Server (See
`T:\Projects\AKR\ArcGIS Server`).  A similar folder structure can be adopted
for AGOL and Portal.

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

## Build

There is no build required to deploy this project

## Deploy

1) Copy files to a server location
2) Build file system (on GIS Team Drive) of services to publish
3) Create CSV of special case service
4) Edit configuration parameters
5) Create and deploy a schedule task

## Using

The script can be run from the command line with the options as shown in
[`publisher.py`](https://github.com/AKROGIS/AGSbuilder/blob/a51a3633759cbdc067fef5ba39dfde44a92de23b/publisher.py#L36-L75)
