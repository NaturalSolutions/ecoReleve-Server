
from pyramid.view import view_config

from sqlalchemy import (
	Float,
	between,
	func,
	cast,
	Date,
	select,
	join,
	and_,
	insert,
	bindparam
	)

import datetime, operator
import re, csv

from ecorelevesensor.utils.eval import Eval

from ..models import DBSession, Base
from pyramid.response import Response
from ecorelevesensor.models.sensor import Argos, Gps
from ecorelevesensor.utils.spreadsheettable import SpreadsheetTable
from ecorelevesensor.renderers.csvrenderer import CSVRenderer
from ecorelevesensor.renderers.pdfrenderer import PDFrenderer
from ecorelevesensor.renderers.gpxrenderer import GPXRenderer
from ecorelevesensor.views.views import query_criteria



@view_config(route_name = 'core/views/export/filter/export', request_method='POST', renderer = 'json')
def views_filter_export(request):

	try:
		function_export= { 'csv': export_csv, 'pdf': export_pdf, 'gpx': export_gpx }
		criteria = request.json_body.get('criteria', {})
		viewName = criteria['viewName']
		table = Base.metadata.tables[viewName]
		type_export= criteria['type_export']
		#columns selection
		columns=criteria['columns']
		coll=[]
		for col in columns:
			coll.append(table.c[col])
		
		if type_export != 'gpx' :
			query = select(coll)
		else :
			query = select('*')
		#filters selection	
		filterList=criteria['filters']['filters']
		for fltr in filterList:
			column=fltr['Column']
			query = query.where(eval_binary_expr(table.c[column], fltr['Operator'], fltr['Value']))

		bbox=criteria['bbox']

		query = query.where(and_(between(table.c['LAT'], float(bbox[3]), float(bbox[1])), between(table.c['LON'], float(bbox[2]), float(bbox[0]))))
		rows = DBSession.execute(query).fetchall()
		filename = viewName+'.'+type_export
		request.response.content_disposition = 'attachment;filename=' + filename
		value={'header': columns, 'rows': rows}

		io_export=function_export[type_export](value,request,viewName)
		return Response(io_export)

	except: raise


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
    if(operator == 'Contains') :
    	return op1.like('%'+op2+'%')
    return get_operator_fn(operator)(op1, op2)

def export_csv (value,request,name_vue) :
	csvRender=CSVRenderer()
	csv=csvRender(value,{'request':request})
	return csv

def export_pdf (value,request,name_vue):
	pdfRender=PDFrenderer()
	pdf=pdfRender(value,name_vue,request)
	return pdf

def export_gpx (value,request,name_vue):
	gpxRender=GPXRenderer()
	gpx=gpxRender(value,request)
	return gpx


  

	  

  