'''-------------------------------------------------------------------------------
 Tool Name:   CreateNetworkConnectivityFile
 Source Name: CreateNetworkConnectivityFile.py
 Version:     ArcGIS 10.2
 License:     Apache 2.0
 Author:      Environmental Systems Research Institute Inc.
 Updated by:  Environmental Systems Research Institute Inc.
 Description: Generates CSV file of stream network connectivity for RAPID based on
              the input Drainage Line feature class with HydroID and NextDownID fields.
 History:     Initial coding - 07/07/2014, version 1.0
 Updated:     Version 1.0, 10/23/2014 Added comments about the order of rows in tool output
              Version 1.1, 10/24/2014 Modified file and tool names
              Version 1.1, 02/03/2015 Bug fixing - input parameter indices
              Version 1.1, 02/17/2015 Bug fixing - "HydroID", "NextDownID" in the exact
                upper/lower cases as the required field names in input drainage line feature class
              Version 1.1, 02/19/2015 Enhancement - Added error handling for message updating of
                input drainage line features
              Version 1.1, 04/20/2015 Bug fixing - "HydroID", "NextDownID" (case insensitive) as
                the required field names in the input drainage line feature class
              Version 2.0, 02/29/2015 - Used numpy array instead to make program faster
                (adpated from Alan D. Snow, US Army ERDC)
-------------------------------------------------------------------------------'''
import os
import arcpy
import csv
import numpy as NUM

class CreateNetworkConnectivityFile(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Create Connectivity File"
        self.description = "Creates Network Connectivity input CSV file for RAPID \
        based on the Drainage Line feature class with HydroID and NextDownID fields"
        self.canRunInBackground = False
        self.category = "Preprocessing"

    def getParameterInfo(self):
        """Define parameter definitions"""
        in_drainage_line = arcpy.Parameter(
                    displayName = 'Input Drainage Line Features',
                    name = 'in_drainage_line_features',
                    datatype = 'GPFeatureLayer',
                    parameterType = 'Required',
                    direction = 'Input')
        in_drainage_line.filter.list = ['Polyline']

        out_csv_file = arcpy.Parameter(
                    displayName = 'Output Network Connectivity File',
                    name = 'out_network_connectivity_file',
                    datatype = 'DEFile',
                    parameterType = 'Required',
                    direction = 'Output')

        in_max_nbr_upstream = arcpy.Parameter(
                    displayName = 'Maximum Number of Upstream Reaches',
                    name = 'max_nbr_upstreams',
                    datatype = 'GPLong',
                    parameterType = 'Optional',
                    direction = 'Input')

        return [in_drainage_line,
                out_csv_file,
                in_max_nbr_upstream]

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[1].altered:
            (dirnm, basenm) = os.path.split(parameters[1].valueAsText)
            if not basenm.endswith(".csv"):
                parameters[1].value = os.path.join(
                    dirnm, "{}.csv".format(basenm))
        else:
            scratchWorkspace = arcpy.env.scratchWorkspace
            if not scratchWorkspace:
                scratchWorkspace = arcpy.env.scratchGDB
            parameters[1].value = os.path.join(
                scratchWorkspace, "rapid_connect.csv")
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        try:
            if parameters[0].altered:
                field_names = []
                fields = arcpy.ListFields(parameters[0].valueAsText)
                for field in fields:
                    field_names.append(field.baseName.upper())
                if not ("HYDROID" in field_names and "NEXTDOWNID" in field_names):
                    parameters[0].setErrorMessage("Input Drainage Line must contain HydroID and NextDownID.")
        except Exception as e:
            parameters[0].setErrorMessage(e.message)

        if parameters[2].altered:
            max_nbr = parameters[2].value
            if (max_nbr < 0 or max_nbr > 12):
                parameters[2].setErrorMessage("Input Maximum Number of Upstreams must be within [1, 12]")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        in_drainage_line = parameters[0].valueAsText
        out_csv_file = parameters[1].valueAsText
        in_max_nbr_upstreams = parameters[2].value

        fields = ['HydroID', 'NextDownID']
        stream_id = fields[0]
        next_down_id = fields[1]

        list_all = []
        max_count_Upstream = 0
        '''The script line below makes sure that rows in the output connectivity
           file are arranged in ascending order of HydroIDs of stream segements'''
        np_table = arcpy.da.TableToNumPyArray(in_drainage_line, fields)
        for hydroid in NUM.sort(np_table[stream_id]):
            # find the HydroID of the upstreams
            list_upstreamID = np_table[np_table[next_down_id]==hydroid][stream_id]
            # count the total number of the upstreams
            count_upstream = len(list_upstreamID)
            if count_upstream > max_count_Upstream:
                max_count_Upstream = count_upstream
            # replace the nextDownID with 0 if it equals to -1 (no next downstream)
            nextDownID = np_table[np_table[stream_id]==hydroid][next_down_id][0]
            if nextDownID == -1:
                nextDownID = 0
             # append the list of Stream HydroID, NextDownID, Count of Upstream ID, and  HydroID of each Upstream into a larger list
            list_all.append(NUM.concatenate([NUM.array([hydroid,nextDownID,count_upstream]),list_upstreamID]))

        # If the input maximum number of upstreams is none, the actual max number of upstreams is used
        if in_max_nbr_upstreams == None:
            in_max_nbr_upstreams = max_count_Upstream

        with open(out_csv_file,'wb') as csvfile:
            connectwriter = csv.writer(csvfile, dialect='excel')

            for row_list in list_all:
                out = NUM.concatenate([row_list, NUM.array([0 for i in xrange(in_max_nbr_upstreams - row_list[2])])])
                connectwriter.writerow(out.astype(int))


        return

