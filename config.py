import os
import arcpy
import utility

utility.datetime_print("Running Config")

log_file = r"\\besfile1\ISM_PROJECTS\Work_Orders\WO_10199_H_Stevens\hazard_areas_log"

input_gdb = r"\\besfile1\ISM_PROJECTS\Work_Orders\WO_10199_H_Stevens\inputs.gdb"
output_20pcnt_gdb = r"\\besfile1\ISM_PROJECTS\Work_Orders\WO_10199_H_Stevens\flow_result_20pcnt_slope.gdb"
output_25pcnt_gdb = r"\\besfile1\ISM_PROJECTS\Work_Orders\WO_10199_H_Stevens\flow_result_25pcnt_slope.gdb"
output_50pcnt_gdb = r"\\besfile1\ISM_PROJECTS\Work_Orders\WO_10199_H_Stevens\flow_result_50pcnt_slope.gdb"

connections = r"\\besfile1\grp117\DAshney\Scripts\connections"

EGH_PUBLIC = os.path.join(connections, "egh_public on gisdb1.rose.portland.local.sde")

slope_20pcnt_raw = EGH_PUBLIC + r"\EGH_Public.ARCMAP_ADMIN.slope_20_percent_lidar_bes_pdx"
slope_25pcnt_raw = EGH_PUBLIC + r"\EGH_Public.ARCMAP_ADMIN.slope_25_percent_lidar_pdx"
slope_50pcnt_raw = r"\\besfile1\ISM_PROJECTS\Work_Orders\WO_10199_H_Stevens\inputs.gdb\slope_50_percent_lidar"

landslide_hazard_raw = os.path.join(input_gdb, "draft_regulatory_landslide_hazard_area")
grid_100ft_COP_raw = os.path.join(input_gdb, "empty_grid_COP")
grid_100ft_BPS_raw = os.path.join(input_gdb, "regLandslideHazGridIndex100x100_BPS")
grid_100ft_BPS_raster = os.path.join(input_gdb, "regLandslideHazGrid_BPS_raster")
flow_dir_BE_2019_raw = os.path.join(input_gdb, "flow_dir_BE_DEM2019") #need to recreate and repoint if we want it based on newer lidar

#lidar_BE_DEM = r"https://www.portlandmaps.com/arcgis/services/Public/COP_LiDAR_2019_1ft_BE_DEM_WS/ImageServer/Public/COP_LiDAR_2019_1ft_BE_DEM_WS"
#lidar_BE_DEM = r"\\besfile1\ASM_Projects\Lidar_Processing\gdb\2019_lidar_dem_comparison.gdb\bes_topo_dem_1ft"
lidar_BE_DEM_raw = r"\\besfile1\ISM_PROJECTS\Lidar_Processing\2019 Lidar Processing\GDB\2019_lidar_dem_usb.gdb\usb_be_dem_1ft"

slope_20pcnt_nowater_fl = arcpy.MakeFeatureLayer_management(slope_20pcnt_raw, r"in_memory\slope_20pcnt_nowater_fl", "Is_Water is Null") #ie is not Water
slope_25pcnt_nowater_fl = arcpy.MakeFeatureLayer_management(slope_25pcnt_raw, r"in_memory\slope_25pcnt_nowater_fl", "Is_Water is Null") #ie is not Water
slope_50pcnt_fl = arcpy.MakeFeatureLayer_management(slope_50pcnt_raw, r"in_memory\slope_50pcnt_nowater_fl")

slope_20pcnt_nowater_copy = arcpy.CopyFeatures_management(slope_20pcnt_nowater_fl, r"in_memory\slope_20pcnt_nowater_copy")
slope_25pcnt_nowater_copy = arcpy.CopyFeatures_management(slope_25pcnt_nowater_fl, r"in_memory\slope_25pcnt_nowater_copy")
slope_50pcnt_copy = arcpy.CopyFeatures_management(slope_50pcnt_fl, r"in_memory\slope_50pcnt_nowater_copy")

landslide_hazard_copy = arcpy.CopyFeatures_management(landslide_hazard_raw, r"in_memory\landslide_hazard_copy")
grid_100ft_COP_copy = arcpy.CopyFeatures_management(grid_100ft_COP_raw, r"in_memory\grid_100ft_COP_copy")
grid_100ft_BPS_copy = arcpy.CopyFeatures_management(grid_100ft_BPS_raw, r"in_memory\grid_100ft_BPS_copy")

lidar_BE_DEM_raster = arcpy.sa.Raster(lidar_BE_DEM_raw)
flow_dir_BE_2019_raster = arcpy.sa.Raster(flow_dir_BE_2019_raw)

grid_generalization_pcnt = 20  # used to remove small, steep things like walls

slope_source_dict = {
    20: [slope_20pcnt_nowater_copy, output_20pcnt_gdb],
    25: [slope_25pcnt_nowater_copy, output_25pcnt_gdb],
    50: [slope_50pcnt_copy, output_50pcnt_gdb]
}
