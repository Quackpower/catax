# -*- coding: utf-8 -*-
from odoo import http, tools
from werkzeug.wrappers import Response
import json
import re
import hashlib
import pytz
from localStoragePy import localStoragePy
from datetime import datetime, timedelta
from odoo.http import request
from io import BytesIO
from PyPDF2 import PdfFileWriter, PdfFileReader
import base64, os,re,itertools
from os.path import dirname
from werkzeug.utils import secure_filename
import logging

logger = logging.getLogger(__name__)

class Catax(http.Controller):

    @http.route('/catax/buscar/', type='http', auth='public', website=True, cors='*', csrf=False)
    def catax_buscar(self, **kw):
        data = {'status': False}
        data['data'] = []
        try:
            registro = http.request.env['catax.catax'].sudo().search([('folio_report', '=',kw['folio'])],limit=1)
            

            auxmeei = len(registro)
            if auxmeei > 0:
                data["data"] = {
                    'categoria': registro.categoria.display_name,
                    'subcategoria': registro.sub_categoria.display_name,
                    'latitud': registro.latitud,
                    'longitud': registro.longitud,
                    'descripcion_reporte': registro.descripcion_reporte,
                    'comentario_seguimiento': registro.comentario_seguimiento,
                    'estatus': registro.estatus,
                    'evidencias' : []
                }

                for ev in registro.evidencia_atencion:
                    data['data']['evidencias'].append({
                        'filename' : ev.filename,
                        'nombre_archivo' : ev.nombre_archivo,
                        'evidencia' : str(ev.evidencia) if ev.evidencia else False,
                    })

            data['status'] = True


        except ValueError as er:
            data['status'] = False
            data['error'] = str(er)

        except Exception as er:
            data['status'] = False
            data['error'] = str(er)
            data['folio'] = False

        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)

    @http.route('/catax/get_all_data/', type='http', auth='public', website=True, cors='*', csrf=False)
    def get_all_data(self, **kw):
        data = {'status': False}
        data['data'] = []
        try:
            registro = http.request.env['catax.catax'].sudo().search([]) #('estatus', 'in',[kw['filtro']])
            
            for campo in registro:
                data['data'].append({
                    'categoria': campo.categoria.display_name,
                    'subcategoria': campo.sub_categoria.display_name,
                    'subcategoria_clave': campo.sub_categoria.clave,
                    'latitud': campo.latitud,
                    'longitud': campo.longitud,
                    'descripcion_reporte': campo.descripcion_reporte,
                    'comentario_seguimiento': campo.comentario_seguimiento,
                    'estatus' : campo.estatus
                })
            data['status'] = True

        except ValueError as er:
            data['status'] = False
            data['error'] = str(er)

        except Exception as er:
            data['status'] = False
            data['error'] = str(er)

        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)

    @http.route('/catax/getdata/', type='http', auth='public', website=True, cors='*', csrf=False)
    def catax_getdata(self, **km):
        data = {'status': False}
        data['data'] = []
        
        localStorage = localStoragePy('catax_map', 'catax_map')
        if 'latitud' in km:
            localStorage.setItem('latitud', km['latitud'])
        if 'longitud' in km:
            localStorage.setItem('longitud', km['longitud'])
        if 'direccion' in km:
            localStorage.setItem('direccion', km['direccion'])
        if 'calle' in km:
            localStorage.setItem('calle', km['calle'])
        localStorage.setItem('estado', 30)
        localStorage.setItem('municipio', 2087)

        cachedict = {}

        def strrep(orig, repdict):
            for k,v in repdict.items():
                if k in cachedict:
                    pattern = cachedict[k]
                else:
                    pattern = re.compile(k, re.IGNORECASE)
                    cachedict[k] = pattern
                orig = pattern.sub(v, orig)
            return orig

        try:
            
            if 'colonia' in km:
                localStorage.setItem('colonia', km['colonia'])
                logger.info(localStorage.getItem('colonia'))
                

        except ValueError as er:
            data['status'] = False
            data['error'] = str(er)

        except Exception as er:
            data['status'] = False
            data['error'] = str(er)

        

        
        
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)

    @http.route('/catax/get_closest_reports/', type='http', auth='public', website=True, cors='*', csrf=False)
    def catax_get_closest_reports(self, **kw):
        try:
            lat = kw.get('lat')
            lng = kw.get('lng')
            categoria = kw.get('categoria')
            data = {'status': False}
            data['data'] = []

            cat = http.request.env['catalogos_catax'].sudo().search([('clave', '=',categoria)],limit=1)
            if len(cat)>0:
                
                buscar_estatus = "('recibido','R','enproceso')"
                notvacio = "(ltrim(latitud) != '' or ltrim(longitud) != '')"
                _cr = http.request.cr
                query = 'select * from catax_catax where estatus in '+buscar_estatus+' and '+notvacio+' and categoria = '+str(cat.id)+' and ST_DWITHIN(st_SetSrid(st_MakePoint('+lng+','+lat+'), 4326), ST_MakePoint( (CASE when catax_catax."longitud" is null then 0 when catax_catax."longitud" = \'None\' then 0 else catax_catax."longitud"::double precision end),(case when catax_catax."latitud" is null then 0 when catax_catax."latitud" = \'None\' then 0 else catax_catax."latitud"::double precision end))::geography, 1000)'
                _cr.execute(query)
                results = _cr.dictfetchall()

                for campo in results:
                    data['data'].append({
                        'latitud': campo['latitud'],
                        'longitud': campo['longitud'],
                        'subcategoria': http.request.env['subcategorias_catax'].sudo().search([('id', '=',campo['sub_categoria'])],limit=1).name,
                        'folio': campo['folio_report'],
                        'desc' : campo['descripcion_reporte']
                    })

                data['status'] = True
                

                return Response(json.dumps(data['data']), content_type='application/json;charset=utf-8', status=200)

        except ValueError as er:
            data['status'] = False
            data['error'] = str(er)

        except Exception as er:
            data['status'] = False
            data['error'] = str(er)

        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)


    @http.route('/catax/guardar/', type='http', auth='public', website=True, cors='*', csrf=False)
    def catax_guardar(self, **kw):
        data = {'status': False}
        try:
            catax = http.request.env['catax.catax']

            kw['sub_categoria'] = http.request.env['subcategorias_catax'].sudo().search([('clave','=',kw['sub_categoria'])]).id

            kw['categoria'] = http.request.env['catalogos_catax'].sudo().search([('clave','=',kw['categoria'])]).id


            rec = catax.sudo().create(kw)
            
           
            data["status"] = True
            data["folio"] = rec.folio_report

        except ValueError as er:
            data['status'] = False
            data['error'] = str(er)

        except Exception as er:
            data['status'] = False
            data['error'] = str(er)

        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)

    @http.route('/catax/guardar_comentario_apoyo/', type='http', auth='public', website=True, cors='*', csrf=False)
    def catax_guardar_comentario_apoyo(self, **kw):
        data = {'status': False}
        try:
            catax = http.request.env['catax.catax']


            folio = catax.sudo().search([('folio_report','=',kw['folio'])]).id

            vals ={
                'id_catax' : folio,
                'comentarios' : kw['comentarios'] if 'comentarios' in kw and  kw['comentarios'] != "undefined"  else False,
            }

            http.request.env['catax.comentarios_apoyo'].sudo().create(vals)


            data["status"] = True
            data["folio"] = kw['folio']

        except ValueError as er:
            data['status'] = False
            data['error'] = str(er)

        except Exception as er:
            data['status'] = False
            data['error'] = str(er)

        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)

    @http.route('/catax/folio_dec/', type='http', auth='public', website=True, cors='*', csrf=False)
    def folio_dec(self, **kw):
        data = {'status': False}
        try:
            catax = http.request.env['catax.catax']
            fol = str(base64.b64decode(bytes(kw['folio'], 'utf-8'))).split("'")[1]
            folio = catax.sudo().search([('folio_report','=',fol)], limit=1)

            vals ={
                'calificacion_atencion' : kw['calificacion_atencion'] if 'calificacion_atencion' in kw and  kw['calificacion_atencion'] != "undefined"  else False,
                'calificacion_reporte' : kw['calificacion_reporte'] if 'calificacion_reporte' in kw and  kw['calificacion_reporte'] != "undefined"  else False,
                'comentarios_reportante' : kw['comentarios_reportante'] if 'comentarios_reportante' in kw and  kw['comentarios_reportante'] != "undefined"  else False,
                'eval_calif' : True,
                'fecha_encuesta_evaluada' : datetime.now().astimezone(pytz.timezone('Mexico/General'))

            }

            if folio.calificacion_reporte == True or folio.calificacion_reporte != "0":
                
                data["status"] = False
                data["error"] = "Este folio ya fue valorado."
            else:
                folio.sudo().write(vals)

                data["status"] = True
                data["folio"] = kw['folio']

        except ValueError as er:
            data['status'] = False
            data['error'] = str(er)

        except Exception as er:
            data['status'] = False
            data['error'] = str(er)

        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)


    @http.route('/catax/download_file', auth='public', type='http', website=True, methods = ['GET'], csrf=False)
    def download_file(self, path, file_name, **kw):
        _file = open(path, 'rb').read()
        #odt = base64.encodebytes(file)

        if not _file:
            return http.request.not_found()
        else:
            os.remove(path)
            return http.request.make_response(_file,[('Content-Type', 'application/vnd'),
                             ('Content-Disposition', 'attachment; filename=' + file_name + ';')])     

    @http.route('/catax/estadisticas/', type='http', auth='public', website=True, cors='*', csrf=False)
    def estadisticas(self, **kw):
        data = {'status': False}
        data['data'] = []
        data['total_categorias'] = []
        try:

            categorias = http.request.env['catalogos_catax'].sudo().search([('activo','=', True)], order='prioridadCate asc')
            
            for x in categorias:
                registro = http.request.env['catax.catax'].sudo().search([('categoria','=', x.id)])

                
                data['total_categorias'].append({
                        'id' : x.id,
                        'categoria': x.display_name,
                        'cantidad_reportes': len(registro),
                        'recibidos' : len(http.request.env['catax.catax'].sudo().search([('&'),('categoria','=', x.id),('estatus','=', 'R')])),
                        'atendidos' : len(http.request.env['catax.catax'].sudo().search([('&'),('categoria','=', x.id),('estatus','=', 'ATEN')])),
                        'proceso' : len(http.request.env['catax.catax'].sudo().search([('&'),('categoria','=', x.id),('estatus','=', 'enproceso')])),
                    })

            data['status'] = True

        except ValueError as er:
            data['status'] = False
            data['error'] = str(er)

        except Exception as er:
            data['status'] = False
            data['error'] = str(er)

        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)