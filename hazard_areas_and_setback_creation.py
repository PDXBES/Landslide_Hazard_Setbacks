import config
import utility
import arcpy
import os
import sys

arcpy.env.overwriteOutput = True

log_obj = utility.Logger(config.log_file)

### when running all methods (make_hazard_area and create_setback) the results will be:
### - 'grid_for_slope_##pcnt_nowater_copy' = used for QC of slope % grid assignment - may not retain
### - 'landslide_slope_raster' = result of make_hazard_area method, used as input to create_setback method
### - 'landslide_slope_poly' = polygon version of landslide_slope_raster - displays faster then raster (display result #1)
### - 'hazard_setback_###ft' = result of create_setback method (display result #2)


def make_hazard_area(slope):  # slope = eg 20, 25 etc

    slope_input = config.slope_source_dict[slope][0]
    output_gdb = config.slope_source_dict[slope][1]

    log_obj.info("Hazard Area Creation - Process Started - using {}% slope".format(slope))
    log_obj.info("Hazard Area Creation - Process Started - using {}".format(slope_input))
    log_obj.info("Hazard Area Creation - Intersecting".format())
    sect = arcpy.Intersect_analysis([slope_input,
                                     config.grid_100ft_BPS_copy],
                                    r"in_memory\sect")
    log_obj.info("Hazard Area Creation - Dissolving".format())
    diss = arcpy.Dissolve_management(sect, r"in_memory\diss", "PageNumber", '', 'MULTI_PART')
    log_obj.info("Hazard Area Creation - Adding fields".format())
    arcpy.AddGeometryAttributes_management(diss, "AREA", "", "SQUARE_FEET_US", 2913) # adds POLY_AREA field
    arcpy.AddField_management(diss, "pcnt_area", "DOUBLE")
    arcpy.AddField_management(config.grid_100ft_BPS_copy, "pcnt_area", "DOUBLE")
    log_obj.info("Hazard Area Creation - Calcing pcnt_area".format())
    utility.calculate_pcnt_area_field(diss) # calc pcnt_area on the dissolved features, then transfer value to grid
    utility.get_and_assign_field_value_from_dict(diss,
                                                 'PageNumber',
                                                 'pcnt_area',
                                                 config.grid_100ft_BPS_copy,
                                                 'PageNumber',
                                                 'pcnt_area')

    # output for QC - not required for process
    # diss_name = "diss_for_" + os.path.basename(str(slope_input))
    # diss_fullname = os.path.join(output_gdb, diss_name)
    # arcpy.CopyFeatures_management(diss, diss_fullname)
    #
    # grid_name = "grid_for_" + os.path.basename(str(slope_input))
    # grid_fullname = os.path.join(output_gdb, grid_name)
    # arcpy.CopyFeatures_management(config.grid_100ft_BPS_copy, grid_fullname)

    log_obj.info("Hazard Area Creation - Subsettings slope grids".format())
    grid_fl = arcpy.MakeFeatureLayer_management(config.grid_100ft_BPS_copy,
                                                r"in_memory\grid_fl",
                                                "pcnt_area > {}".format(config.grid_generalization_pcnt))

    log_obj.info("Hazard Area Creation - Merging slope grids and landslide".format())
    merge = arcpy.Merge_management([grid_fl, config.landslide_hazard_copy], r"in_memory\merge")
    log_obj.info("Hazard Area Creation - Dissolving and saving poly result".format())
    diss_hazards = arcpy.Dissolve_management(merge,
                                             os.path.join(output_gdb, "landslide_slope_poly"),
                                             '',
                                             '',
                                             "MULTI_PART")
    log_obj.info("Hazard Area Creation - Converting to Raster".format())
    arcpy.FeatureToRaster_conversion(diss_hazards, 'OBJECTID',
                                     os.path.join(output_gdb, "landslide_slope_raster"), 5)
    log_obj.info("Hazard Area Creation - Cleanup".format())
    arcpy.DeleteField_management(config.grid_100ft_BPS_copy, "pcnt_area")
    log_obj.info("Hazard Area Creation - Process Complete - output to {}".format(output_gdb))


def create_setback(output_gdb, setback_distance):
    log_obj.info("Setback Area Creation - Process Started - using {} as input and {}' setback".format(output_gdb,
                                                                                             setback_distance))
    arcpy.CheckOutExtension("Spatial")

    log_obj.info("Setback Area Creation - Setting environment variables".format())
    arcpy.env.workspace = r"C:\temp_work\working.gdb"
    arcpy.env.extent = config.flow_dir_BE_2019_raster
    arcpy.env.snapRaster = config.flow_dir_BE_2019_raster
    arcpy.env.cellSize = 5

    # run watershed with hazard input + bare earth DEM: takes about 25 min
    log_obj.info("Setback Area Creation - Running Watershed".format())
    wshed_result = arcpy.sa.Watershed(config.flow_dir_BE_2019_raw, os.path.join(output_gdb, "landslide_slope_raster"))
    #wshed = wshed_result.save(r"in_memory\wshed")

    # raster calc - Remove from the watershed result where the hazard area overlaps (retain upstream area only)
    log_obj.info("Setback Area Creation - Removing hazard areas from watershed result (keep upstream areas)".format())
    landslide_slope_raster = arcpy.sa.Raster(os.path.join(output_gdb, "landslide_slope_raster"))
    wshed_raster = arcpy.sa.Raster(wshed_result)
    wshed_upstream_only = arcpy.sa.SetNull(~arcpy.sa.IsNull(landslide_slope_raster), wshed_raster)

    # flow dir raster calc - Set flow direction to Null where it does NOT fall within the watershed result (upstream portion)
    log_obj.info("Setback Area Creation - Subsetting flow direction to the upstream watershed areas".format())
    upstream_flow_dir = arcpy.sa.SetNull(arcpy.sa.IsNull(wshed_upstream_only), config.flow_dir_BE_2019_raster)

    # flow length: takes the longest - between 12 and 4 hours depending on input raster
    log_obj.info("Setback Area Creation - Running Flow Length".format())
    flow_length = arcpy.sa.FlowLength(upstream_flow_dir, "DOWNSTREAM")

    # raster calc - limit flow length to setback distance
    log_obj.info("Setback Area Creation - Applying {}' setback".format(setback_distance))
    flow_length_with_setback = arcpy.sa.SetNull(flow_length, flow_length, "VALUE>{}".format(setback_distance))

    # int
    log_obj.info("Setback Area Creation - Converting result to Int type".format())
    flow_length_with_setback_int = arcpy.sa.Int(flow_length_with_setback)

    # raster to polygon
    log_obj.info("Setback Area Creation - Converting raster to polygon result".format())
    hazard_setback_polygon = arcpy.RasterToPolygon_conversion(flow_length_with_setback_int,
                                                              r"in_memory\hazard_setback_polygon")

    # dissolve
    arcpy.Dissolve_management(hazard_setback_polygon, os.path.join(output_gdb,
                                                                   "hazard_setback_{}ft").format(setback_distance))

    log_obj.info("Setback Area Creation - Process Complete - output to {}".format(output_gdb))


try:

    # uncomment and run them all if you want a full refresh
    # per Henry (12/20/23) the result using 25% slope input with a 100' setback is the main product

    make_hazard_area(25)
    # create_setback(config.output_25pcnt_gdb, 100)

    # Ian LaVielle wants to see a run with >=50% slope and 100' setback
    # make_hazard_area(50)
    # create_setback(config.output_50pcnt_gdb, 100)


except Exception as e:
    arcpy.ExecuteError()
    log_obj.exception(str(sys.exc_info()[0]))
    log_obj.info("Hazard Area Creation Failed".format())
    pass

