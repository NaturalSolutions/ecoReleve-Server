USE [ecoReleve_Data]
GO
/****** Object:  StoredProcedure [dbo].[sp_validate_rfid]    Script Date: 06/09/2014 15:27:48 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		Thomas PEEL
-- Create date: 2014-09-04
-- Description:	
-- =============================================
ALTER PROCEDURE [dbo].[sp_validate_rfid]
	@user int,
	@nb int OUTPUT,
	@error int OUTPUT
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	DECLARE @data_to_insert table ( PK_id int
		, FK_ind int
		, FK_obj int
		, chip_code varchar(10)
		, date_ datetime
		, lat decimal(9,5)
		, lon decimal(9,5));

	-- Gather not validated data.
	WITH data AS (
		SELECT PK_id
			, FK_obj
			, chip_code
			, date_
			, validated
			, ROW_NUMBER() OVER (PARTITION BY FK_obj, chip_code, CONVERT(DATE, date_), DATEPART(hour, date_) ORDER BY date_) as r
		FROM [ecoReleve_Data].[dbo].[T_DataRfid]
	)

	INSERT INTO @data_to_insert
    SELECT data.PK_id
		, indiv.Individual_Obj_PK
		, data.FK_obj
		, data.chip_code
		, date_
		, lat
		, lon
    FROM data
	JOIN TViewIndividual indiv 
		ON data.chip_code = indiv.id13@TCarac_Chip_Code
	JOIN T_MonitoredSiteEquipment e 
		ON e.FK_obj = data.FK_obj 
		AND data.date_ >= e.begin_date
		AND (data.date_ <= e.end_date OR e.end_date IS NULL)
	WHERE data.r = 1 AND data.validated = 0;

	-- Insert only the first chip lecture per RFID, per individual, per hour.
	INSERT INTO T_AnimalLocation (FK_creator, FK_obj, FK_ind, type_, date_, lat, lon, creation_date)
	SELECT @user, FK_obj, FK_ind, 'rfid', date_, lat, lon, CURRENT_TIMESTAMP
	FROM @data_to_insert

	-- Update inserted data.
	UPDATE T_DataRfid SET validated = 1 
	WHERE T_DataRfid.PK_id IN (SELECT PK_id FROM @data_to_insert);

	SELECT @error = @@ERROR
	SELECT @nb = COUNT(*) FROM @data_to_insert

	RETURN
END
