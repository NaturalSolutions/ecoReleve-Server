-- =============================================
-- Author:		Romain FABBRO
-- Create date: 2014-11-28
-- Description:	add column max/min LAT/LON retrieve from gemotry polygon on utm_grid and geo_CNTRIES Tables
-- 				and create spatial index
-- WARNING: Make sure of the presence of primary key on these tables
-- =============================================
	
alter table dbo.geo_utm_grid_20x20_km add minLon decimal(9,5) null

alter table dbo.geo_utm_grid_20x20_km add minLat decimal(9,5) null

alter table dbo.geo_utm_grid_20x20_km add maxLon decimal(9,5) null

alter table dbo.geo_utm_grid_20x20_km add maxLat decimal(9,5) null

GO

UPDATE dbo.geo_utm_grid_20x20_km SET

       minLon = ogr_geometry.STEnvelope().STPointN(1).STX,

       minLat = ogr_geometry.STEnvelope().STPointN(1).STY,

       maxLon = ogr_geometry.STEnvelope().STPointN(3).STX,

       maxLat = ogr_geometry.STEnvelope().STPointN(3).STY

GO

alter table dbo.geo_CNTRIES_and_RENECO_MGMTAreas add minLon decimal(9,5) null

alter table dbo.geo_CNTRIES_and_RENECO_MGMTAreas add minLat decimal(9,5) null

alter table dbo.geo_CNTRIES_and_RENECO_MGMTAreas add maxLon decimal(9,5) null

alter table dbo.geo_CNTRIES_and_RENECO_MGMTAreas add maxLat decimal(9,5) null

GO

UPDATE dbo.geo_CNTRIES_and_RENECO_MGMTAreas SET

       minLon = valid_geom.STEnvelope().STPointN(1).STX,

       minLat = valid_geom.STEnvelope().STPointN(1).STY,

       maxLon = valid_geom.STEnvelope().STPointN(3).STX,

       maxLat = valid_geom.STEnvelope().STPointN(3).STY
 
GO

CREATE SPATIAL INDEX IX_geo_CNTRIES_and_RENECO_MGMTAreas_SPATIAL
ON geo_CNTRIES_and_RENECO_MGMTAreas (valid_geom) USING GEOMETRY_GRID  WITH ( BOUNDING_BOX = ( -180, -90, 180, 90 ),GRIDS =(LEVEL_1 = LOW,LEVEL_2 = LOW,LEVEL_3 = LOW,LEVEL_4 = LOW)  );

CREATE SPATIAL INDEX IX_geo_utm_grid_20x20_km
ON geo_utm_grid_20x20_km (ogr_geometry) USING GEOMETRY_GRID  WITH ( BOUNDING_BOX = ( -180, -90, 180, 90 ),GRIDS =(LEVEL_1 = LOW,LEVEL_2 = LOW,LEVEL_3 = LOW,LEVEL_4 = LOW)  );

