"""
Created on Fri Sep 19 17:24:09 2014
@author: Natural Solutions (Thomas)
"""
from pyramid.response import Response
import pyramid.httpexceptions as exc
from pyramid.view import view_config
from sqlalchemy import select, distinct, join, text,Table, and_,or_,cast, String, bindparam, update, func, Date, DateTime
from ecorelevesensor.models import * 
import sys, datetime, transaction, time
from sqlalchemy.sql import func
import json,datetime,math,time,operator
from sqlalchemy.types import *
import pandas
from collections import OrderedDict
from ecorelevesensor.utils.eval import Eval

prefix = 'station'
eval_ = Eval()
def get_operator_fn(op):
	return {
		'<' : operator.lt,
		'>' : operator.gt,
		'=' : operator.eq,
		'<>': operator.ne,
		'<=': operator.le,
		'>=': operator.ge,
		'Like': operator.eq,
		'Not Like': operator.ne,
		}[op]
def eval_binary_expr(op1, operator, op2):
	op1,op2 = op1, op2
	print (op1.type)
	if 'date' in str(op1.type).lower() :
		op1=cast(op1,Date)
		print(op1)
		print(get_operator_fn(operator)(op1, op2))
	return get_operator_fn(operator)(op1, op2)

class Geometry(UserDefinedType):
	def get_col_spec(self):
		return "GEOMETRY"

def getFieldActitityID (FieldActivity_Name) :

	id_field_query=select([ThemeEtude.id], ThemeEtude.Caption == FieldActivity_Name)
	id_field=DBSession.execute(id_field_query).scalar()
	return id_field

def getRegion(lat,lon) :
	stmt_Region = text("""
		DECLARE @geoPlace varchar(255);
		EXEC dbo.sp_GetRegionFromLatLon :lat, :lon, @geoPlace OUTPUT;
		SELECT @geoPlace;"""
	).bindparams(bindparam('lat', value=lat , type_=Numeric(9,5)),bindparam('lon', value=lon , type_=Numeric(9,5)))
	geoRegion=DBSession.execute(stmt_Region).scalar()
	return geoRegion

def getUTM(lat,lon) :
	stmt_UTM=text("""
		DECLARE @geoPlace varchar(255);
		EXEC dbo.sp_GetUTMCodeFromLatLon   :lat, :lon, @geoPlace OUTPUT;
		SELECT @geoPlace;"""
	).bindparams(bindparam('lat', value=lat, type_=Numeric(9,5)),bindparam('lon', value=lon , type_=Numeric(9,5)))
	geoUTM=DBSession.execute(stmt_UTM).scalar()
	return geoUTM

def getWorkerID(workerList) :
	users_ID_query = select([User.id], User.fullname.in_((workerList)))
	users_ID = DBSession.execute(users_ID_query).fetchall()
	users_ID=[row[0] for row in users_ID]
	if len(users_ID) <3 :
		users_ID.extend([None,None])
	return users_ID

@view_config(route_name=prefix, renderer='json', request_method='GET')
def monitoredSites(request):
   
	data = DBSession.query(Station).all()
	return data

@view_config(route_name=prefix+'/id', renderer='json', request_method='GET')
def station_by_id(request):
   
	id_ = request.matchdict['id']
	data = DBSession.execute(select([Station]).where(Station.id == id_)).fetchone()
	print(data)
	if data != None : 
		res = {key:val for key, val in data.items() }
		res['PK'] = res['TSta_PK_ID'] 
		del res['TSta_PK_ID']
	else : 
		res=data
	return res

@view_config(route_name=prefix+'/id/next', renderer='json', request_method='GET')
def next_station(request):
   
	id_ = int(request.matchdict['id'])
	data = None
	last_id = DBSession.execute(select([Station.id]).order_by(Station.id.desc())).first()
	last_id = last_id[0]
	print (last_id)
	while data == None :
		id_+=1
		print(id_)
		if id_ > last_id :
			id_ = 1
		data = DBSession.execute(select([Station]).where(Station.id == id_)).fetchone()
	
	res = {key:val for key, val in data.items()}
	res['PK'] = res['TSta_PK_ID']

	del res['TSta_PK_ID']

	workerList = [res['FieldWorker1'],res['FieldWorker2'],res['FieldWorker3']]
	users_ID_query = select([User.fullname], User.id.in_((workerList)))
	users_ID = DBSession.execute(users_ID_query).fetchall()
	users_ID=[row[0] for row in users_ID]
	
	for i in range(len(users_ID)) :
		res['FieldWorker'+str(i+1)] = users_ID[i]
	
	if len(users_ID) <= 1 :
		users_ID.extend([None,None])
	
	return res

@view_config(route_name=prefix+'/id/prev', renderer='json', request_method='GET')
def prev_station(request):
   
	id_ = int(request.matchdict['id'])
	data = None
	last_id = DBSession.execute(select([Station.id]).order_by(Station.id.desc())).first()
	last_id = last_id[0]
	
	while data == None :
		id_-=1
		print(id_)
		if id_ < 1 :
			id_ = last_id
		data = DBSession.execute(select([Station]).where(Station.id == id_)).fetchone()
	
	res = {key:val for key, val in data.items() }
	res['PK'] = res['TSta_PK_ID'] 
	del res['TSta_PK_ID']
	return res
	
@view_config(route_name=prefix+'/area', renderer='json', request_method='POST')
def monitoredSitesArea(request):

	req = request.POST

	if 'name_view' in req :
		print('name_view')
		try :
			proto_view_Table = Base.metadata.tables[proto_view_Name]
			join_table = join(proto_view_Table, Station, proto_view_Table.c['TSta_PK_ID'] == Station.id )
		except :
			proto_view_Table = dict_proto[proto_view_Name]()
			join_table = join(proto_view_Table, Station, proto_view_Table.FK_TSta_ID == Station.id )

		print (proto_view_Table)

	
		slct = select([Station.area]).distinct().select_from(join_table)
		data = DBSession.execute(slct).fetchall()
		return [row['Region' or 'Area'] for row in data]


	else :
		table = Base.metadata.tables['geo_CNTRIES_and_RENECO_MGMTAreas']
		slct = select([table.c['Place']]).distinct()
		data =  DBSession.execute(slct).fetchall()
		return [row[0] for row in data]

@view_config(route_name=prefix+'/area_coord', renderer='json', request_method='GET')
def listArea_with_coord(request):

	table = Base.metadata.tables['geo_CNTRIES_and_RENECO_MGMTAreas']
	slct = select([table.c['Place'],table.c['minLat'],table.c['maxLat'],table.c['minLon'],table.c['maxLon']]).distinct()
	data =  DBSession.execute(slct).fetchall()
	areaList={}
	# calcul of the Region/Area center 
	data = [ OrderedDict(row) for row in data]
	for row in data :
		lat_c = row['maxLat'] - (row['maxLat']-row['minLat'])/2
		lon_c = row['maxLon'] - (row['maxLon']-row['minLon'])/2
		areaList[row['Place']] = {'lat': lat_c, 'lon' : lon_c}

	return OrderedDict(areaList)


@view_config(route_name=prefix+'/locality', renderer='json', request_method='POST')
def monitoredSitesLocality(request):

	req = request.POST

	if 'name_view' in req :
		print('name_view')
		try :
			proto_view_Table=Base.metadata.tables[proto_view_Name]
			join_table=join(proto_view_Table, Station, proto_view_Table.c['TSta_PK_ID'] == Station.id )

		except :
			
			proto_view_Table=dict_proto[proto_view_Name]()
			join_table=join(proto_view_Table, Station, proto_view_Table.FK_TSta_ID == Station.id )

		slct=select([Station.locality]).distinct().select_from(join_table)
		data = DBSession.execute(slct).fetchall()
		return [row['Place' or 'Locality'] for row in data]
	else :
		table = Base.metadata.tables['Tthesaurus']
		query = select([table.c['topic_en']]).where(and_(table.c['Id_Type'] == 1000254 ,table.c['Id_Parent'] != 1 )).order_by(table.c['topic_en'])
		data=DBSession.execute(query).fetchall()
		return [row[0] for row in data]


@view_config(route_name=prefix+'/addStation', renderer='json', request_method='POST')
def insertNewStation(request):

	data=dict(request.params)
	print(data)
	check_duplicate_station = select([func.count(Station.id)]).where(and_(Station.date == bindparam('date'),
		Station.lat == bindparam('lat'),Station.lon == bindparam('lon')))
	date=data.get('Date_')
	print (data)
	print(date)

	if 'PK' not in data or data['PK']=='' :
		try: 
			if (data['LON'],data['LAT'])!=('','') :
				print('______________________')
				if DBSession.execute(check_duplicate_station, {'date':date, 'lat':data['LAT'], 'lon':data['LON']}).scalar() == 0 :

					# get REGION and UTM by stored procedure
					print ('_______Region___________')
					stmt_Region = text("""
						DECLARE @geoPlace varchar(255);
						EXEC dbo.sp_GetRegionFromLatLon :lat, :lon, @geoPlace OUTPUT;
						SELECT @geoPlace;"""
					).bindparams(bindparam('lat', value=data['LAT'] , type_=Numeric(9,5)),bindparam('lon', value=data['LON'] , type_=Numeric(9,5)))
					geoRegion=DBSession.execute(stmt_Region).scalar()
					print (geoRegion)

					print ('_______UTM___________')
					stmt_UTM=text("""
						DECLARE @geoPlace varchar(255);
						EXEC dbo.sp_GetUTMCodeFromLatLon   :lat, :lon, @geoPlace OUTPUT;
						SELECT @geoPlace;"""
					).bindparams(bindparam('lat', value=data['LAT'] , type_=Numeric(9,5)),bindparam('lon', value=data['LON'] , type_=Numeric(9,5)))
					geoUTM=DBSession.execute(stmt_UTM).scalar()
					locality=None
					print (geoUTM)

				else :
					response=Response('a station exists at same date and coordinates')
					response.status_int = 500
					return response

			else :
				geoUTM=None
				geoRegion=data['Region']
				data['LAT'] = None
				data['LON'] = None

			#get userID with fieldWorker_Name
			# users_ID_query = select([User.id], User.fullname.in_((data['FieldWorker1'],data['FieldWorker2'],data['FieldWorker3'])))
			# users_ID = DBSession.execute(users_ID_query).fetchall()
			# users_ID=[row[0] for row in users_ID]
			
			# if len(users_ID) <3 :
			# 	users_ID.extend([None,None])

			if data['id_site']=='':
				data['id_site']=None
			else :
				
				# join_table= select([MonitoredSitePosition, MonitoredSite]).join(MonitoredSite, MonitoredSitePosition.site == MonitoredSite.id)
				# q= select([MonitoredSitePosition.id,MonitoredSitePosition.lat
				# 	, MonitoredSitePosition.lon, MonitoredSitePosition.ele
				# 	, MonitoredSitePosition.precision]).select_from(join_table).filter(and_(MonitoredSitePosition.begin_date< data['Date_']
				# 		, or_(MonitoredSitePosition.end_date>data['Date_'], MonitoredSitePosition.end_date == None)))
				

				dt = DBSession.query(MonitoredSitePosition.id,MonitoredSitePosition.lat
					, MonitoredSitePosition.lon, MonitoredSitePosition.ele
					, MonitoredSitePosition.precision
					).join(MonitoredSite, MonitoredSitePosition.site == MonitoredSite.id
					).filter(MonitoredSite.id == data['id_site']
					).filter(and_(MonitoredSitePosition.begin_date< data['Date_']
						, or_(MonitoredSitePosition.end_date>data['Date_'], MonitoredSitePosition.end_date == None))).one()
					
				data['id_site']=data['id_site']
				data['LAT']=dt[1]
				data['LON']=dt[2]

			for i in range(1,3):
				if data['FieldWorker'+str(i)] != '' :
					data['FieldWorker'+str(i)] = int(data['FieldWorker'+str(i)])
				else :
					data['FieldWorker'+str(i)] = None

			id_field_query=select([ThemeEtude.id], ThemeEtude.Caption == data['FieldActivity_Name'])
			id_field=DBSession.execute(id_field_query).scalar()

			# set station and insert it
			station=Station(name=data['Name'],lat=data['LAT'], lon= data['LON'], 
				date=data['Date_'], fieldActivityName = data['FieldActivity_Name'],
				creator=request.authenticated_userid, area=geoRegion, utm=geoUTM, fieldActivityId=id_field,
				fieldWorker1=data['FieldWorker1'],fieldWorker2=data['FieldWorker2'],fieldWorker3=data['FieldWorker3']
				,id_siteMonitored=data['id_site'], nbFielWorker= data['NbFieldWorker'], precision= data['Precision'])

			DBSession.add(station)
			DBSession.flush()
			id_sta=station.id
		
			print(id_sta)
			return {'PK':id_sta,'Region':geoRegion,'UTM20':geoUTM}

		except Exception as err: 
			
			msg = err.args[0] if err.args else ""
			response=Response('Problem occurs on station insert : '+str(type(err))+' = '+msg)
			response.status_int = 500
			return response	

	elif 'PK' in data :
		
		try: 
			print('_______________________')
			print(type(data['PK']))
			up_station=DBSession.query(Station).get(data['PK'])
			
			if 'Date_' in data : 
				data['date']=data['Date_']
			
			toDel = ['Date_','PK','FieldWorker4','FieldWorker5']

			for field in toDel : 
				if field in data :
					del data[field]

			if 'LAT' in data and data['LAT']=='NULL':
				data['LAT']=None
				data['LON']=None

			colToAttr=dict({v.name:k for k,v in up_station.__mapper__.c.items()})

			for k, v in data.items() :
				# if 'FieldWorker' in k :
				# 	v=getWorkerID([v])[0]
				setattr(up_station,colToAttr[k],v)
				print(k+' : ')
			if 'FieldActivity_Name' in data : 
				up_station.fieldActivityId=getFieldActitityID(data['FieldActivity_Name'])
				
			transaction.commit()
			return data

		except Exception as err: 

			msg = err.args[0] if err.args else ""
			response=Response('Problem occurs on station update : '+str(type(err))+' = '+msg)
			response.status_int = 500
			return response
	

@view_config(route_name=prefix+'/addMultStation', renderer='json', request_method='POST')
def insertMultStation(request):

	data=list(request.params)

	data=json.loads(data[0])
	print(type(data))
	start=time.time()
	creation_date=datetime.datetime.now()
	userID=[data[0]['fieldWorker1'],data[0]['fieldWorker2'],data[0]['fieldWorker3']]
	col=tuple(['name','date','LAT','LON','FieldWorker1','FieldWorker2','FieldWorker3','FieldActivity_Name','Creator','Creation_date'])

	print(userID)
	# ----------------------------------------------
	#### TODO ==> Add elevation field ####
	final=[dict(zip(col,[
		row['name']
		,datetime.datetime.strptime(row['waypointTime'].replace('-','/'),'%Y/%m/%d %H:%M:%S')
		,row['latitude']
		,row['longitude']
		,userID[0]
		,userID[1]
		,userID[2]
		,row['fieldActivity']
		,request.authenticated_userid
		,creation_date
		])) for row in data ]

	
	
	# ----------------------------------------------
	# Create temporary Table and insert all waypoints
	tempName='tempTable'+str(request.authenticated_userid)
	tempTable=Table (tempName,
		Base.metadata,
		Column('PK', Integer, primary_key=True),
		Column('TSta_PK_ID', Integer, nullable=True),
		Column('date',DateTime),
		Column('name', String),
		Column('region', String),
		Column('place', String),
		Column('UTM20',String),
		Column('FieldActivity_ID', Integer),
		Column('FieldActivity_Name', String),
		Column('FieldWorker1', Integer),
		Column('FieldWorker2', Integer),
		Column('FieldWorker3', Integer),
		Column('LAT',Numeric(9,5)),
		Column('LON',Numeric(9,5)),
		Column('ele',Integer),
		Column('Precision', Integer),
		Column('Creator', Integer),
		Column('Creation_date', DateTime),
		Column('GeoPoint',Geometry)
		)
	if tempTable.exists() :
		print('table exists')
		tempTable.drop()

	tempTable.create(checkfirst=True)
	DBSession.execute(tempTable.insert(),final)

	# -------------------------- #
	# Launch procedure : check duplicate, 
	# retrieve UTM, Region from coord, fieldActivity_ID from fieldActivity_Name,
	# and insert in Table(Station)
	# -------------------------- #

	df=pandas.DataFrame(data=final)
	query='''DELETE {tableName}
	WHERE EXISTS (SELECT* FROM TStations t WHERE t.LAT={tableName}.LAT 
	AND t.LON={tableName}.LON AND t.DATE={tableName}.date AND t.name={tableName}.name);

	UPDATE {tableName} SET GeoPoint=geometry::STPointFromText('Point('+convert(varchar,LON)
		+' '+convert(varchar,LAT)+'
		)',4326);


	CREATE SPATIAL INDEX IX_tempTable_GeoPoint ON {tableName}(GeoPoint) 
	USING GEOMETRY_GRID WITH ( BOUNDING_BOX = ({minLON},{minLAT},{maxLON},{maxLAT}) ,
	GRIDS =(LEVEL_1 = LOW, LEVEL_2 = LOW, LEVEL_3 = LOW, LEVEL_4 = LOW));
	

	UPDATE {tableName} SET {tableName}.region=geo.Place, {tableName}.UTM20=u.code, {tableName}.FieldActivity_ID=th.TProt_PK_ID
	
	FROM {tableName} tmp LEFT join geo_CNTRIES_and_RENECO_MGMTAreas geo 
	ON tmp.lon >= geo.minLon AND tmp.lon <= geo.maxLon AND tmp.lat >= geo.minLat AND tmp.lat <= geo.maxLat
	
	LEFT JOIN geo_utm_grid_20x20_km u 
	ON tmp.lon >= u.minLon AND tmp.lon <= u.maxLon AND tmp.lat >= u.minLat AND tmp.lat <= u.maxLat
	
	LEFT JOIN TThemeEtude th 
	ON tmp.FieldActivity_Name=th.Caption
	
	WHERE geometry::STPointFromText('Point(' + CONVERT(varchar, tmp.lon) + ' ' 
	+ CONVERT(varchar, tmp.lat) +')', 4326).STWithin(geo.valid_geom)=1  AND 
	geometry::STPointFromText('Point(' + CONVERT(varchar, tmp.lon) + ' ' 
	+ CONVERT(varchar, tmp.lat) +')', 4326).STWithin(u.ogr_geometry)=1 ;
	

	INSERT INTO TStations (date,LAT,LON,name,FieldActivity_Name,FieldActivity_ID,
		FieldWorker1,FieldWorker2,FieldWorker3, Creator, Region, UTM20,Creation_date)
	OUTPUT INSERTED.TSta_PK_ID INTO {tableName} (TSta_PK_ID)
	SELECT date,LAT,LON,name,FieldActivity_Name,FieldActivity_ID,FieldWorker1,FieldWorker2,FieldWorker3,
	 Creator, region,UTM20,Creation_date
	 FROM {tableName};

	'''.format(tableName=tempName, minLON=min(df['LON']), minLAT=min(df['LAT']), maxLON=max(df['LON']), maxLAT=max(df['LAT']))

	try :
		DBSession.execute(query)
		print (time.time()-start)
		
		# -------------------------- #
		# Retrieve new station created 
		query=select([Station]).where(and_(Station.creator==request.authenticated_userid,Station.creationDate==creation_date))
		stationList=DBSession.execute(query).fetchall()
		result=[{'PK':sta['TSta_PK_ID'], 'Name':sta['Name'], 'Date_': sta.date.strftime('%d/%m/%Y %H:%M:%S')
		,'LAT':sta['LAT'], 'LON':sta['LON'],'FieldWorker1':data[0]['fieldWorker1']
		,'FieldWorker2':data[0]['fieldWorker2'],'FieldWorker3':data[0]['fieldWorker3']
		,'FieldActivity_Name':sta['FieldActivity_Name'], 'Region':sta['Region'], 'UTM20':sta['UTM20']
		, 'FieldWorker4':'','FieldWorker5':'' } for sta in stationList]
		transaction.commit()
		
		return {
		'response':str(len(stationList))+' stations were added with succes, '
		+str(len(final)-len(stationList))+' are already existing'
		,'data': result }

	except Exception as err:
		print ('_______EXCEPTION______')
		msg = err.args[0] if err.args else ""
		response=Response('Problem occurs on station import : '+str(type(err))+' = '+msg)
		response.status_int = 500
		return response 

	finally:
		transaction.commit()
		tempTable.drop(Base.metadata.bind)
		Base.metadata.remove(tempTable)


@view_config(route_name=prefix+'/station_byDate', renderer='json', request_method='GET')
def station_byDate (request) :

	data=reques.params

	query= select(Station).filter(Station.date>=data.get('begin_date')).filter(Station.date<=data.get('end_date'))
	result= DBSession.execute(query).fetchall()
	
	return result

@view_config(route_name=prefix+'/search', renderer='json', request_method='POST')
def station_search (request) :
	start=time.time()
	table=Base.metadata.tables['V_Search_AllStation_with_MonitoredSite_Indiv2']
	
	criteria = json.loads(request.POST.get('criteria', '{}'))
	
	dictio={
	'pk':'id',
	'region':'Region',
	'begindate':'date',
	'enddate':'date',
	'date_':'date',
	'maxlat':'LAT',
	'minlat':'LAT',
	'maxlon':'LON',
	'minlon':'LON',
	'fieldactivity':'FieldActivity_Name',
	'sitename':'site_name',
	'monitoredsitetype':'site_type',
	'individ':'ind_id',
	}

	query=select([table.c['id'].label('PK'), table.c['Name']
		,cast(table.c['date'],DateTime).label('Date_')
		,table.c['LAT'], table.c['LON'],table.c['FieldWorker1']
		,table.c['FieldWorker2'],table.c['FieldWorker3']
		,table.c['FieldActivity_Name'], table.c['Region']
		, table.c['UTM20']]).distinct()

	for key, obj in criteria.items():
		print(key)
		print(obj)

		if obj['Value'] != None:
			try:
				Col=dictio[key.lower()]
			except: 
				Col=key	
			
			if key.lower() == 'fieldworker' :
				query=query.where(or_(table.c['FieldWorker1_ID']==obj['Value'],
					table.c['FieldWorker2_ID']==obj['Value'],
					table.c['FieldWorker3_ID']==obj['Value']))
			if 'date' in key.lower() :
				op1=cast(table.c[Col],Date)
				query=query.where(eval_.eval_binary_expr(op1, obj['Operator'], obj['Value']))

			else:
				query=query.where(eval_.eval_binary_expr(table.c[Col], obj['Operator'], obj['Value']))

	print(query)

	total = DBSession.execute(select([func.count()]).distinct().select_from(query.alias())).scalar()
	result = [{'total_entries':total}]


	order_by = json.loads(request.POST.get('order_by', '[]'))
	print(order_by)
	order_by_clause = []
	for obj in order_by:
		column, order = obj.split(':')
		if column.lower() in dictio :
			column=dictio[column.lower()]
		if column in table.c:
			if order == 'asc':
				order_by_clause.append(table.c[column].asc())
			elif order == 'desc':
				order_by_clause.append(table.c[column].desc())
	if len(order_by_clause) > 0:
		print(order_by_clause)
		query = query.order_by(*order_by_clause)


	# Define the limit and offset if exist
	offset = int(request.POST.get('offset', 0))
	limit = int(request.POST.get('per_page', 0))
	if limit > 0:
		query = query.limit(limit)
	if offset > 0:
		query = query.offset(offset)
	
	data=DBSession.execute(query).fetchall()

	print('_____DATA______')
	list_sta = []
	for row in data :
		row = OrderedDict(row)
		row['Date_'] = row['Date_'].strftime('%d/%m/%Y %H:%M')
		
		list_sta.append(OrderedDict(row))
	result.append(list_sta)
	stop=time.time()
	print ('____ time '+str(stop-start))
	return result
