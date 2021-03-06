"""
Created on Thu Aug 28 16:45:25 2014
@author: Natural Solutions (Thomas)
"""

import re, operator
from datetime import datetime

from pyramid.view import view_config
from sqlalchemy import select, insert, text, desc, bindparam, or_, outerjoin, func
from sqlalchemy.exc import IntegrityError
import json
from ecorelevesensor.models import (
    DBSession,
    DataRfid,
    dbConfig,
    Individual,
    MonitoredSite, 
    MonitoredSiteEquipment,
    MonitoredSitePosition,
    Base
)
from ecorelevesensor.models.object import ObjectRfid
from collections import OrderedDict

prefix='rfid/'

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
    return get_operator_fn(operator)(op1, op2)

@view_config(route_name='rfid', renderer='json', request_method='GET')
def rfid_get(request):
    return DBSession.query(ObjectRfid).all()
    
@view_config(route_name='rfid', renderer='string', request_method='POST')
def rfid_add(request):
    try:
        obj = ObjectRfid()
        obj.identifier = request.json_body.get('identifier', None)
        obj.creator = request.authenticated_userid
        DBSession.add(obj)
        rfid = DBSession.query(ObjectRfid.id
            ).filter(ObjectRfid.identifier==obj.identifier).scalar()
    except IntegrityError:
        request.response.status_code = 500
        return 'Error: An object with the same identifier already exists.'
    return ' '.join(['Success: RFID module created with ID =', str(rfid), '.'])

@view_config(route_name=prefix+'byName', renderer='json')
def rfid_detail(request):
    name = request.matchdict['name']
    data = DBSession.query(ObjectRfid, MonitoredSite, MonitoredSiteEquipment
        ).outerjoin(MonitoredSiteEquipment, ObjectRfid.id==MonitoredSiteEquipment.obj
        ).outerjoin(MonitoredSite, MonitoredSiteEquipment.site==MonitoredSite.id
        ).filter(ObjectRfid.identifier==name
        ).order_by(desc(MonitoredSiteEquipment.begin_date)).first()
    module, site, equip = data
    result = {'module': module, 'site':site, 'equip':equip}
    return result

@view_config(route_name=prefix+'byDate', renderer='json')
def rfid_active_byDate(request):
    date = datetime.strptime(request.params['date'], '%d/%m/%Y  %H:%M:%S')
    data = DBSession.query(MonitoredSite.name, MonitoredSite.type_,  MonitoredSitePosition.lat,  MonitoredSitePosition.lon
        ).outerjoin(MonitoredSitePosition, MonitoredSite.id==MonitoredSitePosition.id
        ).filter(MonitoredSitePosition.begin_date <= date
        ).filter(or_(MonitoredSitePosition.end_date >= date, MonitoredSitePosition.end_date == None )).all()
    siteName_type=[{'type':row[1] , 'name':row[0], 'positions': {'lat': row[2], 'lon': row[3] }} for row in data]
    result = {'siteType': list(set([row[1] for row in data])), 'siteName_type': siteName_type}
    return result


@view_config(route_name=prefix+'identifier', renderer='json')
def rfid_get_identifier(request):
    query = select([ObjectRfid.identifier]).where(ObjectRfid.type_=='rfid')
    return [row[0] for row in DBSession.execute(query).fetchall()]

@view_config(route_name=prefix+'import', renderer='string')
def rfid_import(request):
    data = []
    message = ""
    field_label = []
    isHead = False
    try:
        creator = request.authenticated_userid
        content = request.POST['data']
        module = request.POST['module']
        idModule = DBSession.execute(select([ObjectRfid.id]).where(ObjectRfid.identifier==module)).scalar();

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
        Rfids, chip_codes = set(), set()
        if (isHead):
            j=1
        #parsing data
        while j < len(data):
            i = 0
            if data[j] != "":
                line = data[j].replace('"','').split(separateur)
                while i < len(field_label):
                    if field_label[i] == 'Code':
                        code = line[i]
                    if field_label[i] == 'date':
                        date = line[i]
                    if field_label[i] == 'time':
                        time = re.sub('\s','',line[i])
                        format_dt = '%d/%m/%Y %H:%M:%S'
                        if re.search('PM|AM',time):
                            format_dt = '%m/%d/%Y %I:%M:%S%p'
                        dt = date+' '+time
                        dt = datetime.strptime(dt, format_dt)
                    i=i+1
                Rfids.add((creator, idModule, code, dt))
                chip_codes.add(code)
            j=j+1
        Rfids = [{DataRfid.creator.name: crea, DataRfid.obj.name: idMod, 
                DataRfid.chip_code.name: c, DataRfid.date.name: d} for crea, idMod, c, d  in Rfids]
        # Insert data.
        DBSession.execute(insert(DataRfid), Rfids)
        message = str(len(Rfids)) +' rows inserted.'
        # Check if there are unknown chip codes.
        query = select([Individual.chip_code]).where(Individual.chip_code.in_(chip_codes))
        known_chips = set([row[0] for row in DBSession.execute(query).fetchall()])
        unknown_chips = chip_codes.difference(known_chips)
        if len(unknown_chips) > 0:
            message += '\n\nWarning : chip codes ' + str(unknown_chips) + ' are unknown.'
    except IntegrityError as e:
        request.response.status_code = 500
        message = 'Error : data already exist.\n\nDetail :\n' + str(e.orig)
    except Exception as e:
        request.response.status_code = 520
        message = 'Error'
    return message

@view_config(route_name=prefix+'validate', renderer='string')
def rfid_validate(request):
    #TODO: SQL SERVER specific code removal
    stmt = text("""
        DECLARE @error int, @nb int;
        EXEC """ + dbConfig['data_schema'] + """.sp_validate_rfid :user, @nb OUTPUT, @error OUTPUT;
        SELECT @error, @nb;"""
    ).bindparams(bindparam('user', request.authenticated_userid))
    error_code, nb = DBSession.execute(stmt).fetchone()
    if error_code == 0:
        if nb > 0:
            return 'Success : ' + str(nb) + ' new rows inserted in table T_AnimalLocation.'
        else:
            return 'Warning : no new row inserted.'
    else:
        return 'Error : an error occured during validation process (error code : ' + str(error_code) + ' )'

@view_config(route_name=prefix + 'search', renderer='json', request_method='POST')
def rfids_search(request):

    # test data obj => {criteria,order_by,offest,per_page,total_page} ====>>>>> See individuals front
    # criteria={"begin_date":{"Value":"11/11/2013","Operator":">"},"Name":{"Value":"E6","Operator":"="}}
    table=Base.metadata.tables['RFID_MonitoredSite']
    
   
    print(request.params)
    print(request.POST['criteria'])
    criteria=request.json_body.get('criteria',{})
    # Look over the criteria list

    print(criteria)


    #criteria = request.params.get('criteria', '{}')



    criteria = request.json_body.get('criteria', {})
    query = select(table.c)


    for obj in criteria:

        query=query.where(eval_binary_expr(table.c[obj['Column']], obj['Operator'], obj['Value']))


    # Set sorting columns and order


    '''
    order_by = json.loads(request.POST.get('order_by', '[]'))
    order_by_clause = []
    for obj in order_by:
        column, order = obj.split(':')
        if column in table.columns:
            if order == 'asc':
                order_by_clause.append(table.columns[column].asc())
            elif order == 'desc':
                order_by_clause.append(table.columns[column].desc())
    if len(order_by_clause) > 0:
        query = query.order_by(*order_by_clause)
    '''



    total = DBSession.execute(select([func.count()]).select_from(query.alias())).scalar()
    
    #Define the limit and offset if exist

    # offset = int(request.POST.get('offset', 0))
    # limit = int(request.POST.get('per_page', 0))

    # if limit > 0:
    #     query = query.limit(limit)
    # if offset > 0:
    #     query = query.offset(offset)
    # result = [{'total_entries':total}]
    # data = DBSession.execute(query).fetchall()
    # result.append([OrderedDict(row) for row in data])


    '''
    offset = int(request.POST.get('offset', 0))
    limit = int(request.POST.get('per_page', 0))

    if limit > 0:
        query = query.limit(limit)
    if offset > 0:
        query = query.offset(offset)
    '''
    result = [{'total_entries':total}]

    data = DBSession.execute(query).fetchall()
    result.append([OrderedDict(row) for row in data])
    
    return result

@view_config(route_name=prefix + 'getFields', renderer='json', request_method='POST')
def rfids_field(request):
    print('____________FIELDS_________________')

    dictCell={
    'VARCHAR':'string',
    'INTEGER':'number',
    'DECIMAL':'number',
    'DATETIME':'string',
    'BIT':'boolean',
    }

    table=Base.metadata.tables['RFID_MonitoredSite']
    print (table.c)

    columns=[table.c['PK_id'],table.c['identifier'],table.c['begin_date'],table.c['end_date'],table.c['Name'],table.c['name_Type']]
    
    final=[]
    for col in columns :
        name=col.name
        dislay=True
        Ctype=str(col.type).split('(')[0]
        if col.name=='PK_id':
            display=False
        if Ctype in dictCell:        
            Ctype=dictCell[Ctype]  
        else:
            Ctype='string'
        final.append({name:name,label:name.upper().replace('_',' '),cell:Ctype, renderable:display})

    print (final)
    return final

@view_config(route_name=prefix + 'search_geoJSON', renderer='json', request_method='POST')
def rfids_geoJSON(request):

    table=Base.metadata.tables['RFID_MonitoredSite']

    criteria = request.json_body.get('criteria', {})
    print(type(criteria))
    print(criteria)

    query = select(table.c)


    for obj in criteria:

        query=query.where(eval_binary_expr(table.c[obj['Column']], obj['Operator'], obj['Value']))

    data=DBSession.execute(query).fetchall()    
    geoJson=[]
    for row in data:
        geoJson.append({'type':'Feature', 'properties':{'name':row['Name']}, 'geometry':{'type':'Point', 'coordinates':[row['lon'],row['lat']]}})
    return {'type':'FeatureCollection', 'features':geoJson}



@view_config(route_name=prefix + 'update', renderer='json', request_method='POST')
def rfid_update(request):
    data = request.body
    rfid = json.loads(request.body.decode(encoding='UTF-8'))

    #table or view?
    table=Base.metadata.tables['RFID_MonitoredSite']

    query = select(table.c)

    '''
    SELECT obj.*,eq.lat, eq.lon,eq.begin_date,eq.end_date, MS.name_Type,MS.Name
    FROM T_Object obj JOIN  [T_MonitoredSiteEquipment] eq ON obj.PK_id=eq.FK_obj
    JOIN [dbo].[TMonitoredStations] MS ON eq.FK_site=MS.TGeo_pk_id 
    '''

    
