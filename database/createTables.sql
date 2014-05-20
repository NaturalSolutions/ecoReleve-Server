USE [ecoReleve_Sensor]
GO
/****** Object:  Table [dbo].[Tlog]    Script Date: 05/20/2014 13:58:16 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[Tlog](
	[PK_id] [int] IDENTITY(1,1) NOT NULL,
	[FK_objId] [int] NOT NULL,
	[logDate] [datetime2](0) NOT NULL,
	[logLevel] [tinyint] NOT NULL,
	[logProtocol] [varchar](50) NOT NULL,
	[logType] [varchar](50) NOT NULL,
	[logValue] [varchar](max) NOT NULL,
	[fileName] [varchar](max) NULL,
	[lineNumber] [int] NULL,
 CONSTRAINT [PK_Tlog] PRIMARY KEY CLUSTERED 
(
	[PK_id] ASC
)WITH (PAD_INDEX  = OFF, STATISTICS_NORECOMPUTE  = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS  = ON, ALLOW_PAGE_LOCKS  = ON) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
SET ANSI_PADDING OFF
GO
/****** Object:  Table [dbo].[Tgsm]    Script Date: 05/20/2014 13:58:16 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Tgsm](
	[PK_id] [int] IDENTITY(1,1) NOT NULL,
	[FK_ptt] [int] NOT NULL,
	[date] [datetime2](0) NOT NULL,
	[lat] [decimal](9, 5) NOT NULL,
	[lon] [decimal](9, 5) NOT NULL,
	[ele] [smallint] NULL,
	[speed] [smallint] NULL,
	[course] [smallint] NULL,
	[hdop] [decimal](9, 1) NULL,
	[vdop] [decimal](9, 1) NULL,
	[Imported] [bit] NOT NULL,
 CONSTRAINT [PK_TGSM] PRIMARY KEY CLUSTERED 
(
	[PK_id] ASC
)WITH (PAD_INDEX  = OFF, STATISTICS_NORECOMPUTE  = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS  = ON, ALLOW_PAGE_LOCKS  = ON) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Tgps_engineering]    Script Date: 05/20/2014 13:58:16 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[Tgps_engineering](
	[PK_id] [int] IDENTITY(1,1) NOT NULL,
	[FK_ptt] [int] NOT NULL,
	[txDate] [datetime2](0) NOT NULL,
	[pttDate] [datetime2](0) NOT NULL,
	[satId] [varchar](50) NULL,
	[activity] [smallint] NULL,
	[txCount] [smallint] NULL,
	[temp] [decimal](9, 1) NULL,
	[batt] [decimal](9, 2) NULL,
	[fixTime] [int] NULL,
	[satCount] [int] NULL,
	[resetHours] [tinyint] NULL,
	[fixDays] [tinyint] NULL,
	[season] [tinyint] NULL,
	[shunt] [bit] NULL,
	[mortalityGT] [bit] NULL,
	[seasonalGT] [bit] NULL,
	[latestLat] [decimal](9, 5) NULL,
	[latestLon] [decimal](9, 5) NULL,
 CONSTRAINT [PK_TEMP_ArgosDataEnginering] PRIMARY KEY CLUSTERED 
(
	[PK_id] ASC
)WITH (PAD_INDEX  = OFF, STATISTICS_NORECOMPUTE  = ON, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS  = ON, ALLOW_PAGE_LOCKS  = ON, FILLFACTOR = 80) ON [PRIMARY]
) ON [PRIMARY]
GO
SET ANSI_PADDING OFF
GO
/****** Object:  Table [dbo].[Tgps]    Script Date: 05/20/2014 13:58:16 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Tgps](
	[PK_id] [int] IDENTITY(1,1) NOT NULL,
	[FK_ptt] [int] NOT NULL,
	[date] [datetime2](0) NOT NULL,
	[lat] [decimal](9, 5) NOT NULL,
	[lon] [decimal](9, 5) NOT NULL,
	[ele] [smallint] NULL,
	[speed] [smallint] NULL,
	[course] [smallint] NULL,
	[checked] [bit] NOT NULL,
	[imported] [bit] NOT NULL,
 CONSTRAINT [PK_Tgps] PRIMARY KEY CLUSTERED 
(
	[PK_id] ASC
)WITH (PAD_INDEX  = OFF, STATISTICS_NORECOMPUTE  = ON, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS  = ON, ALLOW_PAGE_LOCKS  = ON, FILLFACTOR = 80) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Targos]    Script Date: 05/20/2014 13:58:16 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[Targos](
	[PK_id] [int] IDENTITY(1,1) NOT NULL,
	[FK_ptt] [int] NOT NULL,
	[date] [datetime2](0) NOT NULL,
	[lat] [decimal](9, 5) NOT NULL,
	[lon] [decimal](9, 5) NOT NULL,
	[lc] [varchar](1) NULL,
	[iq] [tinyint] NULL,
	[ele] [smallint] NULL,
	[nbMsg] [tinyint] NULL,
	[nbMsg>-120dB] [tinyint] NULL,
	[bestLevel] [smallint] NULL,
	[passDuration] [smallint] NULL,
	[nopc] [tinyint] NULL,
	[freq] [float] NULL,
	[errorRadius] [int] NULL,
	[semiMajor] [int] NULL,
	[semiMinor] [int] NULL,
	[orientation] [tinyint] NULL,
	[hdop] [int] NULL,
	[checked] [bit] NOT NULL,
	[imported] [bit] NOT NULL,
 CONSTRAINT [PK_Targos] PRIMARY KEY CLUSTERED 
(
	[PK_id] ASC
)WITH (PAD_INDEX  = OFF, STATISTICS_NORECOMPUTE  = ON, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS  = ON, ALLOW_PAGE_LOCKS  = ON, FILLFACTOR = 80) ON [PRIMARY]
) ON [PRIMARY]
GO
SET ANSI_PADDING OFF
GO
/****** Object:  Default [DF_Targos_checked]    Script Date: 05/20/2014 13:58:16 ******/
ALTER TABLE [dbo].[Targos] ADD  CONSTRAINT [DF_Targos_checked]  DEFAULT ((0)) FOR [checked]
GO
/****** Object:  Default [DF_Targos_imported]    Script Date: 05/20/2014 13:58:16 ******/
ALTER TABLE [dbo].[Targos] ADD  CONSTRAINT [DF_Targos_imported]  DEFAULT ((0)) FOR [imported]
GO
/****** Object:  Default [DF_Tgps_checked]    Script Date: 05/20/2014 13:58:16 ******/
ALTER TABLE [dbo].[Tgps] ADD  CONSTRAINT [DF_Tgps_checked]  DEFAULT ((0)) FOR [checked]
GO
/****** Object:  Default [DF__Tgps__imported__108B795B]    Script Date: 05/20/2014 13:58:16 ******/
ALTER TABLE [dbo].[Tgps] ADD  CONSTRAINT [DF__Tgps__imported__108B795B]  DEFAULT ((0)) FOR [imported]
GO
/****** Object:  Default [DF_Tgsm_Imported]    Script Date: 05/20/2014 13:58:16 ******/
ALTER TABLE [dbo].[Tgsm] ADD  CONSTRAINT [DF_Tgsm_Imported]  DEFAULT ((0)) FOR [Imported]
GO
