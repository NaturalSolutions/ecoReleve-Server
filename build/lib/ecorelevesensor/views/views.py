from collections import OrderedDict
from array import array
from geopy.distance import vincenty

from pyramid.response import Response
from pyramid.view import view_config

from sqlalchemy.exc import DBAPIError
from sqlalchemy import over, Float, between, func, cast, Date, String, desc, select, create_engine, text, union, join, and_, insert, bindparam, Sequence, update, or_, literal_column
from sqlalchemy.sql.expression import label

from pyramid.httpexceptions import HTTPBadRequest, HTTPCreated, HTTPServerError, HTTPOk

import datetime, operator, time
import re, csv



from ecorelevesensor.models import DBSession, _Base

from ecorelevesensor.utils.spreadsheettable import SpreadsheetTable
from ecorelevesensor.utils.formula import CurrentPageColSum, PreviousPagesColSum, TotalPagesColSum, RowNumber  

from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, BaseDocTemplate, PageTemplate    
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus.flowables import PageBreak 
from reportlab.lib import colors  

from ecorelevesensor.models.sensor import Argos, Gps, Rfid
from ecorelevesensor.models.data import (
   Individuals,
   ProtocolArgos,
   ProtocolGps,
   ProtocolIndividualEquipment,
   SatTrx,
   Station,
   ViewRfid,
   MonitoredStation,
   ProtocolStationEquipment,
   ThemeEtude,
   MapSelectionManager,
   User,
   Protocole
   )

# Data imported from the CLS WS during the last week.
@view_config(route_name='weekData', renderer='json')
def weekData(request):
   # Initialize Json object
   data = {
      'label':[str(datetime.date.today() - datetime.timedelta(days = i)) for i in range(1,8)],
      'nbArgos': [0] * 7,
      'nbGPS': [0] * 7
   }

   # Argos data
   argos_query = select([cast(Argos.date, Date).label('date'), func.count(Argos.id).label('nb')]).where(Argos.date >= datetime.date.today() - datetime.timedelta(days = 7)).group_by(cast(Argos.date, Date))
   for date, nb in DBSession.execute(argos_query).fetchall():
      try:
         i = data['label'].index(str(date))
         data['nbArgos'][i] = nb
      except:
         pass

   # GPS data
   gps_query = select([cast(Gps.date, Date).label('date'), func.count(Gps.id).label('nb')]).where(Gps.date >= datetime.date.today() - datetime.timedelta(days = 7)).group_by(cast(Gps.date, Date))
   for date, nb in DBSession.execute(gps_query).fetchall():
      try:
         i = data['label'].index(str(date))
         data['nbGPS'][i] = nb
      except:
         pass
   
   return data

# Unchecked data for one PTT.
@view_config(route_name='argos/unchecked', renderer='json')
def argos_unchecked(request):
   
   # ptt is a mandatory parameter.
   try:
      ptt = int(request.GET['ptt'])
   except:
      raise HTTPBadRequest()

   # Get all unchecked data for this ptt and this individual
   argos_data = select([Argos.id.label('id'), Argos.date.label('date'), cast(Argos.lat, String).label('lat'), cast(Argos.lon, String).label('lon'), Argos.lc.label('lc'), literal_column('0').label('type')]
                       ).where(and_(Argos.checked == False, Argos.ptt == ptt))
   gps_data = select([Gps.id.label('id'), Gps.date.label('date'), cast(Gps.lat, String).label('lat'), cast(Gps.lon, String).label('lon'), literal_column('NULL').label('lc'),literal_column('1').label('type')]
                     ).where(and_(Gps.checked == False, Gps.ptt == ptt))
   unchecked = union(argos_data, gps_data).alias('unchecked')

   # ind_id is a facultative parameter
   try:
      ind_id = int(request.GET['ind_id'])
      all_data = select([unchecked.c.id, unchecked.c.date, unchecked.c.lat, unchecked.c.lon, unchecked.c.lc, unchecked.c.type]).select_from(
         unchecked.join(SatTrx, SatTrx.ptt == ptt).join(ProtocolIndividualEquipment, and_(
            SatTrx.id == ProtocolIndividualEquipment.sat_id, unchecked.c.date >= ProtocolIndividualEquipment.begin_date, or_(
               unchecked.c.date < ProtocolIndividualEquipment.end_date, ProtocolIndividualEquipment.end_date == None
               )
            )
         )
      ).where(
         ProtocolIndividualEquipment.ind_id == ind_id
      )
   except KeyError, TypeError:
      all_data = select([unchecked.c.id, unchecked.c.date, unchecked.c.lat, unchecked.c.lon, unchecked.c.lc, unchecked.c.type])
      ind_id = None

   # Initialize json object
   data = {'ptt':{}, 'locations':[], 'indiv':{}}
   
   # Type 0 = Argos data, type 1 = GPS data
   for id, date, lat, lon, lc, type in DBSession.execute(all_data.order_by(desc('date'))).fetchall():
      data['locations'].append({'id': id, 'type':type, 'date':str(date), 'lat':lat, 'lon':lon, 'lc':lc, 'dist':0})
      try:
         # Distance from last location
         data['locations'][-2]['dist'] = round(vincenty((data['locations'][-2]['lat'], data['locations'][-2]['lon']), (data['locations'][-1]['lat'], data['locations'][-1]['lon'])).kilometers, 3)
      except IndexError:
         pass
      
   # Get informations for this ptt
   ptt_infos = select([SatTrx.ptt, SatTrx.manufacturer, SatTrx.model]).where(SatTrx.ptt == ptt)
   data['ptt']['ptt'], data['ptt']['manufacturer'], data['ptt']['model'] = DBSession.execute(ptt_infos).fetchone()

   # Get informations for the individual
   if ind_id is not None:
      indiv_infos = select([Individuals.id, Individuals.age, Individuals.sex, Individuals.specie, Individuals.monitoring_status, Individuals.origin, Individuals.survey_type]).where(Individuals.id == ind_id)
      data['indiv']['id'], data['indiv']['age'], data['indiv']['sex'], data['indiv']['specie'], data['indiv']['monitoring_status'], data['indiv']['origin'], data['indiv']['survey_type'] = DBSession.execute(indiv_infos).fetchone()
      # Last known location
      data['indiv']['last_loc'] = {}
      last_loc = data['indiv']['last_loc']
      query = 'select convert(varchar, StaDate, 120), convert(float, LAT), convert(float, LON) from ecoReleve_Data.dbo.fn_v_qry_GetMaxStation(:ind_id)'
      last_loc['date'], last_loc['lat'], last_loc['lon'] = DBSession.execute(text(query), {'ind_id':ind_id}).fetchone()

   return data

# List all PTTs having unchecked locations, with individual id and number of locations.
@view_config(route_name='argos/unchecked/list', renderer='json')
def argos_unchecked_list(request):
   # Initialize Json array
   data = []
   # SQL query
   unchecked = union(select([Argos.id.label('id'), Argos.ptt.label('ptt'), Argos.date.label('date')]).where(Argos.checked == 0),
                  select([Gps.id.label('id'), Gps.ptt.label('ptt'), Gps.date.label('date')]).where(Gps.checked == 0)).alias()
   # Add the bird associated to each ptt.
   unchecked_with_ind = select([ProtocolIndividualEquipment.ind_id.label('ind_id'), 'ptt', func.count('id').label('nb')]).select_from(
      unchecked.join(SatTrx, SatTrx.ptt == unchecked.c.ptt).outerjoin(
      ProtocolIndividualEquipment, and_(SatTrx.id == ProtocolIndividualEquipment.sat_id, unchecked.c.date >= ProtocolIndividualEquipment.begin_date, or_(unchecked.c.date < ProtocolIndividualEquipment.end_date, ProtocolIndividualEquipment.end_date == None)))
      ).group_by('ptt', ProtocolIndividualEquipment.ind_id).order_by('ptt')
   # Populate Json array
   for ind_id, ptt, nb in DBSession.execute(unchecked_with_ind).fetchall():
      data.append({'ptt':ptt,'ind_id':ind_id, 'count':nb})
   return data

# Count the number of unchecked data.
@view_config(route_name = 'argos/unchecked/count', renderer = 'json')
def argos_unchecked_count(request):
   return DBSession.execute(select([func.count(Argos.id)]).where(Argos.checked == 0)).scalar()

@view_config(route_name = 'argos/insert', renderer = 'json')
def argos_insert(request):
   stations = []
   argos_id = array('i')
   gps_id = array('i')

   # Query that check for duplicate stations
   check_duplicate_station = select([func.count(Station.id)]).where(and_(Station.name == bindparam('name'), Station.lat == bindparam('lat'), Station.lon == bindparam('lon'), Station.ele == bindparam('ele')))
   
   # For each objet in the request body
   for ptt_obj in request.json_body:
      ptt = ptt_obj['ptt']
      ind_id = ptt_obj['ind_id']
         
      # For each location associated with this object
      for location in ptt_obj['locations']:
         # Argos
         if location['type'] == 0:
            # Get all the informations about the sensor data
            argos_data = DBSession.query(Argos).filter_by(id=location['id']).one()
            name = 'ARGOS_' + str(argos_data.ptt) + '_' + argos_data.date.strftime('%Y%m%d%H%M%S')
            if DBSession.execute(check_duplicate_station, {'name':name, 'lat':argos_data.lat, 'lon':argos_data.lon, 'ele':argos_data.ele}).scalar() == 0:
               argos = ProtocolArgos(ind_id=ind_id, lc=argos_data.lc, iq=argos_data.iq, nbMsg=argos_data.nbMsg, nbMsg120=argos_data.nbMsg120,
                                       bestLvl=argos_data.bestLvl, passDuration=argos_data.passDuration, nopc=argos_data.nopc, frequency=argos_data.frequency)
               station = Station(date=argos_data.date, name=name, fieldActivityId=27, fieldActivityName='Argos', lat=argos_data.lat, lon=argos_data.lon, ele=argos_data.ele, protocol_argos=argos)
               # Add the station in the list
               argos_id.append(location['id'])
               stations.append(station)
         # Gps
         elif location['type'] == 1:
            gps_data = DBSession.query(Gps).filter_by(id=location['id']).one()
            name = 'ARGOS_' + str(gps_data.ptt) + '_' + gps_data.date.strftime('%Y%m%d%H%M%S')
            if DBSession.execute(check_duplicate_station, {'name':name, 'lat':argos_data.lat, 'lon':argos_data.lon, 'ele':argos_data.ele}).scalar() == 0:    
               gps = ProtocolGps(ind_id=ind_id, course=gps_data.course, speed=gps_data.speed)
               station = Station(date=argos_data.date, name=name, fieldActivityId=27, fieldActivityName='Argos', lat=argos_data.lat, lon=argos_data.lon, ele=argos_data.ele, protocol_gps=gps)
               # Add the station in the list
               gps_id.append(location['id'])
               stations.append(station)
   # Insert the stations (and protocols thanks to ORM)
   DBSession.add_all(stations)
   # Update the sensor database
   DBSession.execute(update(Argos).where(Argos.id.in_(argos_id)).values(checked=True, imported=True))
   DBSession.execute(update(Gps).where(Gps.id.in_(gps_id)).values(checked=True, imported=True))
   return {'status':'ok'}

@view_config(route_name = 'argos/check', renderer = 'json')
def argos_check(request):
   argos_id = array('i')
   gps_id = array('i')
   try:
      for ptt_obj in request.json_body:
         ptt = ptt_obj['ptt']
         ind_id = ptt_obj['ind_id']
         for location in ptt_obj['locations']:
            if location['type'] == 0:
               argos_id.append(location['id'])
            elif location['type'] == 1:
               gps_id.append(location['id'])
      DBSession.execute(update(Argos).where(Argos.id.in_(argos_id)).values(checked=True))
      DBSession.execute(update(Gps).where(Gps.id.in_(gps_id)).values(checked=True))
      return {'argosChecked': len(argos_id), 'gpsChecked':len(gps_id)}
   except Exception as e:
      raise

@view_config(route_name = 'station_graph', renderer = 'json')
def station_graph(request):
   # Initialize Json object
   data = OrderedDict()

   # Calculate the bounds
   today = datetime.date.today()
   begin_date = datetime.date(day = 1, month = today.month, year = today.year - 1)
   end_date = datetime.date(day = 1, month = today.month, year = today.year)

   # Query
   query = select([func.count(Station.id).label('nb'), func.year(Station.date).label('year'), func.month(Station.date).label('month')]
                  ).where(and_(Station.date >= begin_date, Station.date < end_date)).group_by(func.year(Station.date), func.month(Station.date))

   # Execute query and sort result by year, month (faster than an order_by clause in this case)
   for nb, y, m in sorted(DBSession.execute(query).fetchall(), key = operator.itemgetter(1,2)):
      data[datetime.date(day = 1, month = m, year = y).strftime('%b') + ' ' + str(y)] = nb

   return data

@view_config(route_name = 'rfid_import', renderer = 'string')
def rfid_import(request):
   data = []
   message = ""
   field_label = []
   isHead = False
   try:
      content = request.POST['data']
      if re.compile('\r\n').search(content):
         data = content.split('\r\n')
      elif re.compile('\n').search(content):
         data = content.split('\n')
      elif re.compile('\r').search(content):
         data = content.split('\r')

      fieldtype1 = {'NB':'no','TYPE':'type','"PUCE "':'code','DATE':'no','TIME':'no'}
      fieldtype2 = {'#':'no','Transponder Type:':'type','Transponder Code:':'code','Date:':'no','Time:':'no','Event:':'Event','Unit #:':'Unit','Antenna #:':'Antenna','Memo:':'Memo','Custom:':'Custom','':''}
      fieldtype3 = {'Transponder Type:':'type','Transponder Code:':'code','Date:':'no','Time:':'no','Event:':'Event','Unit #:':'Unit','Antenna #:':'Antenna','Memo:':'Memo','Custom:':'Custom'}
   
      entete = data[0] 
      if re.compile('\t').search(entete):
         separateur = '\t'
      elif re.compile(';').search(entete):
         separateur = ';'
      entete = entete.split(separateur)
      #file with head
      if (sorted(entete) == sorted(fieldtype1.keys())):
         field_label = ["no","Type","Code","date","time"]
         isHead = True
      elif (sorted(entete) == sorted(fieldtype2.keys())):
         field_label = ["no","Type","Code","date","time","no","no","no","no","no"]
         isHead = True
      elif (sorted(entete) == sorted(fieldtype3.keys())):
         field_label = ["Type","Code","date","time","no","no","no","no","no"]  
         isHead = True
      else:# without head
         isHead = False
         if separateur == ';':
            field_label = ["no","Type","Code","date","time","no","no","no","no","no"]
         else:
            if len(entete) > 5:
               field_label = ["Type","Code","date","time","no","no","no","no","no"]
               if entete[0] == 'Transponder Type:':
                  isHead = True
            else: 
               field_label = ["no","Type","Code","date","time"]

      j=0
      code = ""
      date = ""
      dt = ""
      Rfids = []
      if (isHead):
         j=1
      #parsing data
      while j < len(data):
         i = 0
         if data[j] != "":
            row = data[j].replace('"','').split(separateur)
            while i < len(field_label):
               if field_label[i] == 'Code':
                  code = row[i]
               if field_label[i] == 'date':
                  date = row[i]
               if field_label[i] == 'time':
                  time = re.sub('\s','',row[i])
                  format_dt = '%d/%m/%Y %H:%M:%S'
                  if re.search('PM|AM',time):
                     format_dt = '%d/%m/%Y %I:%M:%S%p'
                  dt = date+' '+time
                  dt = datetime.datetime.strptime(dt, format_dt).strftime('%d-%m-%Y %H:%M:%S')
               i=i+1
         
         id_rfid = DBSession.execute(select([Rfid.id]).where(and_(Rfid.code == code,  Rfid.date == dt))).scalar()
         if id_rfid is None:
            Rfids.append({'_code':code, '_date':dt})
         j=j+1 
      
      if len(Rfids) > 0:
         if DBSession.execute(insert(Rfid).values(code=bindparam('_code'), date=bindparam('_date')),Rfids):
            message = str(len(Rfids))+' rows inserted'
      else:
         message = 'The data already exists'
   except Exception as e:
      message = e   
   return message
   
@view_config(route_name = 'rfid_list', renderer = 'json')
def rfid_list(request):
   data = []
   try:
      for id in DBSession.execute(select([ViewRfid.id])).fetchall():
         data.append({'id':id[0]})
      return data
   except Exception as e:
      print e

@view_config(route_name = 'monitored_station_list', renderer = 'json')
def monitored_station_list(request):
   data = []
   try:
      for id in DBSession.execute(select([MonitoredStation.id])).fetchall():
         data.append({'id':id[0]})
      return data
   except Exception as e:
      print e

@view_config(route_name = 'rifd_monitored_add', renderer = 'string')
def rifd_monitored_add(request):
   message = ""
   try:
      begin_date = datetime.datetime.today().strftime('%d-%m-%Y %H:%M:%S')
      fk_rfid = request.GET['rfid']
      fk_geo = request.GET['site']
      if DBSession.execute(insert(ProtocolStationEquipment).values({"FK_RFID_obj":int(fk_rfid), "FK_GeoID":int(fk_geo), "beginDATE":begin_date})):
         message = 'Row inserted successfully '
   except Exception as e:
      message = e
   return message

@view_config(route_name = 'theme/list', renderer = 'json')
def theme_list(request):
   data = []
   try:
      j = join(ThemeEtude, MapSelectionManager, ThemeEtude.id == MapSelectionManager.TSMan_FK_Theme)
      query = select([ThemeEtude.id, ThemeEtude.Caption]).where(ThemeEtude.Actif == 1).group_by(ThemeEtude.id, ThemeEtude.Caption).order_by(ThemeEtude.Caption)
      try:
         if(request.GET['export'] is not None):
            query = query.select_from(j)
      except:
         pass
      for id, caption in DBSession.execute(query).fetchall():
         data.append({'id':id, 'caption': caption})
      try:
         if(request.GET['export'] is not None):
            data.append({'id':'null', 'caption': 'Others'})
      except:
         pass
   except Exception as e:
      print e
   return data

@view_config(route_name = 'core/user/fieldworkers', renderer = 'json')
def fieldWorkers(request):
   data = []
   try:
      for id, name in DBSession.execute(select([User.id, (User.TUse_Nom+' '+User.TUse_Prenom)]).order_by(User.TUse_Nom+' '+User.TUse_Prenom)).fetchall():
         data.append({'ID':id, "Nom":name})
   except Exception as e:
      print e
   return data

@view_config(route_name = 'core/protocoles/list', renderer = 'string')
def protocoles_list(request):
   xml = "<protocoles>"
   try:
      for id, relation, caption, description in DBSession.execute(select([Protocole.id, Protocole.Relation, Protocole.Caption, Protocole.Description]).where(Protocole.Active == 1).order_by(Protocole.Caption)).fetchall():
         xml = xml + "<protocole id='"+str(id)+"'>"+caption+"</protocole>"
      xml = xml + "</protocoles>"
   except Exception as e:
      print e
   request.response.content_type = "text/xml"
   return xml

@view_config(route_name = 'core/views/list', renderer = 'string')
def views_list(request):
   xml = "<views>"
   try:
      query = select([MapSelectionManager.id, MapSelectionManager.TSMan_sp_name, MapSelectionManager.TSMan_Layer_Name, MapSelectionManager.TSMan_Description, MapSelectionManager.TSMan_FK_Theme]).order_by(MapSelectionManager.TSMan_Layer_Name)
      try:
         if request.GET['id_theme'] is not None:
            query = query.where(MapSelectionManager.TSMan_FK_Theme == request.GET['id_theme'])
      except Exception as e:
         print e
      for id, sp_name, layer_name, description, fk_theme in DBSession.execute(query).fetchall():
         xml = xml + "<view id='"+sp_name+"'>"+layer_name.replace("_", " ")+"</view>"
      xml = xml + "</views>"
   except Exception as e:
      print e
   request.response.content_type = "text/xml"
   return xml

@view_config(route_name = 'core/views/export/details', renderer = 'json')
def views_details(request):
   data = []
   try:
      name_vue = request.matchdict['name']
      table = _Base.metadata.tables['ecoReleve_Data.dbo.'+name_vue]
      print table
      for column in table.c:
         name_c = str(column.name)
         type_c = str(column.type)
         if re.compile('VARCHAR').search(type_c):
            type_c = 'string'
         data.append({'name':name_c, 'type':type_c})
      return data
   except Exception as e:
      print e

@view_config(route_name = 'core/views/export/count', renderer = 'json')
def views_count(request):
   try:
      name_vue = request.matchdict['name']
      table = _Base.metadata.tables['ecoReleve_Data.dbo.'+name_vue]
      count = DBSession.execute(table.count()).scalar()
      return count
   except Exception as e:
      print e

@view_config(route_name = 'core/views/export/filter/count', renderer = 'json')
def views_filter_count(request):
   try:
      name_vue = request.matchdict['name']
      table = _Base.metadata.tables['ecoReleve_Data.dbo.'+name_vue]
      criteria = request.params

      query = select([func.count(table.c.values()[0])])
      query = query_criteria(query, table, criteria)

      count = DBSession.execute(query).scalar()
      return count
   except Exception as e:
      print e

@view_config(route_name = 'core/views/export/filter/geo', renderer = 'json')
def views_filter(request):
   try:
      name_vue = request.matchdict['name']
      table = _Base.metadata.tables['ecoReleve_Data.dbo.'+name_vue]
      criteria = request.params
      result = {'type':'FeatureCollection', 'features':[]}
      query = select([cast(table.c['LAT'].label('lat'), Float), cast(table.c['LON'].label('lon'), Float), func.count(table.c.values()[0])]).group_by(table.c['LAT'].label('lat'), table.c['LON'])
      query = query_criteria(query, table, criteria)
      for lat, lon, nb in  DBSession.execute(query).fetchall():
         result['features'].append({'type':'Feature', 'properties':{'count': nb}, 'geometry':{'type':'Point', 'coordinates':[lon,lat]}})
      return result
   except Exception as e:
      print e

@view_config(route_name = 'core/views/export/filter/result', renderer = 'json')
def views_filter_result(request):
   try:
      name_vue = request.matchdict['name']
      table = _Base.metadata.tables['ecoReleve_Data.dbo.'+name_vue]
      criteria = request.params
      skip = 0
      limit = 10
      try:
         if criteria['skip']:
            skip = int(criteria['skip'])
      except:
         pass
      try:
         if criteria['limit']:
            limit = int(criteria['limit'])
      except:
         pass
      columns = []
      cols = []
      if criteria['columns']:
         columns.append(func.row_number().over(order_by=table.c.values()[0].asc()).label('Id'))
         cols = criteria['columns'].split(',')
         for col in cols:
            columns.append(table.c[col])
     
      #count
      query_count = select([func.count(table.c.values()[0])])
      query_count = query_criteria(query_count, table, criteria)
      count = DBSession.execute(query_count).scalar()
      # select data
      query = select(columns)
      query = query_criteria(query, table, criteria)
      query = query.order_by(table.c.values()[0].asc()).limit(limit).offset(skip)

      data = DBSession.execute(query).fetchall()
      result = {'count':str(count), 'values':[]}
      result['values'] = [dict(row) for row in data]
      for obj in result['values']:
         for key, item in obj.items():
               obj[key] = unicode(item)
      return result
   except Exception as e:
      print e

@view_config(route_name = 'core/views/export/filter/export', renderer = 'json')
def views_filter_export(request):
   try:
      name_vue = request.matchdict['name']
      table = _Base.metadata.tables['ecoReleve_Data.dbo.'+name_vue]
      criteria = request.params
      today = datetime.datetime.today().strftime('%d_%m_%Y %H_%M_%S')
      name_file = name_vue+"_"+today
      columns = []
      cols = []
      if criteria['columns']:
            cols = criteria['columns'].split(',')
            for col in cols:
               columns.append(table.c[col])
      query = select(columns)
      query = query_criteria(query, table, criteria)
      rows = DBSession.execute(query).fetchall()

      # generated CSV file
      csv_file = csv.writer(open("Files/csv/"+name_file+".csv", "wb"))
      csv_file.writerow(cols)

      data = []
      for obj in rows:
         row = []
         row_csv = []
         for item in obj:
            row.append(unicode(item))
            try:
               row_csv.append(item.encode("utf-8"))
            except:
               row_csv.append(item)

         csv_file.writerow(row_csv)
         data.append(row)

      #generated GPX file
      gpx='<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n<gpx xmlns="http://www.topografix.com/GPX/1/1" creator="byHand" version="1.1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">\n'
      gpx_data = [dict(row) for row in rows]
      for obj in gpx_data:
         lat, lon, date, sitename = "", "", "", ""
         for key, item in obj.items():
            if key == "LAT":
               lat = str(item)
            elif key == "LON":
               lon = str(item)
            elif key == "DATE":
               date = str(item)
            elif key == "Site_name":
               sitename = str(item)
         gpx = gpx + "\n<wpt lat='"+lat+"' lon='"+lon+"'>\n<ele></ele>\n<time>"+date+"</time>\n<desc></desc>\n<name>"+sitename+"</name>\n<sym>Flag, Blue</sym>\n</wpt>\n";
      gpx = gpx + "</gpx>"
  
      file_gpx = open("Files/gpx/"+name_file+".gpx", "w")
      file_gpx.write(gpx)
      file_gpx.close()

      # generated PDF file
      table_font_size = 9
      if name_vue == "V_Qry_VIndiv_MonitoredLostPostReleaseIndividuals_LastStations":
         table_font_size = 8
         for key in range(len(cols)):
            if cols[key] == 'DATE':
               cols[key] = 'Date lastpos'
            elif cols[key] == 'Name_signal_type':
               cols[key] = 'Signal'
            elif cols[key] == 'MonitoringStatus@Station':
               cols[key] = 'Monitoring st.'
            elif cols[key] == 'SurveyType@Station':
               cols[key] = 'Servey type'
         cols.append('Date')
      else:
         cols.append('Date de saisie')
      
      cols.append('Vu')
      cols.append('Entendu')
      cols.append('Perdu')
      cols.append('Mort')
      cols.append('Repro')
      cols.append('No check')

      data.insert(0,cols)

      def addPageNumber(canvas, doc):
         page_num = canvas.getPageNumber()
         text = "Page %s" % page_num
         canvas.setFont('Times-BoldItalic', 9)
         canvas.drawRightString(145*mm, 5*mm, text)

      styleSheet = getSampleStyleSheet()
      doc = SimpleDocTemplate("Files/pdf/"+name_file+".pdf",pagesize=landscape(A4),rightMargin=72,leftMargin=72,topMargin=20,bottomMargin=18)
      Story=[]
       
      styles=getSampleStyleSheet()
      styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))

      Story.append(Paragraph("Export "+name_vue, styleSheet['Title']))
      Story.append(Spacer(0, 5 * mm))
      if name_vue == "V_Qry_VIndiv_MonitoredLostPostReleaseIndividuals_LastStations":
         Story.append(Paragraph("Nom de l\'observateur:_____________________________",styleSheet['BodyText']))  
         Story.append(Paragraph("Secteur de suivi: _____________________ Date de Saisie: _________________",styleSheet['BodyText']))  
         Story.append(Spacer(0, 10 * mm))

      table_style = [  
        ('GRID', (0,0), (-1,-1), 1, colors.black),  
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),  
        ('LEFTPADDING', (0,0), (-1,-1), 3),  
        ('RIGHTPADDING', (0,0), (-1,-1), 3),  
        ('FONTSIZE', (0,0), (-1,-1), table_font_size),  
        ('FONTNAME', (0,0), (-1,0), 'Times-Bold'),  
      ]  
      spreadsheet_table = SpreadsheetTable(data, repeatRows = 1)  
      spreadsheet_table.setStyle(table_style)  
      Story.append(spreadsheet_table)  
      Story.append(PageBreak()) 
      doc.build(Story, onFirstPage=addPageNumber, onLaterPages=addPageNumber)

      return name_file
   except Exception as e:
      raise

def query_criteria(query, table, criteria):
   for column, value in criteria.items():
         if column in table.c:
            if re.search(',',value):
               sp = value.split(',')
               if sp[0] == 'IN':
                  if re.search('|',sp[1]):
                     data = sp[1].split('|')
                  else:
                     data = sp[1]
                  query = query.where(table.c[column].in_(data))
               elif sp[0] == 'LIKE':  
                  query = query.where(table.c[column].like('%'+sp[1]+'%'))
               elif sp[0] == '<':
                  query = query.where(table.c[column] < sp[1])
               elif sp[0] == '>':
                  query = query.where(table.c[column] > sp[1])
               elif sp[0] == '<>':
                  query = query.where(table.c[column] != sp[1])
            else:
               if value == 'IS NULL':
                  query = query.where(table.c[column].is_(None))
               elif value == 'IS NOT NULL':
                  query = query.where(table.c[column].isnot(None))
               else:
                  query = query.where(table.c[column] == value)
         else:
            if column == 'bbox':
               sp = value.split(',')
               query = query.where(and_(between(table.c['LAT'], float(sp[1]), float(sp[3])), between(table.c['LON'], float(sp[0]), float(sp[2]))))
   return query












