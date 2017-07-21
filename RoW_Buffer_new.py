# -*- coding: utf-8 -*-

# A folder called natsort should have been included with the script
# and should be placed in the same folder as this .py file.

import arcpy, os, sys, natsort
from arcpy import env
from natsort import natsorted

arcpy.Delete_management(ur'in_memory')

try:
    del selectLines
    # arcpy.AddMessage(u'Deleted selectLines')
except:
    pass
    
lyrList = [u'lyr_RoW_Buffer_0', u'temp_lyr_rowLines', u'lyr_rowLines', u'temp_trsPolygons', u'lyr_trsPolygons', u'trLyr', u'lyr_intersect', u'lyr_buffer', u'lyr_trsSelect', u'lyr_intersectSelect']

for i in lyrList:
    if arcpy.Exists(i):
        arcpy.Delete_management(i)

def ReorderFields(table, out_table, field_order, add_missing = True):
    """ 
    Reorders fields in input featureclass/table
    :table:         input table (fc, table, layer, etc)
    :out_table:     output table (fc, table, layer, etc)
    :field_order:   order of fields (objectid, shape not necessary)
    :add_missing:   add missing fields to end if True (leave out if False)
    -> path to output table
    """
    existing_fields = arcpy.ListFields(table)
    existing_field_names = [field.name for field in existing_fields]

    existing_mapping = arcpy.FieldMappings()
    existing_mapping.addTable(table)

    new_mapping = arcpy.FieldMappings()

    def add_mapping(field_name):
        mapping_index = existing_mapping.findFieldMapIndex(field_name)

        # required fields (OBJECTID, etc) will not be in existing mappings
        # they are added automatically
        if mapping_index != -1:
            field_map = existing_mapping.fieldMappings[mapping_index]
            new_mapping.addFieldMap(field_map)

    # add user fields from field_order
    for field_name in field_order:
        if field_name not in existing_field_names:
            raise Exception(u'Field: {} not in {}'.format(field_name, table))

        add_mapping(field_name)

    # add missing fields at end
    if add_missing:
        missing_fields = [f for f in existing_field_names if f not in field_order]
        for field_name in missing_fields:
            add_mapping(field_name)

    # use merge with single input just to use new field_mappings
    arcpy.Merge_management(table, out_table, new_mapping)
    return out_table
        
def GetWorkspace(fc):
    # Set workspace to geodatabase containing the new dispensary points
    dirname = unicode(os.path.dirname(arcpy.Describe(fc).catalogPath))
    desc = arcpy.Describe(dirname)

    # Checks to see if the path of the layer is a feature dataset and if so changes the output path
    # to the geodatabase
    if hasattr(desc, u'datasetType') and desc.datasetType == u'FeatureDataset':
        dirname = unicode(os.path.dirname(dirname))
    return dirname

def WhereClauseFromList(table, field, valueList):
    """Takes a list of values and constructs a SQL WHERE
    clause to select those values within a given field and table."""

    # Add DBMS-specific field delimiters
    fieldDelimited = arcpy.AddFieldDelimiters(arcpy.Describe(table).path, field)

    # Determine field type
    fieldType = arcpy.ListFields(table, field)[0].type

    # Add single-quotes for string field values
    if unicode(fieldType) == u'String':
        valueList = [u'\'{}\''.format(value) for value in valueList]

    # Format WHERE clause in the form of an IN statement
    whereClause = u'{} IN({})'.format(fieldDelimited, u', '.join(map(unicode, valueList)))
    return whereClause
    
# Setting this to FALSE to ensure script is smart
env.overwriteOutput = False

rowLines = arcpy.GetParameterAsText(0)
trsPolygons = arcpy.GetParameterAsText(1)
env.workspace = arcpy.GetParameterAsText(2)
bufferTxt = arcpy.GetParameterAsText(3)
keNumber = arcpy.GetParameterAsText(4)

# arcpy.AddMessage(u'Workspace: {}'.format(env.workspace))

testList = [u'TEST_lyr_buffer', u'TEST_lyr_intersect', u'TEST_trsPolygons']

for i in testList:
    if arcpy.Exists(i):
        arcpy.Delete_management(i)

mxd = arcpy.mapping.MapDocument(u'CURRENT')
df = arcpy.mapping.ListDataFrames(mxd)[0]

# Checks if a value exists in keNumber and if the length is less than 50
if keNumber and len(keNumber) > 50:
    arcpy.AddError(u'ERROR: KE Number must be 50 characters or less.')
    sys.exit(u'Script failed.')
    
# Uses in_memory workspace to create intermediate feature classes
# This way you don't have lots of temporary files floating around
# Deletes in_memory first to ensure it's fresh

try:
    bufferFloat = float(bufferTxt)
    if bufferFloat.is_integer():
        bufferTag = int(bufferFloat) * 2
    else:
        bufferTag = bufferFloat * 2
    bufferWidth = u'{} feet'.format(unicode(bufferFloat))
except:
    arcpy.AddError(u'Buffer width must be a numeric value.')
    sys.exit(u'Script failed.')

selectLines = arcpy.Describe(rowLines)

# arcpy.AddMessage(u'FID Set: {}'.format(selectLines.FIDset))  

if not selectLines.FIDset:
    arcpy.AddError(u'Please have line features selected.')
    sys.exit()
else:
    arcpy.CopyFeatures_management(rowLines, ur'in_memory\inMem_rowLines')
    arcpy.MakeFeatureLayer_management(ur'in_memory\inMem_rowLines', u'lyr_rowLines')

arcpy.Buffer_analysis(u'lyr_rowLines', ur'in_memory\inMem_lyr_buffer', bufferWidth, method = u'PLANAR')
# arcpy.CopyFeatures_management(ur'in_memory\inMem_lyr_buffer', u'TEST_lyr_buffer')

arcpy.MakeFeatureLayer_management(ur'in_memory\inMem_lyr_buffer', u'lyr_buffer')

arcpy.AddMessage(u'\nGenerated {} foot buffer.'.format(unicode(bufferTag)))

# arcpy.AddMessage(u'\nBuffer fields: {}'.format([i.name for i in arcpy.ListFields(u'lyr_buffer')]))

del selectLines

arcpy.MakeFeatureLayer_management(trsPolygons, u'temp_trsPolygons')

arcpy.SelectLayerByLocation_management(u'temp_trsPolygons', select_features = u'lyr_buffer', selection_type = u'NEW_SELECTION')
arcpy.CopyFeatures_management(u'temp_trsPolygons', ur'in_memory\inMem_trsPolygons')
# arcpy.FeatureClassToFeatureClass_conversion(u'temp_trsPolygons', env.workspace, u'TEST_trsPolygons')

arcpy.MakeFeatureLayer_management(ur'in_memory\inMem_trsPolygons', u'lyr_trsPolygons')

arcpy.Intersect_analysis([u'lyr_buffer', u'lyr_trsPolygons'], ur'in_memory\inMem_lyr_intersect')
# arcpy.CopyFeatures_management(ur'in_memory\inMem_lyr_intersect', u'TEST_lyr_intersect')

arcpy.MakeFeatureLayer_management(ur'in_memory\inMem_lyr_intersect', u'lyr_intersect')

arcpy.AddMessage(u'Generated intersect of buffer with TRS layer.\n')

# arcpy.AddMessage(u'\nIntersect fields: {}'.format([i.name for i in arcpy.ListFields(u'lyr_intersect')]))

trsList = [u'OID@', u'TOWNSHIP', u'RANGE', u'SECTION']
trsSet = set()
trSet = set()

with arcpy.da.SearchCursor(u'lyr_trsPolygons', trsList) as cursor:
    for row in cursor:
        township = row[1]
        range = row[2]
        section = row[3]
        
        trsSet.update([(township, range, section)])
        trSet.update([(township, range)])
    
del cursor
        
orderedTRS = natsorted([i for i in trsSet])
orderedTR = natsorted([i for i in trSet])
trDict = {i:[0] for i in orderedTR}

# arcpy.AddMessage(u'Ordered TRS: {}'.format(orderedTRS))
# arcpy.AddMessage(u'Ordered TR: {}'.format(orderedTR))
# arcpy.AddMessage(u'TR list: {}'.format(trDict))

for trs in orderedTRS:
    
    tempList = [u'lyr_trsSelect', u'lyr_intersectSelect']
    
    for i in tempList:
        if arcpy.Exists(i):
            arcpy.Delete_management(i)
            
    twn = trs[0]
    twnStrip = int(u''.join([i for i in twn if i.isdigit() or i == u'.']))
    rng = trs[1]
    rngStrip = int(u''.join([i for i in rng if i.isdigit() or i == u'.']))
    sec = trs[2]
    secStrip = int(u''.join([i for i in sec if i.isdigit() or i == u'.']))
    
    arcpy.AddMessage(u'Processing T {} R {} S {}'.format(twn, rng, sec))
    
    trsWhere = u'TOWNSHIP = \'{}\' AND RANGE = \'{}\' AND SECTION = \'{}\''.format(twn, rng, sec)
    
    arcpy.SelectLayerByAttribute_management(u'lyr_trsPolygons', selection_type = u'NEW_SELECTION', where_clause = trsWhere)
    # arcpy.CopyFeatures_management(u'lyr_trsPolygons', u'lyr_trsSelect')
    # arcpy.SelectLayerByAttribute_management(u'lyr_trsPolygons', selection_type = u'CLEAR_SELECTION')
    
    arcpy.SelectLayerByLocation_management(u'lyr_intersect', overlap_type = u'HAVE_THEIR_CENTER_IN', select_features = u'lyr_trsPolygons')
    # arcpy.CopyFeatures_management(u'lyr_intersect', u'lyr_intersectSelect')
    # arcpy.SelectLayerByAttribute_management(u'lyr_intersect', selection_type = u'CLEAR_SELECTION')
    
    dissolveNum = 0
    
    if keNumber and keNumber != u'#':
        dissolveTag = ur'inMem_T_{}_R_{}_S_{}_KE_{}'.format(twn, rng, sec, keNumber.replace(u'-', u'_').replace(u' ', u'_'))
    else:
        dissolveTag = ur'inMem_T_{}_R_{}_S'.format(twn, rng, sec)
    
    dissolveName = dissolveTag.replace(u' ', u'_').replace(u'.', u'_')
    
    while arcpy.Exists(ur'in_memory\{}'.format(dissolveName)):
        dissolveNum += 1
        dissolveName = ur'{}_{}'.format(dissolveTag, unicode(dissolveNum))
     
    inMem_dissolveName = ur'in_memory\{}'.format(dissolveName)
    arcpy.Dissolve_management(u'lyr_intersect', inMem_dissolveName, [u'LANDNUM', u'QUAD', u'COUNTY', u'COUNTYNM', u'FUND', u'PARCEL', u'EDIT_DATE', u'TSSW_ACRES', u'KE_NUMBER', u'COMMENT'])
    
    # arcpy.AddMessage('TR dict {} {}: {}'.format(twn, rng, trDict[twn,rng]))
    # arcpy.AddMessage(inMem_dissolveName)
    
    trDict[twn,rng].append(inMem_dissolveName)
    
    arcpy.AddField_management(inMem_dissolveName, u'TWP', u'DOUBLE')
    arcpy.AddField_management(inMem_dissolveName, u'RNG', u'DOUBLE')
    arcpy.AddField_management(inMem_dissolveName, u'SEC', u'LONG')
    
    updateList = [u'OID@', u'TWP', u'RNG', u'SEC']
    
    with arcpy.da.UpdateCursor(inMem_dissolveName , updateList) as cursor:
        for row in cursor:
            row[1] = twnStrip
            row[2] = rngStrip
            row[3] = secStrip
            
            cursor.updateRow(row)
    
    arcpy.Delete_management(u'lyr_trsSelect')
    arcpy.Delete_management(u'lyr_intersectSelect')
    del cursor
    
# arcpy.AddMessage(u'Merge dict: {}'.format(trDict))

arcpy.AddMessage(u'')

outputSet = set()

for tr in orderedTR:
    twn = tr[0]
    rng = tr[1]
    
    arcpy.AddMessage(u'Merging T {} R {}'.format(twn, rng))
    
    mergeList = trDict[twn, rng][1:]
    
    mergeNum = 0
    
    if keNumber and keNumber != u'#':
        mergeTag = ur'T_{}_R_{}_KE_{}'.format(twn, rng, keNumber.replace(u'-', u'_'))
    else:
        mergeTag = ur'T_{}_R_{}'.format(twn, rng)
    
    mergeName = mergeTag.replace(u' ', u'_').replace(u'.', u'_')
        
    while arcpy.Exists(ur'{}'.format(mergeName)):
        mergeNum += 1
        mergeName = ur'{}_{}'.format(mergeTag, unicode(mergeNum))
     
    inMem_mergeName = ur'in_memory\inMem_{}'.format(mergeName)
    
    arcpy.Merge_management(mergeList, inMem_mergeName)
    
    ReorderFields(inMem_mergeName, mergeName, field_order = [u'LANDNUM', u'QUAD', u'TWP', u'RNG', u'SEC', u'COUNTY', u'COUNTYNM', u'FUND', u'PARCEL', u'EDIT_DATE', u'TSSW_ACRES', u'KE_NUMBER', u'COMMENT'], add_missing = True)
    
    if keNumber and keNumber != u'#':
        arcpy.CalculateField_management(mergeName, u'KE_NUMBER', u'\"{}\"'.format(keNumber))

    # Calculates acreage in ACRES field
    arcpy.CalculateField_management(mergeName, u'TSSW_ACRES', u'!shape.area@acres!', u'PYTHON_9.3')

    # arcpy.AddMessage(u'\nMerge fields: {}'.format([i.name for i in arcpy.ListFields(mergeName)]))

    outputSet.add(mergeName)
    
    mergeLyr = arcpy.mapping.Layer(mergeName)
    arcpy.mapping.AddLayer(df, mergeLyr, u'TOP')

arcpy.AddMessage(u'\nAdded KE number {} to field KE_NUMBER.'.format(keNumber))
arcpy.AddMessage(u'\nCalculated acreage of each dissolved buffer feature in field TSSW_ACRES.')

arcpy.AddMessage(u'\nWorkspace: {}'.format(env.workspace))

orderedOutput = natsorted([i for i in outputSet])

arcpy.AddMessage(u'\nGenerated Feature Classes:')

for output in orderedOutput:
    arcpy.AddMessage(output)
    
arcpy.Delete_management(ur'in_memory')
    
for i in lyrList:
    if arcpy.Exists(i):
        arcpy.Delete_management(i)

arcpy.AddMessage(u'\nScript complete.')
